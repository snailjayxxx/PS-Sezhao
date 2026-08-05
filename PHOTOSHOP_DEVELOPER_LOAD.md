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
PS-Sezhao-Photoshop-Developer-v0.5.1.zip
```

解压后应看到：

```text
PS-Sezhao-Photoshop-Developer/
├── manifest.json
├── index.html
├── styles.css
├── engine.js
├── runtime-common.js
├── runtime-panel-preview.js
├── runtime-preview.js
├── runtime-sampler.js
├── runtime-final.js
├── runtime-controls-v050.js
├── runtime-v022.js
└── 开发者加载说明.md
```

## 使用 UXP Developer Tool 加载

1. 完全关闭旧版本 PS-Sezhao 插件面板。
2. 启动 Photoshop 2024 或更高版本。
3. 启动 Adobe UXP Developer Tool。
4. 在 UXP Developer Tool 中启用 Developer Mode；系统要求时输入管理员密码。
5. 点击 `Add Plugin`。
6. 选择解压目录中的 `manifest.json`。
7. 在插件右侧菜单中选择 `Load`。
8. 回到 Photoshop，打开：

```text
插件 → 胶片去色罩
```

插件顶部应显示：

```text
PS-SEZHAO · 0.5.1
```

每个主要滑块下方显示 `− / 数字输入框 / +`。数字可直接输入，按 Enter 生效；加减按钮按该参数的最小步长微调。

v0.5.1 的相机 RAW 直读位于独立桌面版。Photoshop 中的 RAW 仍先通过 Camera Raw 打开，再由插件处理进入 Photoshop 的图层。

## 更新源码版本

安装新版本开发者包后：

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
