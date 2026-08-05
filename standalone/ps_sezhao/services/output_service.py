from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from queue import Queue
import threading
from typing import Any, Callable, Mapping, Sequence
import uuid

from ..engine import Analysis, Controls, analyze_image
from ..io_utils import load_image, make_preview, save_image
from ..processing import ProcessingCancelled, process_image_tiled
from ..raw_io import RawDecodeSettings, prepare_save_output
from ..workspace import clamp_crop, crop_array, normalize_rotation, rotate_array


@dataclass(frozen=True)
class ExportTask:
    source: Path
    destination: Path
    controls: Controls
    crop: tuple[float, float, float, float]
    rotation: int = 0
    analysis: Analysis | None = None
    raw_settings: RawDecodeSettings | Mapping[str, Any] | None = None
    bit_depth: int = 16
    jpeg_quality: int = 95
    label: str = ""

    def normalized(self) -> "ExportTask":
        return ExportTask(
            source=Path(self.source),
            destination=Path(self.destination),
            controls=self.controls.sanitized(),
            crop=clamp_crop(self.crop),
            rotation=normalize_rotation(self.rotation),
            analysis=self.analysis,
            raw_settings=self.raw_settings,
            bit_depth=16 if int(self.bit_depth) >= 16 else 8,
            jpeg_quality=min(100, max(1, int(self.jpeg_quality))),
            label=self.label or Path(self.source).name,
        )


@dataclass(frozen=True)
class ExportFailure:
    index: int
    source: str
    destination: str
    error: str


@dataclass(frozen=True)
class ExportEvent:
    kind: str
    batch_id: str
    index: int
    total: int
    task: ExportTask | None
    stage: str = ""
    item_progress: float = 0.0
    overall_progress: float = 0.0
    message: str = ""
    error: str | None = None


@dataclass(frozen=True)
class ExportSummary:
    batch_id: str
    total: int
    succeeded: int
    failed: int
    cancelled: int
    failures: tuple[ExportFailure, ...]

    @property
    def completed(self) -> int:
        return self.succeeded + self.failed


@dataclass
class _ExportBatch:
    batch_id: str
    tasks: tuple[ExportTask, ...]
    on_event: Callable[[ExportEvent], None] | None
    on_complete: Callable[[ExportSummary], None] | None
    cancel_event: threading.Event


