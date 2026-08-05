# PS-Sezhao 胶片去色罩

PS-Sezhao 是面向彩色负片扫描和相机翻拍的本地图像处理项目。同一个仓库同时发布：

- **Photoshop 版**：UXP `.ccx` 插件，直接读取和写入 Photoshop 图层。
- **Photoshop 开发者加载版**：完整 UXP 插件目录。
- **Lightroom Classic 版**：原生直接转正、高精度 16 位 TIFF、恢复快照。
- **独立桌面版**：不依赖 Adobe，支持相机 RAW 直读、多图工作区、裁切和批量输出。

照片只在本机处理，不上传服务器。

## 当前版本

统一版本：**v0.5.1**

- Photoshop 2024（25.0）或更高版本
- Lightroom Classic 15.4 或更高版本
- macOS Apple Silicon
- Windows x64

## Release 文件

| 使用场景 | 下载文件 |
|---|---|
| Photoshop 正常安装 | `PS-Sezhao-Photoshop-v0.5.1.ccx` |
| Photoshop 开发者加载 | `PS-Sezhao-Photoshop-Developer-v0.5.1.zip` |
| Lightroom Classic · Apple Silicon | `PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.1.zip` |
| Lightroom Classic · Windows x64 | `PS-Sezhao-LightroomClassic-Windows-x64-v0.5.1.zip` |
| 独立桌面版 · Apple Silicon | `PS-Sezhao-Standalone-macOS-arm64-v0.5.1.zip` |
| 独立桌面版 · Windows x64 | `PS-Sezhao-Standalone-Windows-x64-v0.5.1.zip` |

## v0.5.1：独立版相机 RAW 直读

独立桌面版现在可直接把相机 RAW 加入单图或多图工作区。常见扩展名包括：

```text
CR2 / CR3 / NEF / NRW / ARW / RAF / RW2 / ORF / PEF / SRW / DNG
```

实际可解码范围取决于安装包内的 rawpy 与 LibRaw；新相机、特殊压缩、多帧 RAW 或厂家私有格式可能暂不支持。遇到不支持的文件时，程序会显示运行时版本和明确的 16 位 TIFF 替代流程。

### 固定高质量解码流程

完整 RAW 解码固定采用：

```text
相机 RAW
→ 16 位解码
→ 关闭自动提亮
→ 线性 Gamma
→ ProPhoto RGB
→ 胶片基底分析与光密度转正
→ 16 位 TIFF（嵌入 ProPhoto ICC）
```

RAW 设置面板提供：

- 相机拍摄白平衡；
- 日光白平衡；
- LibRaw 自动白平衡；
- 自定义 R / G / B / G2 通道倍率；
- 高光混合、裁切或重建；
- AHD、线性、VNG、PPG 去马赛克；
- 优先读取 RAW 内嵌预览；
- 无内嵌预览时使用半尺寸快速预览；
- 修改设置后重新解码当前 RAW。

切换到 RAW 时，程序优先显示内嵌预览，同时在后台完成完整 16 位解码。批量导出会逐张解码和释放内存，不会同时展开整卷 RAW。

## v0.5.0：数字微调、多图、缩放和裁切

Photoshop 与独立版的主要参数同时提供滑块、数字输入框和 `− / +` 微调按钮。独立版和 Lightroom 高精度窗口支持：

- 一次添加多张图片或整个文件夹；
- 左侧多选图片列表；
- 每张图片独立保存分析、参数和裁切；
- 参数与裁切同步到选中照片；
- 鼠标滚轮缩放、平移、适应窗口、100% 和 200%；
- 非破坏性矩形裁切；
- 保存当前、导出选中和导出全部。

裁切不会修改原始文件，只在导出时应用。

## Lightroom Classic

### 原生直接转正（默认）

```text
图库 → 增效工具额外功能
→ PS-Sezhao：原生直接转正所选照片（默认）
```

直接把反相曲线、RGB 曲线、白平衡和明暗参数写入 Lightroom 当前照片，不生成新文件。默认创建恢复快照。Lightroom 中的相机 RAW 仍由 Lightroom 自己解码。

### 高精度 16 位 TIFF

```text
图库 → 增效工具额外功能
→ PS-Sezhao：高精度 16 位 TIFF
```

Lightroom 先渲染 16 位 ProPhoto RGB TIFF，再打开多图窗口。每张照片可单独调色和裁切，成品会自动导回目录。

## Photoshop

Photoshop 版继续处理已经进入 Photoshop 文档的图层。相机 RAW 应先通过 Camera Raw 打开，再使用 PS-Sezhao。Photoshop 版保留点击吸管、实时画布预览、大图预览、数字输入和完整分辨率输出。

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
