# PS-Sezhao v0.7.0-beta.4 安装与使用说明

## 独立桌面版

### macOS Apple Silicon

1. 下载 `PS-Sezhao-Installer-macOS-arm64-v0.7.0-beta.4.dmg`。
2. 打开 DMG。
3. 将 `PS-Sezhao.app` 拖到右侧 `Applications` 文件夹。
4. 从 Finder 的“应用程序”中打开 PS-Sezhao。

Beta 4 不再要求运行 `.command` 安装脚本。应用程序会直接出现在 macOS 的“应用程序”窗口中。

已使用 Apple Developer ID 签名并完成公证的构建可以正常双击打开；未签名的测试构建仍会被 Gatekeeper 要求手动确认。仓库构建流程已经支持自动签名和公证，但发布者必须先配置 Apple Developer Program 证书和公证凭据。

macOS 安装版的数据保存在：

```text
~/Library/Application Support/PS-Sezhao/
├── workspace.sqlite3
└── lut/
```

数据库沿用原位置，不写入 `.app`，更新或替换 App 不会删除胶卷项目。

### Windows x64

1. 下载并运行 `PS-Sezhao-Installer-Windows-x64-v0.7.0-beta.4.exe`。
2. 默认安装到 `%LOCALAPPDATA%\Programs\PS-Sezhao\`。
3. 安装器会创建开始菜单快捷方式，并可选择创建桌面快捷方式。
4. SmartScreen 出现时，确认文件来自本仓库 Release，再选择“更多信息 → 仍要运行”。

Windows 安装版继续使用应用同级的：

```text
project\workspace.sqlite3
lut\
```

## 便携 ZIP

- `PS-Sezhao-Standalone-macOS-arm64-v0.7.0-beta.4.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.7.0-beta.4.zip`

便携版必须保留完整外层 `PS-Sezhao` 文件夹：

```text
PS-Sezhao/
├── PS-Sezhao.app 或 PS-Sezhao.exe
├── project/
│   └── workspace.sqlite3
├── lut/
├── 安装说明.html
└── .ps-sezhao-portable
```

## 启动与关闭

- 普通启动时不再自动打开上次关闭时的照片；
- 已保存的胶卷项目仍可通过左侧“打开”手动恢复；
- 关闭程序且当前有照片时，会询问是否保存本次胶卷项目；
- 选择“是”：保存项目后退出；
- 选择“否”：直接退出，并清空临时照片列表；
- 选择“取消”：返回程序继续处理；
- 临时工作区选择保存时，会要求输入胶卷项目名称。

## 用户 LUT

右侧“胶卷风格”区域提供“添加 LUT…”和“打开 LUT 文件夹”。支持标准 1D/3D `.cube` 文件。macOS 安装版 LUT 位于：

```text
~/Library/Application Support/PS-Sezhao/lut/
```

Windows 安装版和两平台便携版使用应用外层同级 `lut` 文件夹。

## Photoshop 2024（25.0）或更高版本

1. 下载 `PS-Sezhao-Photoshop-v0.7.0-beta.4.ccx`。
2. 完全退出 Photoshop。
3. 双击 CCX，通过 Creative Cloud Desktop 安装。
4. 重新打开 Photoshop，从 `插件 → 胶片去色罩` 启动。

开发者加载版为 `PS-Sezhao-Photoshop-Developer-v0.7.0-beta.4.zip`。

## Lightroom Classic 15.4+

- Apple Silicon Mac：`PS-Sezhao-LightroomClassic-macOS-arm64-v0.7.0-beta.4.zip`
- Windows x64：`PS-Sezhao-LightroomClassic-Windows-x64-v0.7.0-beta.4.zip`

退出 Lightroom Classic，解压下载文件，在插件管理器中移除旧记录后，重新添加完整的 `PS-Sezhao.lrplugin` 文件夹。
