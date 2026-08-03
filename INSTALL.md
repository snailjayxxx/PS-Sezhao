# 安装与使用说明

## 推荐：安装 `.ccx`

适合普通使用者，也是本项目第一版建议采用的发布方式。

### macOS / Windows

1. 安装或更新 Adobe Creative Cloud Desktop。
2. 安装 Photoshop 23.3 或更高版本。
3. 在 GitHub Releases 下载 `PS-Sezhao-v0.1.0.ccx`。
4. 双击 `.ccx` 文件。
5. Creative Cloud 会提示该插件不是来自 Adobe Marketplace。确认文件来自本仓库后，选择“本地安装”或“安装”。
6. 重启 Photoshop。
7. 打开 `插件（Plugins） → 胶片去色罩`。

### 为什么选择安装式，而不是独立程序

PS-Sezhao 需要读取 Photoshop 当前图层并把结果写回新图层。使用 `.ccx` 安装后，工作流最短、可保留 PSD 图层，也不需要用户安装 Python、Node.js 或其他运行环境。

独立程序更适合未来的文件夹批量转换，但会失去 Photoshop 选区、图层和即时修图衔接，因此不作为第一版主方案。

## 开发者加载方式

当 `.ccx` 安装失败或需要调试时：

1. 在 Creative Cloud Desktop 安装 UXP Developer Tool。
2. 打开 Photoshop。
3. 打开 UXP Developer Tool。
4. 点击 `Add Plugin`，选择本仓库 `plugin/manifest.json`。
5. 点击 `Load`。
6. 回到 Photoshop，在插件菜单打开面板。

## 推荐的胶片准备

- 保留未曝光的橙色胶片边框。
- 扫描或翻拍不要剪切通道。
- 优先使用 16 位文档。
- 一卷胶片保持相同的采集设备和设置。

## 常见问题

### 自动分析提示边框像素不足

用矩形选框工具框选一块未曝光、没有齿孔和文字的橙色胶片边缘，然后点击“从当前选区采样”。

### 转正后偏色明显

检查是否采样到了画面、黑色片夹、齿孔或灯板直射区域。重新选择更干净的胶片基底。还应确认输入图像的某个颜色通道没有过曝或欠曝剪切。

### 插件没有出现在 Photoshop

确认 Photoshop 版本不低于 23.3，安装后完全退出并重新打开 Photoshop。也可通过 UXP Developer Tool 加载 `plugin/manifest.json` 查看具体错误。

### `.ccx` 被提示未验证

通过 GitHub 直接分发的插件没有经过 Adobe Marketplace 审核，Creative Cloud 会显示信任提示。这不等于插件包含恶意代码；用户应确认下载来源和 `CHECKSUMS.txt` 后再安装。
