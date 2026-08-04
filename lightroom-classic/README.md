# Lightroom Classic 版

目标版本：Lightroom Classic 15.4 / 15.4.1 及以上。

插件目录为 `PS-Sezhao.lrplugin`。源码目录不含平台二进制；GitHub Actions 会在发布时把 macOS Apple Silicon 或 Windows x64 的独立处理器放入 `bin/`，并分别生成可安装 ZIP。

插件通过 `LrExportSession` 将所选照片渲染为临时 16 位 TIFF，随后调用本地处理器。调整完成后，成品会写入原图旁的 `PS-Sezhao` 子目录，并通过目录写入事务导回 Lightroom Classic。
