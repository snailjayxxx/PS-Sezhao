# PS-Sezhao v0.5.1

这是独立桌面版相机 RAW 直读更新。v0.5.0 的数字输入、多图、缩放、平移、裁切和批量导出继续保留；Photoshop 与 Lightroom Classic 同步使用统一版本号重新构建。

## 独立版直接读取相机 RAW

独立桌面版现在可以直接添加常见相机 RAW，包括：

```text
CR2 / CR3 / NEF / NRW / ARW / RAF / RW2 / ORF / PEF / SRW / DNG
```

此外还登记了多种 LibRaw 可识别扩展名。具体相机与压缩方式的支持范围由发行包内的 rawpy / LibRaw 决定。

## 16 位线性 ProPhoto 工作流

完整 RAW 解码固定采用：

- 16 位输出；
- `gamma=(1,1)` 线性解码；
- 关闭 LibRaw 自动提亮；
- ProPhoto RGB 输出空间；
- 胶片基底分析与光密度转正；
- 16 位 TIFF 保存；
- 自动嵌入 ProPhoto RGB ICC。

这样避免普通相片解码流程中的自动亮度干预，并为负片翻拍保留更完整的通道和高光信息。

## RAW 解码设置

右侧新增“相机 RAW 解码 · v0.5.1”：

- 相机拍摄白平衡；
- 日光白平衡；
- LibRaw 自动白平衡；
- 自定义 R / G / B / G2 通道倍率；
- 高光混合、直接裁切或重建；
- AHD、线性、VNG、PPG 去马赛克；
- 优先读取内嵌预览；
- 内嵌预览不存在时使用半尺寸快速解码；
- 修改设置后重新解码当前 RAW。

## 快速预览与完整解码

切换 RAW 照片时，程序会优先读取 RAW 内嵌 JPEG/位图预览，让图片尽快出现在工作区；随后在后台完成完整 16 位线性解码。最终分析、调色和导出只使用完整解码结果，不会把内嵌预览当成成品输出。

## 批量 RAW

- 文件夹导入会发现 RAW；
- RAW 与 TIFF/JPEG/PNG 可以出现在同一多图列表；
- 批量导出逐张进行完整解码；
- 每张照片继续使用自己的分析、参数和裁切；
- 单张完成后释放内存，再处理下一张；
- 输出默认是新的16位TIFF。

## 不支持机型与压缩格式

程序会捕获 LibRaw 的不支持错误，并显示：

- 当前文件名；
- rawpy 与 LibRaw 运行版本；
- 可能是不支持的相机、压缩方式或多帧结构；
- 使用 Lightroom Classic、Camera Raw 或相机厂商软件导出16位TIFF的替代流程。

## Lightroom Classic

Lightroom 原生直接转正、高精度16位TIFF和恢复快照入口保持不变。Lightroom 中的相机RAW继续由 Lightroom 解码；v0.5.1 的RAW设置面板主要面向独立桌面版。

## Photoshop 2024+

Photoshop 继续处理已经进入文档的图层。相机RAW先通过 Camera Raw 打开。点击吸管、实时预览、数字输入、加减微调和完整分辨率输出保持不变。

## 发行包与自动检查

GitHub Actions 会：

- 安装并导入 rawpy 0.27 系列；
- 输出 rawpy 与 LibRaw 版本；
- 测试16位线性ProPhoto解码参数；
- 测试白平衡、自定义通道倍率、内嵌预览和不支持机型提示；
- 在 macOS Apple Silicon 和 Windows x64 包中收集 rawpy / LibRaw 二进制组件；
- 对打包后的可执行程序执行启动参数冒烟测试；
- 继续执行 Photoshop、Lightroom、独立图像引擎和发行结构测试。

本版本的自动测试使用模拟 RAW 解码器验证参数与异常流程；不同相机型号的真实画面和色彩仍需通过实际 RAW 文件验证。

## 发行文件

- `PS-Sezhao-Photoshop-v0.5.1.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.5.1.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.1.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.5.1.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.5.1.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.5.1.zip`