class OutputQueueService:
    """Sequential full-resolution export queue with cooperative cancellation."""

    def __init__(self) -> None:
        self._queue: Queue[_ExportBatch | None] = Queue()
        self._lock = threading.RLock()
        self._closed = False
        self._active_batch: str | None = None
        self._cancel_events: dict[str, threading.Event] = {}
        self._worker = threading.Thread(
            target=self._run,
            daemon=True,
            name="ps-sezhao-output-1",
        )
        self._worker.start()

    def submit(
        self,
        tasks: Sequence[ExportTask],
        *,
        on_event: Callable[[ExportEvent], None] | None = None,
        on_complete: Callable[[ExportSummary], None] | None = None,
    ) -> str:
        normalized = tuple(task.normalized() for task in tasks)
        if not normalized:
            raise ValueError("输出队列中没有任务。")
        batch_id = uuid.uuid4().hex
        cancel_event = threading.Event()
        with self._lock:
            if self._closed:
                raise RuntimeError("输出队列已经关闭。")
            self._cancel_events[batch_id] = cancel_event
            self._queue.put(
                _ExportBatch(
                    batch_id=batch_id,
                    tasks=normalized,
                    on_event=on_event,
                    on_complete=on_complete,
                    cancel_event=cancel_event,
                )
            )
        return batch_id

    def cancel(self, batch_id: str) -> bool:
        with self._lock:
            event = self._cancel_events.get(str(batch_id))
            if event is None:
                return False
            event.set()
            return True

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            for event in self._cancel_events.values():
                event.set()
            self._queue.put(None)

    @property
    def active_batch_id(self) -> str | None:
        with self._lock:
            return self._active_batch

    def _run(self) -> None:
        while True:
            batch = self._queue.get()
            try:
                if batch is None:
                    return
                with self._lock:
                    self._active_batch = batch.batch_id
                self._run_batch(batch)
            finally:
                if batch is not None:
                    with self._lock:
                        self._cancel_events.pop(batch.batch_id, None)
                        if self._active_batch == batch.batch_id:
                            self._active_batch = None
                self._queue.task_done()

    def _run_batch(self, batch: _ExportBatch) -> None:
        total = len(batch.tasks)
        succeeded = 0
        failed = 0
        failures: list[ExportFailure] = []
        self._emit(
            batch,
            ExportEvent(
                kind="batch_started",
                batch_id=batch.batch_id,
                index=0,
                total=total,
                task=None,
                message=f"开始导出 {total} 张图片。",
            ),
        )

        for zero_index, task in enumerate(batch.tasks):
            if batch.cancel_event.is_set():
                break
            index = zero_index + 1
            self._emit_progress(
                batch,
                task,
                index=index,
                total=total,
                stage="decode",
                item_progress=0.0,
                message=f"读取全分辨率原图：{task.label}",
            )
            try:
                self._execute_task(batch, task, index=index, total=total)
            except ProcessingCancelled:
                batch.cancel_event.set()
                self._emit(
                    batch,
                    ExportEvent(
                        kind="item_cancelled",
                        batch_id=batch.batch_id,
                        index=index,
                        total=total,
                        task=task,
                        stage="cancelled",
                        item_progress=0.0,
                        overall_progress=zero_index / total,
                        message=f"已取消：{task.label}",
                    ),
                )
                break
            except Exception as exc:
                failed += 1
                failure = ExportFailure(
                    index=index,
                    source=str(task.source),
                    destination=str(task.destination),
                    error=str(exc),
                )
                failures.append(failure)
                self._emit(
                    batch,
                    ExportEvent(
                        kind="item_failed",
                        batch_id=batch.batch_id,
                        index=index,
                        total=total,
                        task=task,
                        stage="failed",
                        item_progress=1.0,
                        overall_progress=index / total,
                        message=f"导出失败，继续下一张：{task.label}",
                        error=str(exc),
                    ),
                )
                continue

            succeeded += 1
            self._emit(
                batch,
                ExportEvent(
                    kind="item_succeeded",
                    batch_id=batch.batch_id,
                    index=index,
                    total=total,
                    task=task,
                    stage="complete",
                    item_progress=1.0,
                    overall_progress=index / total,
                    message=f"已导出：{task.destination.name}",
                ),
            )

        cancelled = max(0, total - succeeded - failed)
        summary = ExportSummary(
            batch_id=batch.batch_id,
            total=total,
            succeeded=succeeded,
            failed=failed,
            cancelled=cancelled,
            failures=tuple(failures),
        )
        self._emit(
            batch,
            ExportEvent(
                kind="batch_completed",
                batch_id=batch.batch_id,
                index=summary.completed,
                total=total,
                task=None,
                stage="cancelled" if cancelled else "complete",
                item_progress=1.0,
                overall_progress=(summary.completed / total) if total else 1.0,
                message=(
                    f"导出完成：成功 {succeeded}，失败 {failed}。"
                    if not cancelled
                    else f"导出已停止：成功 {succeeded}，失败 {failed}，未处理 {cancelled}。"
                ),
            ),
        )
        if batch.on_complete is not None:
            try:
                batch.on_complete(summary)
            except Exception:
                pass

    def _execute_task(
        self,
        batch: _ExportBatch,
        task: ExportTask,
        *,
        index: int,
        total: int,
    ) -> None:
        self._check_cancel(batch)
        image, metadata = load_image(task.source, raw_settings=task.raw_settings)
        self._emit_progress(
            batch,
            task,
            index=index,
            total=total,
            stage="geometry",
            item_progress=0.12,
            message=f"应用旋转与裁切：{task.label}",
        )
        self._check_cancel(batch)
        image = rotate_array(image, task.rotation)
        source = crop_array(image, task.crop)
        analysis = task.analysis
        if analysis is None:
            analysis = analyze_image(
                make_preview(source, 1800),
                method="crop-border",
            )

        def processing_progress(value: float) -> None:
            progress = 0.20 + min(1.0, max(0.0, float(value))) * 0.65
            self._emit_progress(
                batch,
                task,
                index=index,
                total=total,
                stage="processing",
                item_progress=progress,
                message=f"计算正片 {index}/{total}：{task.label}",
            )

        result = process_image_tiled(
            source,
            analysis,
            task.controls,
            should_cancel=batch.cancel_event.is_set,
            progress_callback=processing_progress,
        )
        self._check_cancel(batch)
        result = prepare_save_output(result, metadata)
        self._emit_progress(
            batch,
            task,
            index=index,
            total=total,
            stage="saving",
            item_progress=0.90,
            message=f"写入文件：{task.destination.name}",
        )
        _atomic_save(
            task.destination,
            result,
            bit_depth=task.bit_depth,
            icc_profile=metadata.get("icc_profile"),
            jpeg_quality=task.jpeg_quality,
            should_cancel=batch.cancel_event.is_set,
        )

    def _check_cancel(self, batch: _ExportBatch) -> None:
        if batch.cancel_event.is_set():
            raise ProcessingCancelled("输出任务已取消。")

    def _emit_progress(
        self,
        batch: _ExportBatch,
        task: ExportTask,
        *,
        index: int,
        total: int,
        stage: str,
        item_progress: float,
        message: str,
    ) -> None:
        fraction = min(1.0, max(0.0, float(item_progress)))
        overall = ((index - 1) + fraction) / total
        self._emit(
            batch,
            ExportEvent(
                kind="item_progress",
                batch_id=batch.batch_id,
                index=index,
                total=total,
                task=task,
                stage=stage,
                item_progress=fraction,
                overall_progress=overall,
                message=message,
            ),
        )

    @staticmethod
    def _emit(batch: _ExportBatch, event: ExportEvent) -> None:
        if batch.on_event is None:
            return
        try:
            batch.on_event(event)
        except Exception:
            pass


def _atomic_save(
    destination: Path,
    image: Any,
    *,
    bit_depth: int,
    icc_profile: bytes | None,
    jpeg_quality: int,
    should_cancel: Callable[[], bool],
) -> None:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.stem}.ps-sezhao-{uuid.uuid4().hex}{destination.suffix}"
    )
    try:
        if should_cancel():
            raise ProcessingCancelled("输出任务已取消。")
        save_image(
            temporary,
            image,
            bit_depth=bit_depth,
            icc_profile=icc_profile,
            jpeg_quality=jpeg_quality,
        )
        if should_cancel():
            raise ProcessingCancelled("输出任务已取消。")
        temporary.replace(destination)
    finally:
        try:
            if temporary.exists():
                temporary.unlink()
        except OSError:
            pass


def reserve_unique_destination(
    requested: Path,
    reserved: set[str],
) -> Path:
    """Return a collision-safe destination and reserve it for the batch."""

    requested = Path(requested)
    candidate = requested
    number = 2
    while _destination_key(candidate) in reserved or candidate.exists():
        candidate = requested.with_name(f"{requested.stem}_{number}{requested.suffix}")
        number += 1
    reserved.add(_destination_key(candidate))
    return candidate


def _destination_key(path: Path) -> str:
    return str(Path(path).expanduser().resolve(strict=False)).casefold()
