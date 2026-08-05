# PS-Sezhao 胶片去色罩

PS-Sezhao 是面向彩色负片扫描和相机翻拍的本地图像处理项目。同一个仓库同时发布：

- **Photoshop 版**：UXP `.ccx` 插件，直接读取和写入 Photoshop 图层。
- **Photoshop 开发者加载版**：完整 UXP 插件目录。
- **Lightroom Classic 版**：原生直接转正、高精度 16 位 TIFF、恢复快照。
- **独立桌面版**：不依赖 Adobe，支持相机 RAW 直读、多图、缩放、裁切和批量输出。

照片只在本机处理，不上传服务器。

## 当前版本

统一版本：**v0.5.2**

- Photoshop 2024（25.0）或更高版本
- Lightroom Classic 15.4 或更高版本
- macOS Apple Silicon
- Windows x64

## Release 文件

| 使用场景 | 下载文件 |
|---|---|
| Photoshop 正常安装 | `PS-Sezhao-Photoshop-v0.5.2.ccx` |
| Photoshop 开发者加载 | `PS-Sezhao-Photoshop-Developer-v0.5.2.zip` |
| Lightroom Classic · Apple Silicon | `PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.2.zip` |
| Lightroom Classic · Windows x64 | `PS-Sezhao-LightroomClassic-Windows-x64-v0.5.2.zip` |
| 独立桌面版 · Apple Silicon | `PS-Sezhao-Standalone-macOS-arm64-v0.5.2.zip` |
| 独立桌面版 · Windows x64 | `PS-Sezhao-Standalone-Windows-x64-v0.5.2.zip` |

## v0.5.2：原图吸管

胶片基底吸管不从转正或调色后的预览读取颜色：

- 独立版始终从 `preview_source` 对应的未修改输入图像取样；
- 裁切后点击可见画面时，坐标会先映射回完整原图；
- Photoshop 版从记录的原始负片图层读取像素，不读取临时预览图层；
- 基底颜色确定后，色调范围使用当前裁切区域重新计算。

因此，改变曝光、色温、RGB 增益或风格后重新吸取基底，不会把修改后的颜色误当成胶片基底。

## 胶片基底手动微调

独立桌面版和 Lightroom 高精度窗口新增：

```text
基底 R：滑块　−　数字输入　+
基底 G：滑块　−　数字输入　+
基底 B：滑块　−　数字输入　+
```

界面同时显示“原图识别值”和“当前实际使用值”。三通道偏移按8位等效单位调整，每张照片分别保存，也可通过参数同步功能应用到多张图片。

Photoshop 版原有“胶片基底微调”继续保留，并同样支持数字输入和加减按钮。

## 新裁切方式

- 平时只显示裁切后保留的画面；
- 不显示裁切框、遮罩或被裁掉的部分；
- 点击“裁切”后显示完整照片和当前裁切框；
- 可拖动四角、四边中点、整个框，也可在框外重新拖出范围；
- 点击“完成裁切”后重新只显示保留范围；
- 再次点击“裁切”会恢复完整照片和上次裁切框；
- 裁切仍是非破坏性的，只在导出时应用。

“自动分析边框”只分析裁切后的区域。完成或重置裁切时，会按新范围重新计算；批量任务和 Lightroom 高精度任务在没有保存分析时，也会先裁切再分析。

## 相机 RAW 直读

独立版可直接加入常见 RAW：

```text
CR2 / CR3 / NEF / NRW / ARW / RAF / RW2 / ORF / PEF / SRW / DNG
```

完整解码固定采用16位、线性Gamma、关闭自动提亮和ProPhoto RGB。RAW设置包括相机、日光、自动和自定义白平衡，高光处理、去马赛克方式、内嵌预览优先和重新解码。

具体相机与压缩方式支持范围取决于发行包内的 rawpy / LibRaw。不支持时可先用 Lightroom、Camera Raw 或相机厂商软件导出16位TIFF。

## Lightroom Classic

### 原生直接转正（默认）

```text
图库 → 增效工具额外功能
→ PS-Sezhao：原生直接转正所选照片（默认）
```

直接写入 Lightroom 非破坏性调整，不生成新文件，并默认创建恢复快照。该模式没有独立处理窗口。

### 高精度 16 位 TIFF

```text
图库 → 增效工具额外功能
→ PS-Sezhao：高精度 16 位 TIFF
```

Lightroom 先渲染16位ProPhoto RGB TIFF，再打开与独立版相同的多图窗口。因此原图吸管、基底手动微调和新裁切方式均可使用。

## Photoshop

相机 RAW 先通过 Camera Raw 打开，再使用 PS-Sezhao。Photoshop 版保留点击吸管、实时画布预览、大图预览、基底微调、数字输入和完整分辨率输出。

## 开发检查

```bash
node scripts/validate.mjs
node --test tests/*.test.js
PYTHONPATH=standalone python -m unittest discover -s standalone/tests -v
bash scripts/build-release.sh
```

## 第三方组件

- rawpy：LibRaw 的 Python 封装，用于相机 RAW 解码。
- LibRaw：随 rawpy 平台包提供的 RAW 解码运行库。
- Compact ICC Profiles：内置 `ProPhoto-v2-micro.icc`，按 CC0 发布。

## 许可证

MIT。Adobe、Photoshop 和 Lightroom 是 Adobe 的商标；本项目与 Adobe 无隶属或背书关系。
