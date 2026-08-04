# PS-Sezhao v0.3.0 安装说明

## Photoshop 27.8+

1. 下载 `PS-Sezhao-Photoshop-v0.3.0.ccx`。
2. 完全退出 Photoshop。
3. 双击 CCX，通过 Creative Cloud Desktop 安装。
4. 重新打开 Photoshop，从 `插件 → 胶片去色罩` 启动。

## Lightroom Classic 15.4+

### Apple Silicon Mac

1. 下载并解压 `PS-Sezhao-LightroomClassic-macOS-arm64-v0.3.0.zip`。
2. 打开 Lightroom Classic。
3. 进入 `文件 → 增效工具管理器`。
4. 点击“添加”，选择 `PS-Sezhao.lrplugin` 文件夹。
5. 从 `图库 → 增效工具额外功能 → PS-Sezhao：转正所选负片` 启动。

### Windows x64

步骤相同，但下载 `PS-Sezhao-LightroomClassic-Windows-x64-v0.3.0.zip`。

Lightroom 插件包已经包含对应平台的本地处理器，不要求用户安装 Python。

## 不使用 Adobe：独立桌面版

### macOS Apple Silicon

1. 下载并解压 `PS-Sezhao-Standalone-macOS-arm64-v0.3.0.zip`。
2. 将 `PS-Sezhao.app` 移到“应用程序”。
3. 首次启动若被 Gatekeeper 阻止，请在 Finder 中右键应用并选择“打开”。

### Windows x64

1. 下载并解压 `PS-Sezhao-Standalone-Windows-x64-v0.3.0.zip`。
2. 运行 `PS-Sezhao.exe`。

独立版不需要 Photoshop、Lightroom、Creative Cloud、Python 或 Node.js。

## 关于非正版 Adobe 软件

本项目不会提供绕过 Adobe 授权、修改 Creative Cloud、破解 CCX/LR 插件验证或针对第三方修改版宿主的适配。此类环境的插件接口经常不完整，也无法可靠测试。用户可以合法、完整地使用独立桌面版完成胶片转正，再把 TIFF/JPEG 导入任意图像软件。
