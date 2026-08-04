#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
DIST="$ROOT/dist"
DEV_STAGE="$ROOT/.build/PS-Sezhao-Photoshop-Developer"
LR_STAGE="$ROOT/.build/PS-Sezhao.lrplugin"

rm -rf "$DIST" "$ROOT/.build"
mkdir -p "$DIST" "$DEV_STAGE" "$LR_STAGE"
cp -R "$ROOT/plugin/." "$DEV_STAGE/"
cp -R "$ROOT/lightroom-classic/PS-Sezhao.lrplugin/." "$LR_STAGE/"
cp "$ROOT/PHOTOSHOP_DEVELOPER_LOAD.md" "$DEV_STAGE/开发者加载说明.md"

(
  cd "$ROOT/.build"
  zip -q -r "$DIST/PS-Sezhao-Photoshop-Developer-v${VERSION}.zip" PS-Sezhao-Photoshop-Developer
  zip -q -r "$DIST/PS-Sezhao-LightroomClassic-source-v${VERSION}.zip" PS-Sezhao.lrplugin
)
(
  cd "$ROOT"
  git archive --format=zip --output="$DIST/PS-Sezhao-v${VERSION}-source.zip" HEAD
)

printf 'Built developer and source release files in %s\n' "$DIST"
ls -lh "$DIST"
