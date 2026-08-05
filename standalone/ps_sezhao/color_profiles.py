from __future__ import annotations

import base64

# Compact ProPhoto RGB ICC v2 profile from
# https://github.com/saucecontrol/Compact-ICC-Profiles
# File: profiles/ProPhoto-v2-micro.icc
# License: CC0-1.0 (public domain dedication).
_PROPHOTO_V2_MICRO_BASE64 = """
AAAB8GxjbXMCEAAAbW50clJHQiBYWVogB+IAAwAUAAkADgAdYWNzcE1TRlQA
AAAAc2F3c2N0cmwAAAAAAAAAAAAAAAAAAPbWAAEAAAAA0y1oYW5k/jHrr7/D
F5NlYRCDJH8ZpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJZGVz
YwAAAPAAAABfY3BydAAAAQwAAAAMd3RwdAAAARgAAAAUclhZWgAAASwAAAAU
Z1hZWgAAAUAAAAAUYlhZWgAAAVQAAAAUclRSQwAAAWgAAACIZ1RSQwAAAWgA
AACIYlRSQwAAAWgAAACIZGVzYwAAAAAAAAAFdVJPTQAAAAAAAAAAAAAAAHRl
eHQAAAAAQ0MwAFhZWiAAAAAAAAD23AABAAAAANM6WFlaIAAAAAAAAMw3AABJ
vgAAAABYWVogAAAAAAAAIpoAALY9AAAAAVhZWiAAAAAAAAAIBQAAAAUAANMs
Y3VydgAAAAAAAAA+AAAAQwCHAR0B4wLTA+4FLwaZCCkJ3Qu3DbQP1BIXFHsX
AhmpHHEfWiJiJYso0yw5L78zYzclOwY/BUMgR1pLsFAkVLVZYl4sYxJoFG0z
cm13w300gsGIao4tlAyaBaAapkmskrL3uXXADsbBzY7Udtt34pHpxvEU+Hv/
/w==
"""

PROPHOTO_RGB_V2_MICRO: bytes = base64.b64decode(_PROPHOTO_V2_MICRO_BASE64)


def validate_profiles() -> None:
    """Raise when the embedded profile was damaged during packaging."""

    if len(PROPHOTO_RGB_V2_MICRO) != 496:
        raise RuntimeError("内置 ProPhoto RGB ICC 配置文件长度无效。")
    declared_size = int.from_bytes(PROPHOTO_RGB_V2_MICRO[:4], "big")
    if declared_size != len(PROPHOTO_RGB_V2_MICRO):
        raise RuntimeError("内置 ProPhoto RGB ICC 配置文件头无效。")
