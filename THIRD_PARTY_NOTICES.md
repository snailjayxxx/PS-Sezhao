# Third-party notices

PS-Sezhao 的独立桌面版使用以下第三方组件。

## rawpy

- Project: `letmaik/rawpy`
- Purpose: Python bindings for LibRaw and camera RAW decoding
- License: MIT

## LibRaw

- Project: LibRaw
- Purpose: Camera RAW reading, unpacking and post-processing
- Distribution: Included through the binary wheels supplied by rawpy
- License: LibRaw is distributed under its published dual-license terms. See the LibRaw project and the licenses bundled with the rawpy wheel for the exact version included in each platform build.

## Compact ICC Profiles

- Project: `saucecontrol/Compact-ICC-Profiles`
- File: `profiles/ProPhoto-v2-micro.icc`
- Purpose: ProPhoto RGB profile embedded in 16-bit TIFF output
- License: Creative Commons CC0 1.0 / public-domain dedication

The embedded ICC bytes are stored in `standalone/ps_sezhao/color_profiles.py` so PyInstaller can include the profile consistently on macOS and Windows.
