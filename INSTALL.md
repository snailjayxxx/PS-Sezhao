# PS-Sezhao v0.5.0 安装与使用说明

## Photoshop 2024（25.0）或更高版本

### CCX 安装

1. 下载 `PS-Sezhao-Photoshop-v0.5.0.ccx`。
2. 完全退出 Photoshop。
3. 双击 CCX，通过 Creative Cloud Desktop 安装。
4. 重新打开 Photoshop，从 `插件 → 胶片去色罩` 启动。
5. 确认顶部显示 `PS-SEZHAO · 0.5.0`。

每个主要滑块下方都有：

```text
−　数字输入框　+
```

可以直接输入数值并按 Enter，也可以用加减按钮或输入框中的上下方向键微调。

### UXP Developer Tool 加载

1. 下载并解压 `PS-Sezhao-Photoshop-Developer-v0.5.0.zip`。
2. 启动 Photoshop 2024 或更高版本。
3. 启动 Adobe UXP Developer Tool 并启用 Developer Mode。
4. 点击 `Add Plugin`，选择解压目录中的 `manifest.json`。
5. 点击 `Load`。

开发者加载只改变插件加载方式，不会激活 Photoshop、修改 Creative Cloud 或绕过 Adobe 授权。

## Lightroom Classic 15.4+

### Apple Silicon Mac

1. 下载并解压 `PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.0.zip`。
2. 完全退出 Lightroom Classic。
3. 删除或移走旧的 `PS-Sezhao.lrplugin`，不要覆盖旧目录。
4. 重新打开 Lightroom Classic，进入 `文件 → 增效工具管理器`。
5. 移除旧条目，点击“添加”，选择新的 `PS-Sezhao.lrplugin`。
6. 确认显示 `PS-Sezhao 0.5.0`。

Windows x64 使用 `PS-Sezhao-LightroomClassic-Windows-x64-v0.5.0.zip`，步骤相同。

### 原生直接转正

```text
图库 → 增效工具额外功能
→ PS-Sezhao：原生直接转正所选照片（默认）
```

该模式直接写入 Lightroom 非破坏性调整，不生成新文件。建议保持“应用前创建恢复快照”开启。

### 高精度 16 位 TIFF

```text
图库 → 增效工具额外功能
→ PS-Sezhao：高精度 16 位 TIFF
```

v0.5.0 的高精度窗口支持：

- 多张照片列表；
- 每张照片独立参数；
- 参数和裁切同步到选中照片；
- 缩放、平移和非破坏性裁切；
- 每张照片分别生成 16 位 TIFF；
- 完成后自动导回 Lightroom。

## 独立桌面版

### macOS Apple Silicon

1. 下载并解压 `PS-Sezhao-Standalone-macOS-arm64-v0.5.0.zip`。
2. 将 `PS-Sezhao.app` 移到“应用程序”。
3. 首次启动若被 Gatekeeper 阻止，在 Finder 中右键应用并选择“打开”。

### Windows x64

1. 下载并解压 `PS-Sezhao-Standalone-Windows-x64-v0.5.0.zip`。
2. 运行 `PS-Sezhao.exe`。

独立版不要求安装 Photoshop、Lightroom、Creative Cloud、Python 或 Node.js。

## 独立版操作

### 添加多张图片

- 点击“添加图像”一次选择多张；
- 点击“添加文件夹”导入整个文件夹；
- 可选择是否包含子文件夹；
- 左侧列表支持多选、上一张和下一张。

### 缩放和平移

- 鼠标滚轮缩放；
- `− / +` 控制预览缩放；
- “适应”“100%”“200%”快速切换；
- 选择“平移”后拖动画面；
- `Ctrl/Cmd + 0` 适应窗口，`Ctrl/Cmd + 1` 显示 100%。

### 非破坏性裁切

1. 选择“裁切”。
2. 在预览上拖出裁切矩形。
3. 需要整卷相同裁切时，多选图片并点击“同步裁切到选中”。
4. 点击“重置裁切”恢复完整画面。

裁切只在导出时应用，原图不会修改。

### 批量输出

- “保存当前”：只保存当前图片；
- “导出选中”：保存左侧多选图片；
- “导出全部”：保存列表全部图片；
- 每张图片使用自己的分析结果、调色参数和裁切。

## 关于第三方修改版 Adobe 软件

本项目不提供绕过 Adobe 授权、修改 Creative Cloud 或破解插件验证的方法。无法使用 Adobe 宿主时，可使用独立桌面版处理并导出 TIFF/JPEG。
