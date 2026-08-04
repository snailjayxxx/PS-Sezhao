# PS-Sezhao v0.4.0 安装说明

## Photoshop 2024（25.0）或更高版本

### 推荐：CCX 安装

1. 下载 `PS-Sezhao-Photoshop-v0.4.0.ccx`。
2. 完全退出 Photoshop。
3. 双击 CCX，通过 Creative Cloud Desktop 安装。
4. 重新打开 Photoshop，从 `插件 → 胶片去色罩` 启动。
5. 确认插件顶部显示 `PS-SEZHAO · 0.4.0`。

### 备用：UXP Developer Tool 加载

1. 下载并解压 `PS-Sezhao-Photoshop-Developer-v0.4.0.zip`。
2. 启动 Photoshop 2024 或更高版本。
3. 启动 Adobe UXP Developer Tool，并启用 Developer Mode。
4. 点击 `Add Plugin`，选择解压目录中的 `manifest.json`。
5. 点击 `Load`。

开发者加载只改变插件加载方式，不会激活 Photoshop、修改 Creative Cloud 或绕过 Adobe 授权。

## Lightroom Classic 15.4+

### Apple Silicon Mac

1. 下载并解压 `PS-Sezhao-LightroomClassic-macOS-arm64-v0.4.0.zip`。
2. **完全退出 Lightroom Classic**。
3. 删除或移走旧的 `PS-Sezhao.lrplugin` 文件夹，不要把新文件直接覆盖到旧目录。
4. 重新打开 Lightroom Classic，进入 `文件 → 增效工具管理器`。
5. 移除旧的 PS-Sezhao 条目。
6. 点击“添加”，选择新解压的 `PS-Sezhao.lrplugin` 文件夹。
7. 确认增效工具管理器显示 `PS-Sezhao 0.4.0`。

### Windows x64

步骤相同，但下载 `PS-Sezhao-LightroomClassic-Windows-x64-v0.4.0.zip`。

Lightroom 插件包包含对应平台的本地处理器，不要求用户安装 Python。

## Lightroom 使用方法

### 默认：直接修改 Lightroom 当前照片

1. 在图库中选择一张或多张负片。
2. 打开：

```text
图库 → 增效工具额外功能
→ PS-Sezhao：原生直接转正所选照片（默认）
```

3. 选择胶片起始风格，并输入附加曝光、色温、色调、明暗和饱和度。
4. 保持“应用前创建恢复快照”勾选。
5. 点击“直接应用”。
6. 进入“修改照片”模块继续调整。

原生模式不会创建新的图片文件。Lightroom 会把反相曲线和颜色参数保存为非破坏性调整。

### 恢复原生转正前状态

选择相应照片后打开：

```text
图库 → 增效工具额外功能
→ PS-Sezhao：恢复原生转正前状态
```

插件会应用最近一个名称以 `PS-Sezhao 原生转正前` 开头的快照。

### 高精度逐像素模式

需要胶片基底吸管、光密度算法或新 16 位 TIFF 时打开：

```text
图库 → 增效工具额外功能
→ PS-Sezhao：高精度 16 位 TIFF
```

该模式会生成新 TIFF，并自动导回 Lightroom。

## 不使用 Adobe：独立桌面版

### macOS Apple Silicon

1. 下载并解压 `PS-Sezhao-Standalone-macOS-arm64-v0.4.0.zip`。
2. 将 `PS-Sezhao.app` 移到“应用程序”。
3. 首次启动若被 Gatekeeper 阻止，请在 Finder 中右键应用并选择“打开”。

### Windows x64

1. 下载并解压 `PS-Sezhao-Standalone-Windows-x64-v0.4.0.zip`。
2. 运行 `PS-Sezhao.exe`。

独立版不需要 Photoshop、Lightroom、Creative Cloud、Python 或 Node.js。

## 关于第三方修改版 Adobe 软件

本项目不提供绕过 Adobe 授权、修改 Creative Cloud 或破解插件验证的方法。无法使用 Adobe 宿主时，可使用独立桌面版完成胶片转正，再将 TIFF/JPEG 导入其他图像软件。
