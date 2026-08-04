# PS-Sezhao v0.3.1 安装说明

## Photoshop 2024（25.0）或更高版本

### 推荐：CCX 安装

1. 下载 `PS-Sezhao-Photoshop-v0.3.1.ccx`。
2. 完全退出 Photoshop。
3. 双击 CCX，通过 Creative Cloud Desktop 安装。
4. 重新打开 Photoshop，从 `插件 → 胶片去色罩` 启动。
5. 确认插件顶部显示 `PS-SEZHAO · 0.3.1`。

发布流水线会自动确认 CCX 的 `manifest.json` 位于包根目录，并核对版本、宿主和最低 Photoshop 版本，避免多套一层目录造成安装错误。

### 备用：UXP Developer Tool 加载

当 CCX 安装器不可用，或需要查看插件加载日志时：

1. 下载并解压 `PS-Sezhao-Photoshop-Developer-v0.3.1.zip`。
2. 启动 Photoshop 2024 或更高版本。
3. 启动 Adobe UXP Developer Tool，并启用 Developer Mode。
4. 点击 `Add Plugin`，选择解压目录中的 `manifest.json`。
5. 点击 `Load`。
6. 回到 Photoshop，从 `插件 → 胶片去色罩` 打开。

完整说明见 [PHOTOSHOP_DEVELOPER_LOAD.md](PHOTOSHOP_DEVELOPER_LOAD.md)。开发者加载只改变插件加载方式，不会激活 Photoshop、修改 Creative Cloud 或绕过 Adobe 授权。

## Lightroom Classic 15.4+

### Apple Silicon Mac

1. 下载并解压 `PS-Sezhao-LightroomClassic-macOS-arm64-v0.3.1.zip`。
2. 打开 Lightroom Classic。
3. 进入 `文件 → 增效工具管理器`。
4. 点击“添加”，选择 `PS-Sezhao.lrplugin` 文件夹。
5. 从 `图库 → 增效工具额外功能 → PS-Sezhao：转正所选负片` 启动。

### Windows x64

步骤相同，但下载 `PS-Sezhao-LightroomClassic-Windows-x64-v0.3.1.zip`。

Lightroom 插件包已经包含对应平台的本地处理器，不要求用户安装 Python。

## 不使用 Adobe：独立桌面版

### macOS Apple Silicon

1. 下载并解压 `PS-Sezhao-Standalone-macOS-arm64-v0.3.1.zip`。
2. 将 `PS-Sezhao.app` 移到“应用程序”。
3. 首次启动若被 Gatekeeper 阻止，请在 Finder 中右键应用并选择“打开”。

### Windows x64

1. 下载并解压 `PS-Sezhao-Standalone-Windows-x64-v0.3.1.zip`。
2. 运行 `PS-Sezhao.exe`。

独立版不需要 Photoshop、Lightroom、Creative Cloud、Python 或 Node.js。

## Photoshop 2024 兼容提醒

- Photoshop 2024 对应 25.x 系列。
- 插件清单最低版本为 `25.0.0`。
- v0.3.1 已移除需要 Photoshop 25.10 才支持的模态超时选项。
- 较早的 25.x 小版本若出现 UXP 宿主问题，建议先更新到 Photoshop 2024 系列的最新补丁版，而不必升级到 2025/2026。

## 关于第三方修改版 Adobe 软件

本项目不提供绕过 Adobe 授权、修改 Creative Cloud 或破解插件验证的方法。UXP Developer Tool 可以用于源码加载和调试，但不能补回被第三方删除的 UXP 组件，也不能保证修改版宿主的兼容性。无法使用 Adobe 宿主时，可使用独立桌面版完成胶片转正，再将 TIFF/JPEG 导入任意图像软件。
