# PS-Sezhao v0.5.1 安装与使用说明

## Photoshop 2024（25.0）或更高版本

### CCX 安装

1. 下载 `PS-Sezhao-Photoshop-v0.5.1.ccx`。
2. 完全退出 Photoshop。
3. 双击 CCX，通过 Creative Cloud Desktop 安装。
4. 重新打开 Photoshop，从 `插件 → 胶片去色罩` 启动。
5. 确认顶部显示 `PS-SEZHAO · 0.5.1`。

主要滑块提供 `− / 数字输入框 / +`。可直接输入后按 Enter，也可通过按钮或上下方向键微调。

### UXP Developer Tool 加载

1. 下载并解压 `PS-Sezhao-Photoshop-Developer-v0.5.1.zip`。
2. 启动 Photoshop 2024 或更高版本。
3. 启动 Adobe UXP Developer Tool 并启用 Developer Mode。
4. 点击 `Add Plugin`，选择解压目录中的 `manifest.json`。
5. 点击 `Load`。

开发者加载只改变插件加载方式，不会激活 Photoshop、修改 Creative Cloud 或绕过 Adobe 授权。

## Lightroom Classic 15.4+

### 安装

Apple Silicon Mac 下载：

```text
PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.1.zip
```

Windows x64 下载：

```text
PS-Sezhao-LightroomClassic-Windows-x64-v0.5.1.zip
```

1. 完全退出 Lightroom Classic。
2. 删除或移走旧的 `PS-Sezhao.lrplugin`，不要覆盖旧目录。
3. 解压新版，重新打开 Lightroom Classic。
4. 进入 `文件 → 增效工具管理器`，移除旧条目。
5. 点击“添加”，选择新的 `PS-Sezhao.lrplugin`。
6. 确认显示 `PS-Sezhao 0.5.1`。

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

Lightroom 先将当前照片渲染为 16 位 ProPhoto RGB TIFF，再打开多图窗口。支持逐张参数、缩放、平移、裁切和批量导回。Lightroom 中的 RAW 仍由 Lightroom 解码，不使用独立版 RAW 设置。

## 独立桌面版

### macOS Apple Silicon

1. 下载并解压 `PS-Sezhao-Standalone-macOS-arm64-v0.5.1.zip`。
2. 将 `PS-Sezhao.app` 移到“应用程序”。
3. 首次启动若提示无法验证开发者，在 Finder 中右键应用，选择“打开”，再确认“打开”。
4. 新版 macOS 仍阻止时，进入 `系统设置 → 隐私与安全性`，在安全区域找到 PS-Sezhao，点击“仍要打开”。
5. 只对从本仓库 Release 下载且来源可信的文件执行以上操作。

### Windows x64

1. 下载并解压 `PS-Sezhao-Standalone-Windows-x64-v0.5.1.zip`。
2. 运行 `PS-Sezhao.exe`。
3. Windows SmartScreen 出现时，先确认文件来自本仓库 Release，再选择“更多信息 → 仍要运行”。

独立版不要求安装 Photoshop、Lightroom、Creative Cloud、Python、rawpy 或 LibRaw；所需 RAW 运行库已包含在发行包内。

## 直接打开相机 RAW

点击“添加图像”或“添加文件夹”，可加入常见 RAW：

```text
CR2 / CR3 / NEF / NRW / ARW / RAF / RW2 / ORF / PEF / SRW / DNG
```

### RAW 设置

右侧“相机 RAW 解码 · v0.5.1”区域包含：

- **相机拍摄白平衡**：使用相机写入的白平衡，默认选择；
- **日光白平衡**：适合固定灯箱、统一翻拍条件；
- **自动白平衡**：由 LibRaw 估算；
- **自定义通道倍率**：输入 R、G、B、G2 四通道倍率；
- **高光处理**：混合、直接裁切或重建；
- **去马赛克**：AHD、线性、VNG 或 PPG；
- **优先读取内嵌预览**：切换图片时先快速显示；
- **半尺寸快速预览**：没有内嵌预览时降低等待时间；
- **重新解码当前 RAW**：修改解码设置后重新处理当前照片。

完整解码固定为16位、线性Gamma、ProPhoto RGB并关闭自动提亮。预览完成后仍会在后台加载完整RAW；最终导出不会使用内嵌JPEG预览。

### 不支持的 RAW

若安装包内的 LibRaw 不支持某个相机、压缩方式或多帧结构，程序会显示：

- 文件名；
- rawpy 与 LibRaw 版本；
- 可能的原因；
- 先导出16位TIFF的替代办法。

此时可使用 Lightroom Classic、Camera Raw或相机厂商软件导出16位TIFF，再加入PS-Sezhao。

## 多图、缩放、裁切和导出

- “添加图像”可一次选择多张；
- “添加文件夹”可扫描整个文件夹及子文件夹；
- 左侧列表支持多选、上一张和下一张；
- 每张图片保存自己的分析、参数和裁切；
- 滚轮缩放，平移模式拖动画面；
- 裁切模式拖出非破坏性矩形；
- 参数和裁切可同步到选中照片；
- 可保存当前、导出选中或导出全部。

RAW 批量导出会逐张完整解码、处理、保存和释放内存。默认输出16位TIFF并嵌入ProPhoto ICC。

## 关于第三方修改版 Adobe 软件

本项目不提供绕过 Adobe 授权、修改 Creative Cloud 或破解插件验证的方法。无法使用 Adobe 宿主时，可使用独立桌面版处理 RAW、TIFF 或常规图像。
