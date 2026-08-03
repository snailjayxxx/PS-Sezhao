#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
DIST="$ROOT/dist"
STAGE="$ROOT/.build/PS-Sezhao"

rm -rf "$DIST" "$ROOT/.build"
mkdir -p "$DIST" "$STAGE"
cp -R "$ROOT/plugin/." "$STAGE/"

(
  cd "$STAGE"
  zip -q -r "$DIST/PS-Sezhao-v${VERSION}.ccx" .
)
(
  cd "$ROOT"
  git archive --format=zip --output="$DIST/PS-Sezhao-v${VERSION}-source.zip" HEAD
)
(
  cd "$DIST"
  sha256sum "PS-Sezhao-v${VERSION}.ccx" "PS-Sezhao-v${VERSION}-source.zip" > CHECKSUMS.txt
)

printf 'Built release files in %s\n' "$DIST"
ls -lh "$DIST"
