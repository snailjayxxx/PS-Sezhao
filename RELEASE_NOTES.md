# PS-Sezhao v0.3.0

这是首次同时发布 Photoshop、Lightroom Classic 和独立桌面版的统一版本。

## Photoshop

- 保留 v0.2.2 的点击式吸管、大图预览、连续画布预览和完整分辨率输出。
- 版本号统一升级至 0.3.0。
- 最低宿主版本调整为当前 Photoshop 27.8。
- Release 文件更名为 `PS-Sezhao-Photoshop-v0.3.0.ccx`，方便与 LR 版区分。

## Lightroom Classic

- 新增 Lightroom Classic 15.4+ Lua 插件。
- 从图库菜单处理当前所选照片。
- 由 Lightroom 先渲染 16 位 ProPhoto RGB TIFF，避免直接解析 RAW 造成结果不一致。
- 打开与独立版共用的本地大预览窗口。
- 支持整卷批量应用同一胶片基底和校色参数。
- 输出到原图目录下的 `PS-Sezhao` 文件夹，并自动导回目录。
- 分别提供 macOS Apple Silicon 和 Windows x64 安装包。

## 独立桌面版

- 新增不依赖 Adobe 的 macOS Apple Silicon 和 Windows x64 桌面程序。
- 支持 TIFF、JPEG、PNG、BMP、WebP。
- 支持自动边框分析、胶片基底吸管、中性色吸管和实时大图预览。
- 支持 16 位 TIFF 保存和多张照片批量处理。
- 高像素扫描图采用分块处理，降低临时数组的内存峰值。
- 保留输入 TIFF 的 ICC 配置，并写入输出 TIFF。
- 同一可执行程序也作为 Lightroom Classic 插件的本地处理引擎。

## 自动发布

GitHub Actions 现在会自动完成：

- Photoshop UXP 测试与 CCX 打包
- Python 图像引擎测试
- Lightroom Lua 语法检查
- macOS Apple Silicon 桌面版与 LR 包构建
- Windows x64 桌面版与 LR 包构建
- 所有发行文件的 SHA-256 校验

## 说明

本项目不适配破解或修改版 Adobe 软件。没有 Adobe 正版环境的用户应使用独立桌面版。
