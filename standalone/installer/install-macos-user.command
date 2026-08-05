#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_ROOT="$SCRIPT_DIR/PS-Sezhao"
TARGET_ROOT="$HOME/Applications/PS-Sezhao"
SOURCE_APP="$SOURCE_ROOT/PS-Sezhao.app"
TARGET_APP="$TARGET_ROOT/PS-Sezhao.app"
TEMP_APP="$TARGET_ROOT/.PS-Sezhao.app.installing"
BACKUP_APP="$TARGET_ROOT/.PS-Sezhao.app.previous"

if [[ ! -d "$SOURCE_APP" ]]; then
  echo "找不到安装源：$SOURCE_APP"
  read -k 1 "?按任意键关闭…"
  exit 1
fi

mkdir -p "$HOME/Applications" "$TARGET_ROOT/project" "$TARGET_ROOT/lut"
rm -rf "$TEMP_APP" "$BACKUP_APP"
ditto "$SOURCE_APP" "$TEMP_APP"

if [[ -d "$TARGET_APP" ]]; then
  mv "$TARGET_APP" "$BACKUP_APP"
fi
mv "$TEMP_APP" "$TARGET_APP"
rm -rf "$BACKUP_APP"

if [[ -f "$SOURCE_ROOT/.ps-sezhao-portable" ]]; then
  cp -f "$SOURCE_ROOT/.ps-sezhao-portable" "$TARGET_ROOT/.ps-sezhao-portable"
else
  printf '%s\n' 'PS-Sezhao portable data root.' > "$TARGET_ROOT/.ps-sezhao-portable"
fi
if [[ -f "$SCRIPT_DIR/安装说明.html" ]]; then
  cp -f "$SCRIPT_DIR/安装说明.html" "$TARGET_ROOT/安装说明.html"
elif [[ -f "$SOURCE_ROOT/安装说明.html" ]]; then
  cp -f "$SOURCE_ROOT/安装说明.html" "$TARGET_ROOT/安装说明.html"
fi

cat <<EOF

PS-Sezhao 已安装到：
$TARGET_ROOT

胶卷项目：$TARGET_ROOT/project
用户 LUT：$TARGET_ROOT/lut

首次打开若被 macOS 阻止，请在 Finder 中按住 Control 点击 PS-Sezhao.app，选择“打开”。
EOF

open "$TARGET_ROOT"
read -k 1 "?按任意键关闭…"
echo
