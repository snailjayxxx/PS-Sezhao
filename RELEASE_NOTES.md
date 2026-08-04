# PS-Sezhao v0.3.1

这是面向 Photoshop 2024 兼容性、CCX 安装包和开发者加载方式的维护版本。Lightroom Classic 与独立桌面版同步使用统一版本号重新构建。

## Photoshop 2024+

- 将最低宿主版本从 Photoshop 27.8 降至 Photoshop 2024（25.0.0）。
- 保留点击式胶片基底吸管、点击式中性色吸管、大图预览、连续画布预览和完整分辨率输出。
- 移除 `executeAsModal.timeOut` 选项；该选项需要 Photoshop 25.10，早期 Photoshop 2024 小版本不支持。
- 增加兼容性测试，禁止后续运行脚本重新引入 25.10 专用模态超时选项。

## Photoshop CCX

- 发布流水线直接创建符合 CCX ZIP 容器结构的安装包，插件文件位于压缩包根目录。
- 打包完成后会自动解包检查 `manifest.json` 的位置、版本号、Photoshop 宿主声明和 25.0.0 最低版本。
- 避免多套一层文件夹导致 Creative Cloud 安装错误。
- 发行文件命名为 `PS-Sezhao-Photoshop-v0.3.1.ccx`。

## Photoshop 开发者加载包

新增：

```text
PS-Sezhao-Photoshop-Developer-v0.3.1.zip
```

该文件包含完整 UXP 插件目录，可通过 Adobe UXP Developer Tool：

```text
Add Plugin → 选择 manifest.json → Load
```

开发者加载版用于开发、调试以及 CCX 安装器不可用时的源码加载测试。它只改变插件加载方式，不会激活 Photoshop、修改 Creative Cloud 或绕过 Adobe 授权。

## Lightroom Classic

- 版本同步升级至 0.3.1。
- 继续支持 Lightroom Classic 15.4+。
- 继续提供 macOS Apple Silicon 和 Windows x64 插件包。
- 继续使用内置本地处理器生成 16 位 TIFF 并自动导回目录。

## 独立桌面版

- 版本同步升级至 0.3.1。
- 继续提供 macOS Apple Silicon 和 Windows x64 版本。
- 不需要 Photoshop、Lightroom、Creative Cloud、Python 或 Node.js。
- 继续支持自动边框分析、点击吸管、实时预览、批量处理和 16 位 TIFF 输出。

## 自动发布

GitHub Actions 会自动完成：

- Photoshop 2024 兼容性与 JavaScript 语法检查
- Photoshop 图像引擎和界面回归测试
- CCX 根目录结构与清单复核
- Photoshop Developer ZIP 打包
- Python 图像引擎测试
- Lightroom Lua 语法检查
- macOS Apple Silicon 与 Windows x64 的桌面版和 LR 插件构建
- 所有发行文件的 SHA-256 校验
