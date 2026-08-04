# PS-Sezhao 胶片去色罩

PS-Sezhao 是面向彩色负片扫描和相机翻拍的本地图像处理项目。同一个仓库同时发布：

- **Photoshop 版**：UXP `.ccx` 插件，直接读取和写入图层。
- **Photoshop 开发者加载版**：完整 UXP 插件目录。
- **Lightroom Classic 版**：原生直接转正、高精度 16 位 TIFF、恢复快照。
- **独立桌面版**：不依赖 Adobe，支持多图工作区和批量输出。

照片只在本机处理，不上传服务器。

## 当前版本

统一版本：**v0.5.0**

- Photoshop 2024（25.0）或更高版本
- Lightroom Classic 15.4 或更高版本
- macOS Apple Silicon
- Windows x64

## Release 文件

| 使用场景 | 下载文件 |
|---|---|
| Photoshop 正常安装 | `PS-Sezhao-Photoshop-v0.5.0.ccx` |
| Photoshop 开发者加载 | `PS-Sezhao-Photoshop-Developer-v0.5.0.zip` |
| Lightroom Classic · Apple Silicon | `PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.0.zip` |
| Lightroom Classic · Windows x64 | `PS-Sezhao-LightroomClassic-Windows-x64-v0.5.0.zip` |
| 独立桌面版 · Apple Silicon | `PS-Sezhao-Standalone-macOS-arm64-v0.5.0.zip` |
| 独立桌面版 · Windows x64 | `PS-Sezhao-Standalone-Windows-x64-v0.5.0.zip` |

## v0.5.0：参数输入和微调

Photoshop 与独立桌面版的主要调整参数现在同时提供：

```text
滑块
− 按钮
数字输入框
+ 按钮
```

- 数字框可直接输入，按 Enter 或移开焦点后生效。
- 超出允许范围会自动限制到最小值或最大值。
- `− / +` 按参数最小步长微调。
- 数字框内可使用键盘上下方向键微调。
- 参数变化继续触发实时预览。

覆盖曝光、对比度、中间调、饱和度、色温、色调、RGB 增益、黑白点、阴影、高光、风格强度和胶片基底微调。

## v0.5.0：独立版多图工作区

独立桌面版和 Lightroom 的高精度窗口新增：

- 一次添加多张图片；
- 添加整个文件夹，可选择是否包含子文件夹；
- 左侧图片列表和上一张/下一张切换；
- 每张图片单独保存分析结果、调色参数和裁切；
- 将当前参数同步到选中图片；
- 将当前裁切同步到选中图片；
- 导出当前、导出选中、导出全部；
- Lightroom 高精度任务按每张照片各自参数批量生成。

## 缩放、平移和裁切

预览区支持：

- 鼠标滚轮围绕指针位置缩放；
- `适应窗口`、`100%`、`200%`；
- 放大和缩小按钮；
- 平移模式拖动画面；
- 裁切模式拖出矩形裁切框；
- 重置裁切；
- 将裁切同步到选中照片。

裁切是**非破坏性的**：原文件不会被修改，只有导出的结果会应用裁切。裁切区域使用归一化坐标保存，因此可同步到不同分辨率但构图一致的一整卷照片。

## Lightroom Classic

### 原生直接转正（默认）

```text
图库 → 增效工具额外功能
→ PS-Sezhao：原生直接转正所选照片（默认）
```

直接把反相曲线、RGB 曲线、白平衡和明暗参数写入 Lightroom 当前照片，不生成新文件。默认创建恢复快照。

### 高精度 16 位 TIFF

```text
图库 → 增效工具额外功能
→ PS-Sezhao：高精度 16 位 TIFF
```

Lightroom 渲染 16 位 ProPhoto RGB TIFF，随后打开与独立版相同的多图窗口。每张照片可以单独调色和裁切，最终输出新的 16 位 TIFF 并自动导回目录。

## 支持格式

独立版直接支持 TIFF、JPEG、PNG、BMP 和 WebP。相机 RAW 建议先通过 Lightroom、相机厂商软件、Darktable 或 RawTherapee 导出为 16 位 TIFF。

## 开发检查

```bash
node scripts/validate.mjs
node --test tests/*.test.js
PYTHONPATH=standalone python -m unittest discover -s standalone/tests -v
bash scripts/build-release.sh
```

## 许可证

MIT。Adobe、Photoshop 和 Lightroom 是 Adobe 的商标；本项目与 Adobe 无隶属或背书关系。
