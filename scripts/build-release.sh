#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
CORE_VERSION="${VERSION%%-*}"
DIST="$ROOT/dist"
DEV_STAGE="$ROOT/.build/PS-Sezhao-Photoshop-Developer"
LR_STAGE="$ROOT/.build/PS-Sezhao.lrplugin"
CCX="$DIST/PS-Sezhao-Photoshop-v${VERSION}.ccx"

rm -rf "$DIST" "$ROOT/.build"
mkdir -p "$DIST" "$DEV_STAGE" "$LR_STAGE"
cp -R "$ROOT/plugin/." "$DEV_STAGE/"
cp -R "$ROOT/lightroom-classic/PS-Sezhao.lrplugin/." "$LR_STAGE/"
cp "$ROOT/PHOTOSHOP_DEVELOPER_LOAD.md" "$DEV_STAGE/开发者加载说明.md"

# CCX 使用 ZIP 容器，插件文件必须直接位于压缩包根目录。
(
  cd "$ROOT/plugin"
  zip -q -r "$CCX" .
)

# 在发布前验证关键结构。UXP 清单只接受纯数字 x.y.z，
# Beta 标识保留在发行标签、文件名和运行时显示版本中。
unzip -Z1 "$CCX" | grep -qx 'manifest.json'
node -e '
  const fs = require("fs");
  const expected = process.argv[1];
  const manifest = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  if (manifest.version !== expected) throw new Error(`CCX manifest version ${manifest.version} != ${expected}`);
  if (manifest.host?.app !== "PS") throw new Error("CCX manifest does not target Photoshop");
  if (manifest.host?.minVersion !== "25.0.0") throw new Error("CCX does not target Photoshop 2024+");
' "$CORE_VERSION" "$ROOT/plugin/manifest.json"

(
  cd "$ROOT/.build"
  zip -q -r "$DIST/PS-Sezhao-Photoshop-Developer-v${VERSION}.zip" PS-Sezhao-Photoshop-Developer
  zip -q -r "$DIST/PS-Sezhao-LightroomClassic-Source-v${VERSION}.zip" PS-Sezhao.lrplugin
)
(
  cd "$ROOT"
  git archive --format=zip --output="$DIST/PS-Sezhao-v${VERSION}-source.zip" HEAD
)

printf 'Built and verified common release files in %s\n' "$DIST"
ls -lh "$DIST"
