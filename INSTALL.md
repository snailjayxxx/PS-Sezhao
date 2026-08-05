# PS-Sezhao v0.5.3 安装与使用说明

## Photoshop 2024（25.0）或更高版本

### CCX 安装

1. 下载 `PS-Sezhao-Photoshop-v0.5.3.ccx`。
2. 完全退出 Photoshop。
3. 双击 CCX，通过 Creative Cloud Desktop 安装。
4. 重新打开 Photoshop，从 `插件 → 胶片去色罩` 启动。
5. 确认顶部显示 `PS-SEZHAO · 0.5.3`。

胶片基底吸管只读取被记录的原始负片图层。面板下方“胶片基底微调”支持 R/G/B 数字输入、`− / +`和 `-255～+255` 范围。

### UXP Developer Tool 加载

1. 下载并解压 `PS-Sezhao-Photoshop-Developer-v0.5.3.zip`。
2. 启动 Photoshop 2024 或更高版本。
3. 启动 Adobe UXP Developer Tool 并启用 Developer Mode。
4. 点击 `Add Plugin`，选择解压目录中的 `manifest.json`。
5. 点击 `Load`。

开发者加载只改变插件加载方式，不会激活 Photoshop、修改 Creative Cloud 或绕过 Adobe 授权。

## Lightroom Classic 15.4+

Apple Silicon Mac 下载 `PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.3.zip`。

Windows x64 下载 `PS-Sezhao-LightroomClassic-Windows-x64-v0.5.3.zip`。

1. 完全退出 Lightroom Classic。
2. 删除或移走旧的 `PS-Sezhao.lrplugin`，不要覆盖旧目录。
3. 解压新版，重新打开 Lightroom Classic。
4. 进入 `文件 → 增效工具管理器`，移除旧条目。
5. 点击“添加”，选择新的 `PS-Sezhao.lrplugin`。
6. 确认显示 `PS-Sezhao 0.5.3`。

### 原生直接转正

```text
图库 → 增效工具额外功能
→ PS-Sezhao：原生直接转正所选照片（默认）
```

该模式直接写入 Lightroom 非破坏性调整，不生成新文件。该模式没有独立调色窗口，因此不提供吸管或手动基底面板。

### 高精度 16 位 TIFF

```text
图库 → 增效工具额外功能
→ PS-Sezhao：高精度 16 位 TIFF
```

Lightroom 先将照片渲染为16位ProPhoto RGB TIFF，再打开与独立版相同的多图窗口。原图吸管、`-255～+255`基底微调、新裁切方式、侧栏滚轮和批量导回均可使用。

## 独立桌面版

### macOS Apple Silicon

1. 下载并解压 `PS-Sezhao-Standalone-macOS-arm64-v0.5.3.zip`。
2. 将 `PS-Sezhao.app` 移到“应用程序”。
3. 首次启动若提示无法验证开发者，在 Finder 中右键应用，选择“打开”，再确认“打开”。
4. 新版 macOS 仍阻止时，进入 `系统设置 → 隐私与安全性`，找到 PS-Sezhao 并点击“仍要打开”。

### Windows x64

1. 下载并解压 `PS-Sezhao-Standalone-Windows-x64-v0.5.3.zip`。
2. 运行 `PS-Sezhao.exe`。
3. SmartScreen 出现时，确认文件来自本仓库 Release，再选择“更多信息 → 仍要运行”。

独立版不要求安装 Photoshop、Lightroom、Creative Cloud、Python、rawpy 或 LibRaw。

## 左右侧栏滚动

- 鼠标放在右侧参数栏，滚轮上下浏览所有参数；
- 鼠标放在左侧图片列表，滚轮上下浏览图片；
- Windows 鼠标和精密触控板、macOS 鼠标/触控板均支持；
- 中间图片预览区的滚轮仍用于放大和缩小；
- 放大后通过“平移”工具拖动画面。

## 手动修改胶片基底

右侧滚动到“胶片基底手动微调 · v0.5.3”。

- R、G、B 各有滑块；
- 数字框可直接输入 `-255` 到 `255`；
- `− / +` 每次调整1个8位等效单位；
- 输入框内按上下方向键也可微调；
- 顶部显示原图识别值和当前实际使用值；
- “重置胶片基底微调”将三通道恢复为0。

扩大的是吸管或自动分析结果上的手动偏移；吸管本身仍读取未调色、未转正的原始输入像素。

## 裁切流程

1. 平时只显示裁切后保留的画面。
2. 点击“裁切”，显示完整照片和当前裁切框。
3. 拖动角点、边中点或框内区域调整。
4. 点击“完成裁切”，重新只显示保留范围。
5. 再次点击“裁切”，恢复完整照片和上次裁切框。

“自动分析边框”只使用当前裁切范围。裁切区域没有未曝光胶片边框时，应使用胶片基底吸管。

## 相机 RAW

“添加图像”或“添加文件夹”可加入：

```text
CR2 / CR3 / NEF / NRW / ARW / RAF / RW2 / ORF / PEF / SRW / DNG
```

完整解码固定为16位、线性Gamma、ProPhoto RGB并关闭自动提亮。若 LibRaw 不支持相机或压缩方式，可先导出16位TIFF。

## 多图和导出

- 一次选择多张图片或扫描文件夹；
- 每张图片保存自己的分析、基底微调、调色参数和裁切；
- 参数和裁切可同步到选中照片；
- 可保存当前、导出选中或导出全部；
- RAW 批量导出逐张解码、处理、保存和释放内存。

## 关于第三方修改版 Adobe 软件

本项目不提供绕过 Adobe 授权、修改 Creative Cloud 或破解插件验证的方法。无法使用 Adobe 宿主时，可使用独立桌面版。
