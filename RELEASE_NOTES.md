# PS-Sezhao v0.7.0-beta.3

本版本继续改善独立版界面，并加入应用同级项目目录、用户 Cube LUT、macOS DMG 和 Windows 图形化安装器。v0.6.3 继续保留为 Latest 稳定版。

## 风格选择区域

- “扫描仪风格”和“胶卷风格”的下拉框直接跟随各自文字标签，并使用右侧剩余宽度；
- 不再请求固定 31 字符宽度，避免右侧栏较窄时控件左侧或文字被截断；
- 下拉列表根据最长项目自动增加宽度；
- 靠近窗口右边缘时，下拉列表会向左调整，而不是突出应用窗口；
- 内置扫描仪和胶卷名称可在展开列表中完整显示。

## 工具与几何分组

- 预览工具重组为“裁切工具、缩放、旋转”三个有边框的固定组；
- 几何校正重组为“范围、拉直、变换”三个有边框的固定组；
- 同组按钮之间的间距不再随窗口宽度拉伸；
- 仅工具组右侧空白区域参与伸缩；
- 保留原有裁切、缩放、旋转、拉直、翻转、自动范围和四角透视功能。

## project 与 lut 同级目录

安装版和便携版现在使用统一结构：

```text
PS-Sezhao/
├── PS-Sezhao.app 或 PS-Sezhao.exe
├── project/
│   └── workspace.sqlite3
├── lut/
├── 安装说明.html
└── .ps-sezhao-portable
```

- 普通工作区、多个胶卷项目、每张图片参数和输出预设都保存在 `project/workspace.sqlite3`；
- 左侧胶卷项目区域增加“打开 project 文件夹”；
- 右侧风格区域增加“打开 LUT 文件夹”；
- 首次启动会从旧位置自动复制数据库；
- 旧数据库不会删除，新目录会生成 `MIGRATED_FROM.txt` 记录迁移来源；
- 单独把 `.app` 放进不可写的系统 `/Applications` 时，数据会安全回退到 `~/Documents/PS-Sezhao`。

## 用户 Cube LUT

- 胶卷风格区域新增“添加 LUT…”；
- 支持标准 `.cube` 文件，包括 1D 和 3D LUT；
- 导入时检查尺寸、数据行数、数值范围和 Domain；
- 3D LUT 使用三线性插值；
- LUT 应用于基础转正、扫描仪风格和内置胶卷处理之后；
- 使用现有“胶卷强度”控制 LUT 混合比例；
- 项目只保存 LUT 文件名，缺失或损坏的 LUT 不会阻止项目打开；
- 跨电脑迁移时需要同时复制 `project` 和 `lut` 文件夹。

## 安装包

### macOS Apple Silicon

- 新增 `PS-Sezhao-Installer-macOS-arm64-v0.7.0-beta.3.dmg`；
- DMG 内包含“安装到用户应用程序.command”；
- 默认安装到 `~/Applications/PS-Sezhao/`，不需要管理员权限；
- 更新只替换 App，不删除 `project` 和 `lut`；
- 同时继续提供可直接解压使用的便携 ZIP。

### Windows x64

- 新增 `PS-Sezhao-Installer-Windows-x64-v0.7.0-beta.3.exe`；
- 默认安装到 `%LOCALAPPDATA%\Programs\PS-Sezhao\`，不需要管理员权限；
- 支持开始菜单、可选桌面快捷方式和系统卸载入口；
- 卸载程序默认保留 `project` 和 `lut`；
- 同时继续提供便携 ZIP。

## 自动验证

构建流程会检查：

- Cube LUT 解析、1D 插值、3D 三线性插值和参数保存；
- 旧数据库迁移、旧文件保留和同级目录创建；
- 风格下拉框、工具边框分组和固定间距；
- macOS DMG、便携目录和打包后的真实窗口启动；
- Windows 安装器静默安装后的目录结构和真实窗口启动；
- Photoshop、Lightroom、RAW、项目归档和完整输出的既有功能。

## 发行文件

- `PS-Sezhao-Photoshop-v0.7.0-beta.3.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.7.0-beta.3.zip`
- `PS-Sezhao-LightroomClassic-Source-v0.7.0-beta.3.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.7.0-beta.3.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.7.0-beta.3.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.7.0-beta.3.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.7.0-beta.3.zip`
- `PS-Sezhao-Installer-macOS-arm64-v0.7.0-beta.3.dmg`
- `PS-Sezhao-Installer-Windows-x64-v0.7.0-beta.3.exe`
- `CHECKSUMS.txt`
