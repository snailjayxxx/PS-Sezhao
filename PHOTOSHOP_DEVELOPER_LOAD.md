# Photoshop 开发者加载说明

本说明用于插件开发、调试，以及 `.ccx` 安装器不可用时的源码加载测试。

## 支持范围

- Photoshop 2024（25.0）或更高版本
- Adobe UXP Developer Tool
- macOS 或 Windows
- 当前用户具备启用 Developer Mode 所需的管理员权限

开发者加载只改变插件的加载方式，不会激活 Photoshop、修改 Creative Cloud、绕过 Adobe 授权，也不能修复被第三方修改或删除的 UXP 运行组件。

## 下载文件

从 GitHub Release 下载：

```text
PS-Sezhao-Photoshop-Developer-v0.5.2.zip
```

解压后选择其中的 `manifest.json`。

## 使用 UXP Developer Tool 加载

1. 完全关闭旧版本 PS-Sezhao 插件面板。
2. 启动 Photoshop 2024 或更高版本。
3. 启动 Adobe UXP Developer Tool。
4. 启用 Developer Mode；系统要求时输入管理员密码。
5. 点击 `Add Plugin`。
6. 选择解压目录中的 `manifest.json`。
7. 在插件右侧菜单中选择 `Load`。
8. 回到 Photoshop，打开 `插件 → 胶片去色罩`。
9. 确认顶部显示 `PS-SEZHAO · 0.5.2`。

## v0.5.2 吸管与胶片基底

- 胶片基底吸管从记录的原始负片图层读取像素；
- 即使画布顶部显示临时转正预览，也不会读取预览图层颜色；
- 插件内大图点击会先换算到文档坐标，再读取原始负片图层；
- 面板“胶片基底微调”提供 R/G/B 滑块、数字输入和 `− / +` 微调；
- 相机 RAW 仍先通过 Camera Raw 打开，再处理进入 Photoshop 的图层。

## 更新源码版本

1. 在 UXP Developer Tool 中卸载或移除旧目录。
2. 解压新版本到新的文件夹。
3. 重新添加新目录中的 `manifest.json`。
4. 点击 `Load`。

不要把新旧文件混在同一个目录中，否则可能残留旧脚本。

## 常见问题

### Host Application specified is not available

确认 Photoshop 已经启动，并且版本不低于25.0。Photoshop 2024对应25.x。

### Plugin Load Failed

检查：

- 选择的是 `manifest.json`，不是 ZIP 文件；
- 文件夹结构没有多套一层；
- Photoshop 的 UXP 运行环境完整；
- UXP Developer Tool 已获得管理员权限；
- 面板未同时加载另一个相同插件 ID 的版本。

### `.ccx` 能安装，但开发者包不能加载

在 UXP Developer Tool 中查看 `Logs` 或 `Debug`，记录具体报错。

### 开发者模式能否代替 Photoshop 授权

不能。UXP Developer Tool只负责加载和调试插件，不负责Photoshop授权，也不保证第三方修改版宿主能够正常运行插件。
