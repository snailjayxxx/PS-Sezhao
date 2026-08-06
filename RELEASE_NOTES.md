# PS-Sezhao v0.7.2

v0.7.2 是针对 macOS Apple Silicon 独立版无法稳定启动或退出的紧急修复版本。

## 修复内容

- macOS 独立版不再加载原生 TkDND/TkinterDnD 扩展；
- 修复 TkDND 在 Tk/Tcl 窗口初始化、重绘或销毁期间回调 Python，导致 `PyEval_RestoreThread`、`SIGABRT` 和 `Abort trap: 6` 的崩溃；
- macOS 构建中完全排除 TkDND 动态库，避免仅靠运行时回退仍被意外加载；
- Finder 拖放在 macOS 上暂时停用，请使用“添加图像”和“添加文件夹”；
- Windows 拖放功能保持不变；
- macOS 应用的 `CFBundleIdentifier`、`CFBundleShortVersionString` 和 `CFBundleVersion` 现在正确写入，不再显示 `0.0.0`；
- 新增 macOS 打包检查：应用必须报告拖放已停用，并且包内不得包含 TkDND 运行时。

## 未改变的功能

- 彩色负片和相机翻拍转正；
- 相机 RAW；
- 完整裁切、旋转、拉直、翻转和四角透视；
- 整卷项目、项目归档、数据库备份恢复；
- 用户 1D/3D Cube LUT；
- TIFF、PNG、JPEG、ICC、尺寸调整、锐化、命名模板和接触印样；
- Photoshop 和 Lightroom Classic 插件。

## macOS 安装

1. 删除“应用程序”中的旧版 `PS-Sezhao.app`。
2. 下载并打开 `PS-Sezhao-Installer-macOS-arm64-v0.7.2.dmg`。
3. 将 `PS-Sezhao.app` 拖到右侧 `Applications`。
4. 从 Finder 的“应用程序”中打开，不要直接在 DMG 或下载目录里运行。

已有数据库、项目和 LUT 位于：

```text
~/Library/Application Support/PS-Sezhao/
```

删除或替换 App 不会删除这些数据。

## 发行文件

- `PS-Sezhao-Photoshop-v0.7.2.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.7.2.zip`
- `PS-Sezhao-LightroomClassic-Source-v0.7.2.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.7.2.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.7.2.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.7.2.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.7.2.zip`
- `PS-Sezhao-Installer-macOS-arm64-v0.7.2.dmg`
- `PS-Sezhao-Installer-Windows-x64-v0.7.2.exe`
- `CHECKSUMS.txt`
