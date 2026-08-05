from __future__ import annotations

from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

import numpy as np
from PIL import Image

from ps_sezhao.raw_io import RawDecodeSettings
from ps_sezhao.services import proxy_service
from ps_sezhao.services.proxy_service import (
    FrameCache,
    PreviewFrame,
    PreviewProxyService,
    load_edit_proxy_frame,
    load_thumbnail_frame,
)


class ProxyPipelineV070Tests(unittest.TestCase):
    def test_frame_cache_enforces_item_and_memory_limits(self) -> None:
        cache = FrameCache(max_items=2, max_bytes=180)
        for index in range(3):
            image = np.zeros((4, 4, 3), dtype=np.float32)
            image.setflags(write=False)
            frame = PreviewFrame(
                path=f"/scan-{index}.tif",
                level="edit-proxy",
                image=image,
                metadata={},
                cache_key=str(index),
            )
            cache.put(str(index), frame)

        self.assertLessEqual(cache.item_count, 2)
        self.assertLessEqual(cache.byte_count, 180)
        self.assertIsNone(cache.get("0"))

    def test_raw_thumbnail_uses_fast_preview_without_full_decode(self) -> None:
        preview = np.full((12, 18, 3), 0.5, dtype=np.float32)
        with mock.patch.object(
            proxy_service,
            "extract_raw_preview",
            return_value=(preview, {"preview_source": "embedded", "raw": True}),
        ) as extract, mock.patch.object(proxy_service, "decode_raw") as full_decode:
            frame = load_thumbnail_frame("scan.ARW", RawDecodeSettings(), max_edge=720)

        extract.assert_called_once()
        full_decode.assert_not_called()
        self.assertEqual(frame.level, "thumbnail")
        self.assertEqual(frame.metadata["thumbnail_source"], "embedded")
        self.assertFalse(frame.metadata["full_resolution_loaded"])

    def test_raw_edit_proxy_is_linear_half_size_decode(self) -> None:
        source = np.linspace(0.0, 1.0, 90, dtype=np.float32).reshape(5, 6, 3)
        metadata = {"raw": True, "linear_raw": True, "raw_size": {"width": 6000, "height": 4000}}
        with mock.patch.object(proxy_service, "decode_raw", return_value=(source, metadata)) as decode:
            frame = load_edit_proxy_frame("scan.ARW", RawDecodeSettings(), max_edge=2200)

        self.assertTrue(decode.call_args.kwargs["half_size"])
        self.assertEqual(frame.level, "edit-proxy")
        self.assertEqual(frame.metadata["proxy_source"], "half-size-linear-raw")
        self.assertTrue(frame.metadata["linear_raw"])
        self.assertFalse(frame.metadata["full_resolution_loaded"])

    def test_duplicate_proxy_requests_share_one_background_decode(self) -> None:
        started = threading.Event()
        release = threading.Event()
        image = np.zeros((8, 8, 3), dtype=np.float32)
        image.setflags(write=False)
        frame = PreviewFrame(
            path=str(Path("scan.tif").resolve()),
            level="edit-proxy",
            image=image,
            metadata={},
            cache_key="shared",
        )

        def loader(*_args: object, **_kwargs: object) -> PreviewFrame:
            started.set()
            self.assertTrue(release.wait(timeout=5))
            return frame

        service = PreviewProxyService(workers=1)
        try:
            with mock.patch.object(proxy_service, "load_edit_proxy_frame", side_effect=loader) as decode:
                first = service.request_proxy("scan.tif")
                self.assertTrue(started.wait(timeout=5))
                second = service.request_proxy("scan.tif")
                self.assertIs(first, second)
                release.set()
                self.assertIs(first.result(timeout=5), frame)
                self.assertEqual(decode.call_count, 1)
        finally:
            service.shutdown()

    def test_regular_thumbnail_and_proxy_have_separate_resolutions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "scan.jpg"
            Image.new("RGB", (2400, 1600), (120, 80, 40)).save(source, quality=90)

            thumbnail = load_thumbnail_frame(source, max_edge=320)
            proxy = load_edit_proxy_frame(source, max_edge=900)

            self.assertLessEqual(max(thumbnail.image.shape[:2]), 320)
            self.assertLessEqual(max(proxy.image.shape[:2]), 900)
            self.assertGreater(max(proxy.image.shape[:2]), max(thumbnail.image.shape[:2]))
            self.assertEqual(thumbnail.metadata["preview_level"], "thumbnail")
            self.assertEqual(proxy.metadata["preview_level"], "edit-proxy")

    def test_pipeline_defers_full_resolution_until_save(self) -> None:
        root = Path(__file__).resolve().parents[2]
        source = (root / "standalone/ps_sezhao/services/proxy_pipeline.py").read_text(encoding="utf-8")
        self.assertIn("self.full_image = None", source)
        self.assertIn("request_thumbnail", source)
        self.assertIn("request_proxy", source)
        self.assertIn("_prefetch_next_proxy", source)
        self.assertIn("正在读取全分辨率原图", source)


if __name__ == "__main__":
    unittest.main()
