# PS-Sezhao 胶片去色罩

PS-Sezhao 是面向彩色负片扫描和相机翻拍的本地图像处理项目。同一个仓库同时发布：

- **Photoshop 版**：UXP `.ccx` 插件，直接读取和写入 Photoshop 图层。
- **Photoshop 开发者加载版**：完整 UXP 插件目录。
- **Lightroom Classic 版**：原生直接转正、高精度 16 位 TIFF、恢复快照。
- **独立桌面版**：不依赖 Adobe，支持相机 RAW 直读、多图、缩放、裁切和批量输出。

照片只在本机处理，不上传服务器。

## 当前版本

统一版本：**v0.5.4**

- Photoshop 2024（25.0）或更高版本
- Lightroom Classic 15.4 或更高版本
- macOS Apple Silicon
- Windows x64

## Release 文件

| 使用场景 | 下载文件 |
|---|---|
| Photoshop 正常安装 | `PS-Sezhao-Photoshop-v0.5.4.ccx` |
| Photoshop 开发者加载 | `PS-Sezhao-Photoshop-Developer-v0.5.4.zip` |
| Lightroom Classic · Apple Silicon | `PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.4.zip` |
| Lightroom Classic · Windows x64 | `PS-Sezhao-LightroomClassic-Windows-x64-v0.5.4.zip` |
| 独立桌面版 · Apple Silicon | `PS-Sezhao-Standalone-macOS-arm64-v0.5.4.zip` |
| 独立桌面版 · Windows x64 | `PS-Sezhao-Standalone-Windows-x64-v0.5.4.zip` |

## v0.5.4：撤销、重做与直接基底数值

独立版、Lightroom 高精度窗口和 Photoshop 面板都增加撤销与重做：

```text
撤销：Ctrl/Cmd + Z
重做：Ctrl/Cmd + Y 或 Ctrl/Cmd + Shift + Z
```

可恢复曝光、色彩、RGB 增益、胶片基底、自动分析、吸管结果和裁切。独立版按每张照片分别保存最多 60 项历史，不会把一张照片的历史套到另一张照片。

胶片基底不再显示“识别值上的加减偏移”，而是直接编辑最终使用的 R/G/B：

```text
识别值：212 / 143 / 82
最终使用：212 / 143 / 82
```

独立版保留识别值作为参考，滑块和数字框直接修改“最终使用值”；“恢复为识别值”可回到吸管或自动分析结果。Photoshop 版使用 0～255 的直接数值。

## 中性灰吸管修改什么

中性灰吸管不会重新改变胶片基底，也不会直接改写色温或色调。它会计算并修改：

```text
红色输出增益
绿色输出增益
蓝色输出增益
```

目标是让点击区域经过当前转正处理后满足 R≈G≈B。`1.00` 表示该通道不额外校正。v0.5.4 会明确显示这三个数值，允许数字输入、滑块和 `− / +` 微调，并提供“中性灰增益恢复 1.00”。

## 原图吸管

胶片基底吸管不从转正或调色后的预览读取颜色：

- 独立版始终从未修改的输入图像取样；
- 裁切后点击可见画面时，坐标会映射回完整原图；
- Photoshop 从记录的原始负片图层读取像素，不读取临时预览图层；
- 基底确定后，色调范围使用当前裁切区域重新计算。

## 侧栏滚轮和裁切

- 鼠标位于右侧参数栏时，滚轮上下浏览参数；
- 鼠标位于左侧图片列表时，滚轮上下浏览图片；
- 中间图片预览区滚轮继续用于缩放；
- 平时只显示裁切后保留的画面；
- 点击“裁切”后显示完整照片和当前裁切框；
- 自动分析边框只分析裁切后的区域；
- 裁切是非破坏性的，只在导出时应用。

## 相机 RAW 直读

独立版可直接加入常见 RAW：

```text
CR2 / CR3 / NEF / NRW / ARW / RAF / RW2 / ORF / PEF / SRW / DNG
```

完整解码固定采用 16 位、线性 Gamma、关闭自动提亮和 ProPhoto RGB。具体相机与压缩方式支持范围取决于发行包内的 rawpy / LibRaw。

## Lightroom Classic

### 原生直接转正（默认）

```text
图库 → 增效工具额外功能
→ PS-Sezhao：原生直接转正所选照片（默认）
```

直接写入 Lightroom 非破坏性调整，不生成新文件，并默认创建恢复快照。该模式的撤销继续使用 Lightroom 历史记录和插件恢复快照。

### 高精度 16 位 TIFF

```text
图库 → 增效工具额外功能
→ PS-Sezhao：高精度 16 位 TIFF
```

Lightroom 先渲染 16 位 ProPhoto RGB TIFF，再打开与独立版相同的多图窗口，因此撤销/重做、直接基底数值、中性灰增益、原图吸管、裁切和侧栏滚轮均可使用。

## Photoshop

相机 RAW 先通过 Camera Raw 打开，再使用 PS-Sezhao。Photoshop 版保留点击吸管、实时画布预览、大图预览、数字输入和完整分辨率输出，并增加插件参数撤销/重做。

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
