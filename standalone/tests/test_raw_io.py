from __future__ import annotations

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from ps_sezhao import raw_io
from ps_sezhao.color_profiles import PROPHOTO_RGB_V2_MICRO, validate_profiles


class _EnumValue:
    def __init__(self, name: str) -> None:
        self.name = name
        self.isSupported = True


class _UnsupportedError(Exception):
    pass


class _NoThumbnailError(Exception):
    pass


class _FakeRaw:
    def __init__(self, module: type["_FakeRawPy"]) -> None:
        self.module = module
        self.camera_whitebalance = [2.0, 1.0, 1.5, 1.0]
        self.daylight_whitebalance = [2.2, 1.0, 1.4, 1.0]
        self.white_level = 16383
        self.black_level_per_channel = [512, 512, 512, 512]
        self.sizes = SimpleNamespace(raw_width=8, raw_height=6, width=6, height=4)
        self.other = SimpleNamespace(iso_speed=100, shutter_speed=0.01, aperture=8.0, focal_length=100.0)
        self.lens = SimpleNamespace(model="Macro 100mm")

    def __enter__(self) -> "_FakeRaw":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def postprocess(self, **kwargs: object) -> np.ndarray:
        self.module.last_kwargs = kwargs
        return np.full((4, 6, 3), 32768, dtype=np.uint16)

    def extract_thumb(self) -> SimpleNamespace:
        if self.module.no_thumbnail:
            raise _NoThumbnailError("missing")
        image = Image.new("RGB", (12, 8), (128, 64, 32))
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        return SimpleNamespace(format=self.module.ThumbFormat.JPEG, data=buffer.getvalue())


class _FakeRawPy:
    __version__ = "test"
    libraw_version = (0, 22, 0)
    flags = {"LCMS": True}
    last_kwargs: dict[str, object] = {}
    raise_unsupported = False
    no_thumbnail = False

    class ColorSpace:
        ProPhoto = _EnumValue("ProPhoto")

    class HighlightMode:
        Clip = _EnumValue("Clip")
        Blend = _EnumValue("Blend")
        ReconstructDefault = _EnumValue("Reconstruct")

    class DemosaicAlgorithm:
        AHD = _EnumValue("AHD")
        LINEAR = _EnumValue("LINEAR")
        VNG = _EnumValue("VNG")
        PPG = _EnumValue("PPG")

    class ThumbFormat:
        JPEG = _EnumValue("JPEG")
        BITMAP = _EnumValue("BITMAP")

    LibRawFileUnsupportedError = _UnsupportedError
    LibRawNotImplementedError = _UnsupportedError
    NotSupportedError = _UnsupportedError
    LibRawNoThumbnailError = _NoThumbnailError
    LibRawUnsupportedThumbnailError = _NoThumbnailError

    @classmethod
    def imread(cls, _path: str) -> _FakeRaw:
        if cls.raise_unsupported:
            raise _UnsupportedError("unsupported camera")
        return _FakeRaw(cls)


class RawIoTests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeRawPy.last_kwargs = {}
        _FakeRawPy.raise_unsupported = False
        _FakeRawPy.no_thumbnail = False

    def test_embedded_profile_is_valid(self) -> None:
        validate_profiles()
        self.assertEqual(len(PROPHOTO_RGB_V2_MICRO), 496)
        self.assertEqual(int.from_bytes(PROPHOTO_RGB_V2_MICRO[:4], "big"), 496)

    def test_settings_sanitize_custom_white_balance(self) -> None:
        settings = raw_io.RawDecodeSettings(
            wb_mode="custom",
            custom_wb=(0, 2, float("nan"), 99),
            highlight_mode="invalid",
            demosaic="invalid",
        ).sanitized()
        self.assertEqual(settings.wb_mode, "custom")
        self.assertEqual(settings.custom_wb, (0.05, 2.0, 1.0, 16.0))
        self.assertEqual(settings.highlight_mode, "blend")
        self.assertEqual(settings.demosaic, "ahd")

    def test_decode_raw_uses_linear_16_bit_prophoto(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.nef"
            path.write_bytes(b"fake")
            with patch.object(raw_io, "rawpy", _FakeRawPy):
                image, metadata = raw_io.decode_raw(
                    path,
                    raw_io.RawDecodeSettings(wb_mode="camera", highlight_mode="blend", demosaic="ahd"),
                )
        self.assertEqual(image.shape, (4, 6, 3))
        self.assertEqual(image.dtype, np.float32)
        self.assertAlmostEqual(float(image[0, 0, 0]), 32768 / 65535.0, places=6)
        kwargs = _FakeRawPy.last_kwargs
        self.assertEqual(kwargs["output_bps"], 16)
        self.assertEqual(kwargs["gamma"], (1.0, 1.0))
        self.assertTrue(kwargs["no_auto_bright"])
        self.assertTrue(kwargs["use_camera_wb"])
        self.assertIs(kwargs["output_color"], _FakeRawPy.ColorSpace.ProPhoto)
        self.assertTrue(metadata["linear_raw"])
        self.assertEqual(metadata["icc_profile"], PROPHOTO_RGB_V2_MICRO)

    def test_custom_white_balance_is_sent_to_libraw(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.dng"
            path.write_bytes(b"fake")
            settings = raw_io.RawDecodeSettings(wb_mode="custom", custom_wb=(2.0, 1.0, 1.25, 1.0))
            with patch.object(raw_io, "rawpy", _FakeRawPy):
                raw_io.decode_raw(path, settings)
        self.assertEqual(_FakeRawPy.last_kwargs["user_wb"], [2.0, 1.0, 1.25, 1.0])
        self.assertFalse(_FakeRawPy.last_kwargs["use_camera_wb"])
        self.assertFalse(_FakeRawPy.last_kwargs["use_auto_wb"])

    def test_embedded_preview_is_used_before_full_decode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.cr3"
            path.write_bytes(b"fake")
            with patch.object(raw_io, "rawpy", _FakeRawPy):
                preview, metadata = raw_io.extract_raw_preview(path, max_edge=10)
        self.assertLessEqual(max(preview.shape[:2]), 10)
        self.assertEqual(metadata["preview_source"], "embedded")

    def test_unsupported_camera_has_actionable_message(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "future.raw"
            path.write_bytes(b"fake")
            _FakeRawPy.raise_unsupported = True
            with patch.object(raw_io, "rawpy", _FakeRawPy):
                with self.assertRaises(raw_io.RawDecodeError) as raised:
                    raw_io.decode_raw(path)
        text = str(raised.exception)
        self.assertIn("不支持该相机型号", text)
        self.assertIn("16 位 TIFF", text)

    def test_linear_output_is_encoded_for_prophoto_profile(self) -> None:
        image = np.array([[[0.25, 0.5, 1.0]]], dtype=np.float32)
        encoded = raw_io.prepare_save_output(image, {"linear_raw": True})
        expected = np.power(image, 1.0 / 1.8)
        self.assertTrue(np.allclose(encoded, expected))
        unchanged = raw_io.prepare_save_output(image, {"linear_raw": False})
        self.assertTrue(np.array_equal(unchanged, image))


if __name__ == "__main__":
    unittest.main()
