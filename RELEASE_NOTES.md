# PS-Sezhao v0.5.3

本版本根据 Windows 独立版的实际使用反馈，扩大胶片基底手动调整范围，并修复左右侧栏无法通过鼠标滚轮上下滚动的问题。

## 胶片基底调节范围扩大

胶片基底 R / G / B 的8位等效偏移由：

```text
-64 ～ +64
```

扩大为：

```text
-255 ～ +255
```

适用范围：

- Windows x64 独立版；
- macOS Apple Silicon 独立版；
- Lightroom Classic 高精度16位TIFF窗口；
- Photoshop 2024+ 插件。

滑块、数字输入框、`− / +`按钮和上下方向键都使用新范围。独立处理引擎与 Photoshop 像素引擎同时放宽内部限制，不会出现界面数值变大但实际效果仍被旧限制截断的问题。

胶片基底吸管仍然只读取原始负片像素；扩大范围只影响吸管或自动分析之后的手动偏移。

## 侧栏滚轮修复

独立版与 Lightroom 高精度窗口现在支持：

- 鼠标位于右侧参数栏时，滚轮上下滚动参数；
- 鼠标位于左侧图片列表时，滚轮上下滚动图片；
- Windows 鼠标滚轮；
- Windows 精密触控板；
- macOS 鼠标和触控板；
- Linux/X11 的 Button-4 / Button-5 事件。

滚轮事件只作用于指针所在侧栏，并阻止事件继续传递，因此不会在滚动参数栏时误改滑块或下拉选项。

中间图片预览区继续保留滚轮缩放，不改成侧栏滚动。放大后的画面仍通过平移模式拖动查看。

## 继续保留的 v0.5.2 功能

- 吸管只读取原始输入像素；
- 裁切后只显示保留画面；
- 再次点击裁切恢复全图和已有裁切框；
- 裁切范围内自动分析边框；
- 相机RAW直读和16位线性ProPhoto解码；
- 多图、每图独立参数、同步和批量导出；
- Lightroom原生直接转正与高精度16位TIFF；
- Photoshop 2024+。

## 发行文件

- `PS-Sezhao-Photoshop-v0.5.3.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.5.3.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.3.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.5.3.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.5.3.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.5.3.zip`

自动测试新增宽范围基底参数、Windows/macOS/X11滚轮方向、左右侧栏滚动目标和Photoshop宽范围引擎检查；跨平台安装包继续由GitHub Actions实际构建。
