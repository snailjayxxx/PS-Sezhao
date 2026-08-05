# Photoshop 开发者加载说明

本说明用于插件开发、调试，以及 `.ccx` 安装器不可用时的源码加载测试。

## 支持范围

- Photoshop 2024（25.0）或更高版本
- Adobe UXP Developer Tool
- macOS 或 Windows
- 当前用户具备启用 Developer Mode 所需的管理员权限

开发者加载只改变插件加载方式，不会激活 Photoshop、修改 Creative Cloud 或绕过 Adobe 授权。

## 下载和加载

下载并解压：

```text
PS-Sezhao-Photoshop-Developer-v0.5.4.zip
```

1. 完全关闭旧版 PS-Sezhao 面板。
2. 启动 Photoshop 2024 或更高版本。
3. 启动 Adobe UXP Developer Tool 并启用 Developer Mode。
4. 点击 `Add Plugin`。
5. 选择解压目录中的 `manifest.json`。
6. 点击 `Load`。
7. 回到 Photoshop，打开 `插件 → 胶片去色罩`。
8. 确认顶部显示 `PS-SEZHAO · 0.5.4`。

## v0.5.4 操作变化

- 胶片基底吸管继续读取记录的原始负片图层，不读取实时预览图层；
- 胶片基底 R/G/B 改为直接显示和填写最终 0～255 数值，不再显示识别值上的正负偏移；
- 中性灰吸管修改的是红、绿、蓝输出增益，三个值可继续手动输入和微调；
- 面板增加“撤销”和“重做”；
- 快捷键为 `Ctrl/Cmd+Z`、`Ctrl/Cmd+Y`、`Ctrl/Cmd+Shift+Z`；
- 相机 RAW 仍先通过 Camera Raw 打开，再处理进入 Photoshop 的图层。

## 更新源码版本

1. 在 UXP Developer Tool 中移除旧目录。
2. 解压新版本到新的文件夹。
3. 重新添加新目录中的 `manifest.json`。
4. 点击 `Load`。

不要混合新旧文件，否则可能残留旧脚本。

## 常见问题

### Host Application specified is not available

确认 Photoshop 已启动，并且版本不低于 25.0。

### Plugin Load Failed

检查：

- 选择的是 `manifest.json`，不是 ZIP；
- 文件夹结构没有多套一层；
- Photoshop 的 UXP 运行环境完整；
- UXP Developer Tool 已获得管理员权限；
- 没有同时加载另一个相同插件 ID 的版本。

### 开发者模式能否代替 Photoshop 授权

不能。UXP Developer Tool 只负责加载和调试插件，不负责 Photoshop 授权。
