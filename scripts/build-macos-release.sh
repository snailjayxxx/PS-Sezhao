#!/usr/bin/env bash
set -euo pipefail

VERSION="$(tr -d '[:space:]' < VERSION)"
APP_PATH="dist/PS-Sezhao.app"
PLIST_PATH="$APP_PATH/Contents/Info.plist"
RELEASE_DIR="release-assets"
SIGNED_BUILD=0

require_signing_secrets() {
  [[ -n "${APPLE_CERTIFICATE_P12_BASE64:-}" ]] &&
  [[ -n "${APPLE_CERTIFICATE_PASSWORD:-}" ]] &&
  [[ -n "${APPLE_SIGNING_IDENTITY:-}" ]] &&
  [[ -n "${APPLE_ID:-}" ]] &&
  [[ -n "${APPLE_APP_SPECIFIC_PASSWORD:-}" ]] &&
  [[ -n "${APPLE_TEAM_ID:-}" ]]
}

set_plist_value() {
  local key="$1"
  local value="$2"
  if ! /usr/libexec/PlistBuddy -c "Set :$key $value" "$PLIST_PATH"; then
    /usr/libexec/PlistBuddy -c "Add :$key string $value" "$PLIST_PATH"
  fi
}

write_bundle_metadata() {
  test -f "$PLIST_PATH"
  set_plist_value CFBundleIdentifier com.snailjoss.pssezhao
  set_plist_value CFBundleName PS-Sezhao
  set_plist_value CFBundleDisplayName PS-Sezhao
  set_plist_value CFBundleShortVersionString "$VERSION"
  set_plist_value CFBundleVersion "$VERSION"
  set_plist_value NSHighResolutionCapable true

  test "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$PLIST_PATH")" = "com.snailjoss.pssezhao"
  test "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$PLIST_PATH")" = "$VERSION"
}

sign_and_notarize_app() {
  local keychain="$RUNNER_TEMP/ps-sezhao-signing.keychain-db"
  local certificate="$RUNNER_TEMP/ps-sezhao-certificate.p12"
  local password
  password="$(openssl rand -hex 20)"

  printf '%s' "$APPLE_CERTIFICATE_P12_BASE64" | openssl base64 -d -A > "$certificate"
  security create-keychain -p "$password" "$keychain"
  security set-keychain-settings -lut 21600 "$keychain"
  security unlock-keychain -p "$password" "$keychain"
  security import "$certificate" -k "$keychain" -P "$APPLE_CERTIFICATE_PASSWORD" -T /usr/bin/codesign
  security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$password" "$keychain"
  security list-keychains -d user -s "$keychain" login.keychain-db

  codesign --force --deep --options runtime --timestamp \
    --sign "$APPLE_SIGNING_IDENTITY" "$APP_PATH"
  codesign --verify --deep --strict --verbose=2 "$APP_PATH"

  ditto -c -k --keepParent "$APP_PATH" "$RUNNER_TEMP/PS-Sezhao-notarize.zip"
  xcrun notarytool submit "$RUNNER_TEMP/PS-Sezhao-notarize.zip" \
    --apple-id "$APPLE_ID" \
    --password "$APPLE_APP_SPECIFIC_PASSWORD" \
    --team-id "$APPLE_TEAM_ID" \
    --wait
  xcrun stapler staple "$APP_PATH"
  xcrun stapler validate "$APP_PATH"
  spctl --assess --type execute --verbose=4 "$APP_PATH"
  SIGNED_BUILD=1
}

rm -rf "$RELEASE_DIR" lr-stage portable-stage dmg-stage
mkdir -p "$RELEASE_DIR" lr-stage/PS-Sezhao.lrplugin/bin/macos-arm64
mkdir -p portable-stage/PS-Sezhao/project portable-stage/PS-Sezhao/lut portable-stage/PS-Sezhao/logs dmg-stage

write_bundle_metadata

if require_signing_secrets; then
  echo "Apple signing credentials detected; signing and notarizing the app."
  sign_and_notarize_app
else
  echo "::warning::Apple signing secrets are not configured. Applying an ad-hoc signature; Gatekeeper will still require manual confirmation."
  codesign --force --deep --sign - "$APP_PATH"
  codesign --verify --deep --strict --verbose=2 "$APP_PATH"
fi

cp -R lightroom-classic/PS-Sezhao.lrplugin/. lr-stage/PS-Sezhao.lrplugin/
cp -R "$APP_PATH" lr-stage/PS-Sezhao.lrplugin/bin/macos-arm64/
cp -R "$APP_PATH" portable-stage/PS-Sezhao/
cp standalone/installer/INSTALL.zh-CN.html portable-stage/PS-Sezhao/安装说明.html
printf '%s\n' 'PS-Sezhao portable data root.' > portable-stage/PS-Sezhao/.ps-sezhao-portable
printf '%s\n' 'Project archives and backups are stored here.' > portable-stage/PS-Sezhao/project/README.txt
printf '%s\n' 'Place standard .cube LUT files here.' > portable-stage/PS-Sezhao/lut/README.txt
printf '%s\n' 'Startup diagnostics are stored here.' > portable-stage/PS-Sezhao/logs/README.txt

ditto -c -k --sequesterRsrc --keepParent portable-stage/PS-Sezhao \
  "$RELEASE_DIR/PS-Sezhao-Standalone-macOS-arm64-v${VERSION}.zip"
ditto -c -k --sequesterRsrc --keepParent lr-stage/PS-Sezhao.lrplugin \
  "$RELEASE_DIR/PS-Sezhao-LightroomClassic-macOS-arm64-v${VERSION}.zip"

cp -R "$APP_PATH" dmg-stage/PS-Sezhao.app
ln -s /Applications dmg-stage/Applications
cp standalone/installer/INSTALL.zh-CN.html dmg-stage/安装说明.html
cat > dmg-stage/拖动安装.txt <<'EOF'
请将 PS-Sezhao.app 拖到右侧的 Applications 文件夹。
安装后从 Finder 的“应用程序”打开。
首次成功启动时，程序会自动在以下位置创建 project、lut 和 logs：
~/Library/Application Support/PS-Sezhao/
数据库 workspace.sqlite3 仍保留在该目录根部。
EOF

hdiutil create -quiet -format UDZO -fs HFS+ \
  -volname "PS-Sezhao Installer" \
  -srcfolder dmg-stage \
  "$RELEASE_DIR/PS-Sezhao-Installer-macOS-arm64-v${VERSION}.dmg"

if [[ "$SIGNED_BUILD" == "1" ]]; then
  codesign --force --timestamp --sign "$APPLE_SIGNING_IDENTITY" \
    "$RELEASE_DIR/PS-Sezhao-Installer-macOS-arm64-v${VERSION}.dmg"
  xcrun notarytool submit "$RELEASE_DIR/PS-Sezhao-Installer-macOS-arm64-v${VERSION}.dmg" \
    --apple-id "$APPLE_ID" \
    --password "$APPLE_APP_SPECIFIC_PASSWORD" \
    --team-id "$APPLE_TEAM_ID" \
    --wait
  xcrun stapler staple "$RELEASE_DIR/PS-Sezhao-Installer-macOS-arm64-v${VERSION}.dmg"
  xcrun stapler validate "$RELEASE_DIR/PS-Sezhao-Installer-macOS-arm64-v${VERSION}.dmg"
fi
