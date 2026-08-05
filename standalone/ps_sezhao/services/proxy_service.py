from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import Future
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from queue import Queue
import threading
from typing import Any, Callable, Mapping

import numpy as np
from PIL import Image, ImageOps

from ..io_utils import load_image, make_preview
from ..raw_io import (
    RawDecodeSettings,
    decode_raw,
    extract_raw_preview,
    is_raw_path,
)

THUMBNAIL_MAX_EDGE = 720
EDIT_PROXY_MAX_EDGE = 2200
DEFAULT_PROXY_ITEMS = 4
DEFAULT_PROXY_BYTES = 256 * 1024 * 1024
DEFAULT_THUMBNAIL_ITEMS = 24
DEFAULT_THUMBNAIL_BYTES = 72 * 1024 * 1024


@dataclass(frozen=True)
class PreviewFrame:
    path: str
    level: str
    image: np.ndarray
    metadata: dict[str, Any]
    cache_key: str

    @property
    def nbytes(self) -> int:
        return int(self.image.nbytes)


class FrameCache:
    """Thread-safe LRU cache bounded by both item count and memory."""

    def __init__(self, *, max_items: int, max_bytes: int) -> None:
        self.max_items = max(1, int(max_items))
        self.max_bytes = max(1, int(max_bytes))
        self._items: OrderedDict[str, PreviewFrame] = OrderedDict()
        self._bytes = 0
        self._lock = threading.RLock()

    def get(self, key: str) -> PreviewFrame | None:
        with self._lock:
            frame = self._items.get(key)
            if frame is None:
                return None
            self._items.move_to_end(key)
            return frame

    def put(self, key: str, frame: PreviewFrame) -> None:
        with self._lock:
            previous = self._items.pop(key, None)
            if previous is not None:
                self._bytes -= previous.nbytes
            self._items[key] = frame
            self._bytes += frame.nbytes
            self._items.move_to_end(key)
            while len(self._items) > self.max_items or self._bytes > self.max_bytes:
                _old_key, old_frame = self._items.popitem(last=False)
                self._bytes -= old_frame.nbytes

    def invalidate_path(self, path: str | Path) -> None:
        normalized = _normalized_path(path)
        with self._lock:
            stale = [key for key, frame in self._items.items() if frame.path == normalized]
            for key in stale:
                frame = self._items.pop(key)
                self._bytes -= frame.nbytes

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._bytes = 0

    @property
    def item_count(self) -> int:
        with self._lock:
            return len(self._items)

    @property
    def byte_count(self) -> int:
        with self._lock:
            return self._bytes


