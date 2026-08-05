# Lightroom Classic 版

目标版本：Lightroom Classic 15.4 / 15.4.1 及以上。

插件目录为 `PS-Sezhao.lrplugin`。源码目录不含平台二进制；GitHub Actions 会在发布时把 macOS Apple Silicon 或 Windows x64 的独立处理器放入 `bin/`，并分别生成可安装 ZIP。

## 三个入口

1. **原生直接转正所选照片（默认）**：直接写入 Lightroom 非破坏性调整，并可创建恢复快照。
2. **高精度 16 位 TIFF**：通过 `LrExportSession` 把所选照片渲染为临时 16 位 ProPhoto RGB TIFF，打开多图窗口，完成后自动导回目录。
3. **恢复原生转正前状态**：恢复最近一次 PS-Sezhao 原生转正前快照。

## 关于相机 RAW

Lightroom 中的 CR3、NEF、ARW、RAF、DNG 等文件继续由 Lightroom 自己解码：

- 原生模式直接作用于 Lightroom 当前 RAW 的 Develop Settings；
- 高精度模式由 Lightroom 先渲染 16 位 TIFF，再交给本地处理器。

v0.5.1 新增的 rawpy / LibRaw 直读设置主要服务于独立桌面版，不会替换 Lightroom 的 RAW 解码管线。

## 高精度输出

成品写入原图旁的 `PS-Sezhao` 子目录，并通过目录写入事务导回 Lightroom Classic。多图窗口支持每张照片独立参数、缩放、平移、非破坏性裁切和批量输出。
