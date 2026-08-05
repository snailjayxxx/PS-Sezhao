# PS-Sezhao 胶片去色罩

PS-Sezhao 是面向彩色负片扫描和相机翻拍的本地图像处理项目。同一个仓库同时发布：

- **Photoshop 版**：UXP `.ccx` 插件，直接读取和写入 Photoshop 图层。
- **Photoshop 开发者加载版**：完整 UXP 插件目录。
- **Lightroom Classic 版**：原生直接转正、高精度 16 位 TIFF、恢复快照。
- **独立桌面版**：不依赖 Adobe，支持相机 RAW 直读、多图、缩放、裁切、拖放和批量输出。

照片只在本机处理，不上传服务器。

## 当前版本

统一版本：**v0.5.5**

- Photoshop 2024（25.0）或更高版本
- Lightroom Classic 15.4 或更高版本
- macOS Apple Silicon
- Windows x64

## Release 文件

| 使用场景 | 下载文件 |
|---|---|
| Photoshop 正常安装 | `PS-Sezhao-Photoshop-v0.5.5.ccx` |
| Photoshop 开发者加载 | `PS-Sezhao-Photoshop-Developer-v0.5.5.zip` |
| Lightroom Classic · Apple Silicon | `PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.5.zip` |
| Lightroom Classic · Windows x64 | `PS-Sezhao-LightroomClassic-Windows-x64-v0.5.5.zip` |
| 独立桌面版 · Apple Silicon | `PS-Sezhao-Standalone-macOS-arm64-v0.5.5.zip` |
| 独立桌面版 · Windows x64 | `PS-Sezhao-Standalone-Windows-x64-v0.5.5.zip` |

## v0.5.5：修复导入并增加系统拖放

v0.5.4 中，撤销/重做补丁注册了 `_history_for` 等内部方法，但首次加载图片时调用了不存在的 `history_for`。在无控制台的 Windows/macOS 发行版中，这个异常不会显示，所以“添加图像”和“添加文件夹”在完成选择后看起来完全没有反应。

v0.5.5 修复全部方法别名，并让导入异常在状态栏和弹窗中明确显示，不再静默失败。

独立版和 Lightroom 高精度窗口新增系统拖放：

- 从 Windows 资源管理器或 macOS Finder 拖入一张或多张图片；
- 拖入 TIFF、JPEG、PNG、BMP、WebP 或相机 RAW；
- 拖入一个或多个文件夹；
- 文件夹会递归查找支持的图片和 RAW；
- 自动去重并显示实际新增数量；
- 支持带空格、中文和其他 Unicode 字符的路径。

拖放可以落在整个窗口、中央图片区或左侧图片列表。

## 撤销、重做与直接基底数值

独立版、Lightroom 高精度窗口和 Photoshop 面板都支持：

```text
撤销：Ctrl/Cmd + Z
重做：Ctrl/Cmd + Y 或 Ctrl/Cmd + Shift + Z
```

可恢复曝光、色彩、RGB 增益、胶片基底、自动分析、吸管结果和裁切。独立版按每张照片分别保存最多 60 项历史。

胶片基底直接编辑最终使用的 R/G/B：

```text
识别值：212 / 143 / 82
最终使用：212 / 143 / 82
```

“恢复为识别值”可以回到吸管或自动分析结果。

## 中性灰吸管修改什么

中性灰吸管不会重新改变胶片基底，也不会直接改写色温或色调。它修改：

```text
红色输出增益
绿色输出增益
蓝色输出增益
```

目标是让点击区域经过当前转正处理后满足 `R≈G≈B`。`1.00` 表示该通道不额外校正。三个值均可手动输入、拖动滑块或使用 `− / +` 微调。

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

独立版可直接加入：

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

直接写入 Lightroom 非破坏性调整，不生成新文件，并默认创建恢复快照。

### 高精度 16 位 TIFF

```text
图库 → 增效工具额外功能
→ PS-Sezhao：高精度 16 位 TIFF
```

Lightroom 先渲染 16 位 ProPhoto RGB TIFF，再打开与独立版相同的多图窗口，因此拖放之外的桌面功能均可使用。Lightroom 传入的任务照片仍由插件自动载入。

## Photoshop

相机 RAW 先通过 Camera Raw 打开，再使用 PS-Sezhao。Photoshop 版保留点击吸管、实时画布预览、大图预览、数字输入、撤销/重做和完整分辨率输出。

## 开发检查

```bash
node scripts/validate.mjs
node --test tests/*.test.js
PYTHONPATH=standalone python -m unittest discover -s standalone/tests -v
bash scripts/build-release.sh
```

## 第三方组件

- rawpy / LibRaw：相机 RAW 解码。
- TkinterDnD2 / TkDnD：Windows、macOS 和 Linux/X11 系统文件拖放。
- Compact ICC Profiles：内置 `ProPhoto-v2-micro.icc`，按 CC0 发布。

## 许可证

MIT。Adobe、Photoshop 和 Lightroom 是 Adobe 的商标；本项目与 Adobe 无隶属或背书关系。
