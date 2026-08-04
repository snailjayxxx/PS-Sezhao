#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
DIST="$ROOT/dist"
PS_STAGE="$ROOT/.build/PS-Sezhao-Photoshop"
LR_STAGE="$ROOT/.build/PS-Sezhao.lrplugin"

rm -rf "$DIST" "$ROOT/.build"
mkdir -p "$DIST" "$PS_STAGE" "$LR_STAGE"
cp -R "$ROOT/plugin/." "$PS_STAGE/"
cp -R "$ROOT/lightroom-classic/PS-Sezhao.lrplugin/." "$LR_STAGE/"

(
  cd "$PS_STAGE"
  zip -q -r "$DIST/PS-Sezhao-Photoshop-v${VERSION}.ccx" .
)
(
  cd "$ROOT/.build"
  zip -q -r "$DIST/PS-Sezhao-LightroomClassic-source-v${VERSION}.zip" PS-Sezhao.lrplugin
)
(
  cd "$ROOT"
  git archive --format=zip --output="$DIST/PS-Sezhao-v${VERSION}-source.zip" HEAD
)

printf 'Built platform-independent release files in %s\n' "$DIST"
ls -lh "$DIST"
