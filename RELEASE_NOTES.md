# PS-Sezhao v0.4.0

这是 Lightroom Classic 工作流的重要功能版本：新增直接修改 Lightroom 当前照片的“原生转正”模式，同时保留原有高精度 16 位 TIFF 模式。

## Lightroom 原生直接转正（默认）

新增菜单：

```text
PS-Sezhao：原生直接转正所选照片（默认）
```

该模式使用 Lightroom Classic 的 Develop Settings 接口，把调整直接写入所选照片，不生成新文件，也不改写原始图像。

原生模式会应用：

- 完整反相点曲线；
- 兼容曲线和现代 `ExtendedToneCurvePV2012`；
- 红、绿、蓝独立通道曲线；
- 曝光、对比度、高光、阴影、白色、黑色；
- 色温、色调、自然饱和度、饱和度；
- 通用 C-41、Portra、Gold、Fujifilm、ECN-2 起始风格；
- 风格强度和附加校正参数；
- 所选照片批量应用。

应用后可以直接进入 Lightroom 的“修改照片”模块继续调整。

## 恢复快照

原生模式默认会在每张照片上创建带时间的应用前快照：

```text
PS-Sezhao 原生转正前 YYYY-MM-DD HH:MM:SS
```

新增菜单：

```text
PS-Sezhao：恢复原生转正前状态
```

该命令会恢复所选照片最近一次 PS-Sezhao 应用前快照。

## 高精度 16 位 TIFF 继续保留

原有流程改名为：

```text
PS-Sezhao：高精度 16 位 TIFF
```

它继续执行：

- Lightroom 渲染 16 位 ProPhoto RGB TIFF；
- 本地逐像素胶片基底和光密度转正；
- 独立大预览窗口和点击吸管；
- 新 16 位 TIFF 输出并自动导回 Lightroom。

原生模式适合直接编辑、快速批量和不生成新文件；高精度模式适合严重偏色、胶片基底采样和要求逐像素一致性的照片。

## Lightroom 安全性与兼容性

- 原生模式使用 `photo:getDevelopSettings()` 读取当前调整；
- 使用 `photo:applyDevelopSettings()` 写入非破坏性参数；
- 所有写入位于 `catalog:withWriteAccessDo()`；
- 使用 `LrTasks.pcall` 保持协作任务可让出；
- 默认跳过已经应用过反相曲线的照片，避免重复反相；
- 视频会自动跳过。

## Photoshop 与独立版

- Photoshop 最低版本继续为 Photoshop 2024（25.0.0）；
- Photoshop 功能和逐像素算法保持不变；
- macOS Apple Silicon、Windows x64 独立版同步升级至 0.4.0。

## 发行文件

- `PS-Sezhao-Photoshop-v0.4.0.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.4.0.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.4.0.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.4.0.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.4.0.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.4.0.zip`

## 自动检查

GitHub Actions 会自动完成：

- Lightroom 原生 Develop Settings 结构测试；
- 反相和 RGB 通道曲线检查；
- 快照创建和恢复入口检查；
- Lightroom 高精度导出协程与 16 位 TIFF 检查；
- Lightroom Lua 语法检查；
- Photoshop JavaScript、图像引擎和界面测试；
- 独立图像引擎测试；
- macOS Apple Silicon 与 Windows x64 构建；
- 所有发行文件的 SHA-256 校验。