class DaemonTaskPool:
    """Small daemon worker pool so pending previews never block app exit."""

    def __init__(self, workers: int = 2, *, name: str = "ps-sezhao-preview") -> None:
        self._queue: Queue[tuple[Future[Any], Callable[[], Any]] | None] = Queue()
        self._closed = False
        self._lock = threading.Lock()
        self._threads = [
            threading.Thread(target=self._worker, daemon=True, name=f"{name}-{index + 1}")
            for index in range(max(1, int(workers)))
        ]
        for thread in self._threads:
            thread.start()

    def submit(self, function: Callable[[], Any]) -> Future[Any]:
        future: Future[Any] = Future()
        with self._lock:
            if self._closed:
                future.set_exception(RuntimeError("preview worker pool is closed"))
                return future
            self._queue.put((future, function))
        return future

    def shutdown(self, *, cancel_pending: bool = True) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if cancel_pending:
                while True:
                    try:
                        item = self._queue.get_nowait()
                    except Exception:
                        break
                    if item is not None:
                        item[0].cancel()
                    self._queue.task_done()
            for _thread in self._threads:
                self._queue.put(None)

    def _worker(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    return
                future, function = item
                if not future.set_running_or_notify_cancel():
                    continue
                try:
                    future.set_result(function())
                except BaseException as exc:
                    future.set_exception(exc)
            finally:
                self._queue.task_done()


def _normalized_path(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve(strict=False))


def _settings_payload(settings: RawDecodeSettings | Mapping[str, Any] | None) -> dict[str, Any]:
    if isinstance(settings, RawDecodeSettings):
        return settings.sanitized().to_dict()
    return RawDecodeSettings.from_dict(settings).to_dict()


def _cache_key(
    path: str | Path,
    *,
    level: str,
    max_edge: int,
    settings: RawDecodeSettings | Mapping[str, Any] | None,
) -> str:
    source = Path(path).expanduser()
    try:
        stat = source.stat()
        fingerprint = [int(stat.st_size), int(stat.st_mtime_ns)]
    except OSError:
        fingerprint = [0, 0]
    payload = {
        "path": _normalized_path(source),
        "fingerprint": fingerprint,
        "level": str(level),
        "max_edge": int(max_edge),
        "raw_settings": _settings_payload(settings) if is_raw_path(source) else None,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _freeze_frame(
    path: str | Path,
    *,
    level: str,
    image: np.ndarray,
    metadata: Mapping[str, Any],
    cache_key: str,
) -> PreviewFrame:
    array = np.ascontiguousarray(np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0))
    array.setflags(write=False)
    info = dict(metadata)
    info["preview_level"] = level
    info["full_resolution_loaded"] = False
    return PreviewFrame(
        path=_normalized_path(path),
        level=level,
        image=array,
        metadata=info,
        cache_key=cache_key,
    )


def load_thumbnail_frame(
    path: str | Path,
    settings: RawDecodeSettings | Mapping[str, Any] | None = None,
    *,
    max_edge: int = THUMBNAIL_MAX_EDGE,
) -> PreviewFrame:
    """Load the fastest available display thumbnail without full RAW decode."""

    source = Path(path)
    key = _cache_key(source, level="thumbnail", max_edge=max_edge, settings=settings)
    if is_raw_path(source):
        image, metadata = extract_raw_preview(source, settings, max_edge=max_edge)
        metadata = dict(metadata)
        metadata["thumbnail_source"] = metadata.get("preview_source", "embedded")
        return _freeze_frame(
            source,
            level="thumbnail",
            image=image,
            metadata=metadata,
            cache_key=key,
        )

    metadata: dict[str, Any] = {
        "path": str(source),
        "raw": False,
        "thumbnail_source": "pillow",
        "icc_profile": None,
    }
    try:
        with Image.open(source) as opened:
            metadata["icc_profile"] = opened.info.get("icc_profile")
            image = ImageOps.exif_transpose(opened).convert("RGB")
            image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
            array = np.asarray(image, dtype=np.uint8).astype(np.float32) / 255.0
    except Exception:
        full, loaded_metadata = load_image(source)
        array = make_preview(full, max_edge)
        metadata.update(loaded_metadata)
        metadata["thumbnail_source"] = "fallback-decode"
    return _freeze_frame(
        source,
        level="thumbnail",
        image=array,
        metadata=metadata,
        cache_key=key,
    )


def load_edit_proxy_frame(
    path: str | Path,
    settings: RawDecodeSettings | Mapping[str, Any] | None = None,
    *,
    max_edge: int = EDIT_PROXY_MAX_EDGE,
) -> PreviewFrame:
    """Load a high-quality editing proxy while deferring full-resolution output."""

    source = Path(path)
    key = _cache_key(source, level="edit-proxy", max_edge=max_edge, settings=settings)
    if is_raw_path(source):
        image, metadata = decode_raw(source, settings, half_size=True)
        proxy = make_preview(image, max_edge)
        metadata = dict(metadata)
        metadata["proxy_source"] = "half-size-linear-raw"
    else:
        image, metadata = load_image(source)
        proxy = make_preview(image, max_edge)
        metadata = dict(metadata)
        metadata["proxy_source"] = "downsampled-source"
    metadata["proxy_max_edge"] = int(max_edge)
    return _freeze_frame(
        source,
        level="edit-proxy",
        image=proxy,
        metadata=metadata,
        cache_key=key,
    )


class PreviewProxyService:
    """Deduplicated thumbnail and edit-proxy loading with bounded caches."""

    def __init__(
        self,
        *,
        proxy_items: int = DEFAULT_PROXY_ITEMS,
        proxy_bytes: int = DEFAULT_PROXY_BYTES,
        thumbnail_items: int = DEFAULT_THUMBNAIL_ITEMS,
        thumbnail_bytes: int = DEFAULT_THUMBNAIL_BYTES,
        workers: int = 2,
    ) -> None:
        self.proxy_cache = FrameCache(max_items=proxy_items, max_bytes=proxy_bytes)
        self.thumbnail_cache = FrameCache(max_items=thumbnail_items, max_bytes=thumbnail_bytes)
        self._pool = DaemonTaskPool(workers=workers)
        self._inflight: dict[str, Future[PreviewFrame]] = {}
        self._lock = threading.RLock()

    def request_thumbnail(
        self,
        path: str | Path,
        settings: RawDecodeSettings | Mapping[str, Any] | None = None,
        *,
        max_edge: int = THUMBNAIL_MAX_EDGE,
    ) -> Future[PreviewFrame]:
        key = _cache_key(path, level="thumbnail", max_edge=max_edge, settings=settings)
        return self._request(
            key,
            self.thumbnail_cache,
            lambda: load_thumbnail_frame(path, settings, max_edge=max_edge),
        )

    def request_proxy(
        self,
        path: str | Path,
        settings: RawDecodeSettings | Mapping[str, Any] | None = None,
        *,
        max_edge: int = EDIT_PROXY_MAX_EDGE,
    ) -> Future[PreviewFrame]:
        key = _cache_key(path, level="edit-proxy", max_edge=max_edge, settings=settings)
        return self._request(
            key,
            self.proxy_cache,
            lambda: load_edit_proxy_frame(path, settings, max_edge=max_edge),
        )

    def _request(
        self,
        key: str,
        cache: FrameCache,
        loader: Callable[[], PreviewFrame],
    ) -> Future[PreviewFrame]:
        cached = cache.get(key)
        if cached is not None:
            future: Future[PreviewFrame] = Future()
            future.set_result(cached)
            return future

        with self._lock:
            existing = self._inflight.get(key)
            if existing is not None:
                return existing
            future = self._pool.submit(loader)
            self._inflight[key] = future

        def finish(done: Future[PreviewFrame]) -> None:
            try:
                if not done.cancelled():
                    frame = done.result()
                    cache.put(key, frame)
            finally:
                with self._lock:
                    self._inflight.pop(key, None)

        future.add_done_callback(finish)
        return future

    def invalidate(self, path: str | Path) -> None:
        self.thumbnail_cache.invalidate_path(path)
        self.proxy_cache.invalidate_path(path)

    def shutdown(self) -> None:
        self._pool.shutdown(cancel_pending=True)
        with self._lock:
            self._inflight.clear()
