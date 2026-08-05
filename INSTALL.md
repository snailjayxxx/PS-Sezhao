# PS-Sezhao v0.5.2 安装与使用说明

## Photoshop 2024（25.0）或更高版本

### CCX 安装

1. 下载 `PS-Sezhao-Photoshop-v0.5.2.ccx`。
2. 完全退出 Photoshop。
3. 双击 CCX，通过 Creative Cloud Desktop 安装。
4. 重新打开 Photoshop，从 `插件 → 胶片去色罩` 启动。
5. 确认顶部显示 `PS-SEZHAO · 0.5.2`。

胶片基底吸管显示的虽然可以是转正预览，但实际读取的是被记录的原始负片图层。面板下方“胶片基底微调”可手动调整 R/G/B，并支持数字输入和 `− / +`。

### UXP Developer Tool 加载

1. 下载并解压 `PS-Sezhao-Photoshop-Developer-v0.5.2.zip`。
2. 启动 Photoshop 2024 或更高版本。
3. 启动 Adobe UXP Developer Tool 并启用 Developer Mode。
4. 点击 `Add Plugin`，选择解压目录中的 `manifest.json`。
5. 点击 `Load`。

开发者加载只改变插件加载方式，不会激活 Photoshop、修改 Creative Cloud 或绕过 Adobe 授权。

## Lightroom Classic 15.4+

### 安装

Apple Silicon Mac 下载 `PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.2.zip`。

Windows x64 下载 `PS-Sezhao-LightroomClassic-Windows-x64-v0.5.2.zip`。

1. 完全退出 Lightroom Classic。
2. 删除或移走旧的 `PS-Sezhao.lrplugin`，不要覆盖旧目录。
3. 解压新版，重新打开 Lightroom Classic。
4. 进入 `文件 → 增效工具管理器`，移除旧条目。
5. 点击“添加”，选择新的 `PS-Sezhao.lrplugin`。
6. 确认显示 `PS-Sezhao 0.5.2`。

### 原生直接转正

```text
图库 → 增效工具额外功能
→ PS-Sezhao：原生直接转正所选照片（默认）
```

该模式直接写入 Lightroom 非破坏性调整，不生成新文件。建议保持“应用前创建恢复快照”开启。该模式没有独立调色窗口，因此不提供吸管或手动基底面板。

### 高精度 16 位 TIFF

```text
图库 → 增效工具额外功能
→ PS-Sezhao：高精度 16 位 TIFF
```

Lightroom 先将照片渲染为16位ProPhoto RGB TIFF，再打开与独立版相同的多图窗口。原图吸管、基底 R/G/B 手动微调、新裁切方式和批量导回均可使用。

## 独立桌面版

### macOS Apple Silicon

1. 下载并解压 `PS-Sezhao-Standalone-macOS-arm64-v0.5.2.zip`。
2. 将 `PS-Sezhao.app` 移到“应用程序”。
3. 首次启动若提示无法验证开发者，在 Finder 中右键应用，选择“打开”，再确认“打开”。
4. 新版 macOS 仍阻止时，进入 `系统设置 → 隐私与安全性`，在安全区域找到 PS-Sezhao，点击“仍要打开”。
5. 只对从本仓库 Release 下载且来源可信的文件执行以上操作。

### Windows x64

1. 下载并解压 `PS-Sezhao-Standalone-Windows-x64-v0.5.2.zip`。
2. 运行 `PS-Sezhao.exe`。
3. Windows SmartScreen 出现时，先确认文件来自本仓库 Release，再选择“更多信息 → 仍要运行”。

独立版不要求安装 Photoshop、Lightroom、Creative Cloud、Python、rawpy 或 LibRaw。

## 胶片基底吸管

1. 点击“吸管：胶片基底”。
2. 点击未曝光的橙色胶片边框。
3. 程序把当前可见位置换算到完整原图坐标。
4. 取样读取未调色、未转正的原始输入像素。
5. 黑白范围按当前裁切区域重新计算。

曝光、色温、RGB增益、风格和预览效果不会改变吸管读取的基底颜色。

## 手动修改胶片基底

右侧滚动到“胶片基底手动微调 · v0.5.2”。

- R、G、B 各有滑块；
- 数字框可直接输入 `-64` 到 `64`；
- `− / +` 每次调整1个8位等效单位；
- 输入框内按上下方向键也可微调；
- 顶部会显示原图识别值和当前实际使用值；
- “重置胶片基底微调”将三通道恢复为0。

## 新裁切流程

### 应用状态

平时只显示裁切后保留的画面，不显示裁切框、遮罩或被裁掉的部分。

### 编辑状态

1. 点击预览上方的“裁切”。
2. 程序显示完整照片和当前裁切框。
3. 拖动四个角调整宽高。
4. 拖动四边中点只调整一条边。
5. 拖动框内区域移动整个裁切框。
6. 在框外按下并拖动，可重新建立裁切范围。
7. 点击“完成裁切”。
8. 程序重新只显示裁切后的画面。

再次点击“裁切”，会重新显示完整照片和上一次的裁切框。“重置裁切”恢复完整画面。

## 自动分析边框

“自动分析边框”只使用当前裁切范围。完成裁切或重置裁切后：

- 自动分析得到的基底会按新范围重新计算；
- 吸管取得的原图基底颜色会保留，只重新计算新范围内的黑白点；
- 批量处理中没有保存分析结果的照片，也会先裁切再分析。

裁切区域没有未曝光胶片边框时，自动分析可能失败，此时应使用胶片基底吸管。

## 相机 RAW

“添加图像”或“添加文件夹”可加入常见 RAW：

```text
CR2 / CR3 / NEF / NRW / ARW / RAF / RW2 / ORF / PEF / SRW / DNG
```

右侧 RAW 设置提供相机、日光、自动和自定义白平衡，高光处理、去马赛克方式、内嵌预览优先和重新解码。完整解码固定为16位、线性Gamma、ProPhoto RGB并关闭自动提亮。

若 LibRaw 不支持相机或压缩方式，可先用 Lightroom Classic、Camera Raw 或相机厂商软件导出16位TIFF。

## 多图和导出

- “添加图像”一次选择多张；
- “添加文件夹”扫描文件夹及可选子文件夹；
- 每张图片保存自己的分析、基底微调、调色参数和裁切；
- 参数和裁切可同步到选中照片；
- 可保存当前、导出选中或导出全部；
- RAW 批量导出逐张解码、处理、保存和释放内存。

## 关于第三方修改版 Adobe 软件

本项目不提供绕过 Adobe 授权、修改 Creative Cloud 或破解插件验证的方法。无法使用 Adobe 宿主时，可使用独立桌面版处理 RAW、TIFF 或常规图像。
