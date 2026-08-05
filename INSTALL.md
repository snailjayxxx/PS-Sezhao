# PS-Sezhao v0.7.0-beta.3 安装与使用说明

## 独立桌面版：优先使用安装包

### macOS Apple Silicon

1. 下载 `PS-Sezhao-Installer-macOS-arm64-v0.7.0-beta.3.dmg`。
2. 打开 DMG。
3. 双击 `安装到用户应用程序.command`。
4. 安装器会把完整程序目录放到：

```text
~/Applications/PS-Sezhao/
```

5. 在该目录中打开 `PS-Sezhao.app`。
6. 首次打开若 macOS 阻止未公证应用，在 Finder 中按住 Control 点击 App，选择“打开”；仍被阻止时进入 `系统设置 → 隐私与安全性`确认打开。

安装脚本不需要管理员权限。更新安装只替换 App，不删除胶卷项目和用户 LUT。

### Windows x64

1. 下载并运行 `PS-Sezhao-Installer-Windows-x64-v0.7.0-beta.3.exe`。
2. 默认安装位置：

```text
%LOCALAPPDATA%\Programs\PS-Sezhao\
```

3. 安装器会创建开始菜单快捷方式，并可选择创建桌面快捷方式。
4. SmartScreen 出现时，确认文件来自本仓库 Release，再选择“更多信息 → 仍要运行”。
5. 可从 Windows“已安装的应用”中卸载；卸载程序默认保留 `project` 和 `lut`。

安装过程不需要管理员权限。

## 独立桌面版：便携 ZIP

也可以下载：

- `PS-Sezhao-Standalone-macOS-arm64-v0.7.0-beta.3.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.7.0-beta.3.zip`

解压后保留整个 `PS-Sezhao` 文件夹，不要只移动其中的 `.app` 或 `.exe`。目录结构为：

```text
PS-Sezhao/
├── PS-Sezhao.app 或 PS-Sezhao.exe
├── project/
│   └── workspace.sqlite3
├── lut/
├── 安装说明.html
└── .ps-sezhao-portable
```

可把整个文件夹放在本机硬盘、移动硬盘或 NAS 的可写目录中。

## 胶卷项目保存位置

Beta 3 起，以下内容统一保存到同级 `project/workspace.sqlite3`：

- 普通工作区；
- 多个胶卷项目；
- 每张图片的转正、裁切、旋转、几何、RAW 和输出参数；
- 项目元数据；
- 输出预设；
- 当前打开的项目和图片顺序。

第一次启动会从旧位置自动复制数据库：

- macOS：`~/Library/Application Support/PS-Sezhao/workspace.sqlite3`
- Windows：`%LOCALAPPDATA%\PS-Sezhao\workspace.sqlite3`

旧数据库不会删除。新 `project` 文件夹中会生成 `MIGRATED_FROM.txt` 记录迁移来源。

应用内可点击左侧胶卷项目区域的“打开 project 文件夹”。

## 用户 LUT

右侧“胶卷风格”区域提供：

```text
添加 LUT…
打开 LUT 文件夹
```

当前支持标准 `.cube` 文件，包括 1D 和 3D LUT。添加后：

1. 程序验证 LUT 格式；
2. 文件复制到同级 `lut` 文件夹；
3. LUT 出现在“胶卷风格”下拉列表；
4. 使用“胶卷强度”控制 LUT 混合比例；
5. 预览、独立版完整输出和 Lightroom 高精度输出使用同一处理流程。

项目只保存 LUT 文件名。跨电脑迁移时要同时复制 `project` 和 `lut` 文件夹。LUT 缺失或损坏时项目仍可打开，程序会使用基础转正结果并显示提示。

## Photoshop 2024（25.0）或更高版本

1. 下载 `PS-Sezhao-Photoshop-v0.7.0-beta.3.ccx`。
2. 完全退出 Photoshop。
3. 双击 CCX，通过 Creative Cloud Desktop 安装。
4. 重新打开 Photoshop，从 `插件 → 胶片去色罩` 启动。
5. 确认顶部显示 `PS-SEZHAO · 0.7.0-beta.3`。

开发者加载版为 `PS-Sezhao-Photoshop-Developer-v0.7.0-beta.3.zip`。通过 UXP Developer Tool 选择解压目录中的 `manifest.json` 并点击 `Load`。

独立版用户 LUT 功能目前不等于 Photoshop UXP 面板导入 LUT；Photoshop 中可继续使用 Photoshop 自身的颜色查找调整图层。

## Lightroom Classic 15.4+

- Apple Silicon Mac：`PS-Sezhao-LightroomClassic-macOS-arm64-v0.7.0-beta.3.zip`
- Windows x64：`PS-Sezhao-LightroomClassic-Windows-x64-v0.7.0-beta.3.zip`

安装步骤：

1. 完全退出 Lightroom Classic。
2. 解压下载文件，保留完整 `PS-Sezhao.lrplugin` 文件夹。
3. 打开 Lightroom Classic 的插件管理器。
4. 移除旧版 PS-Sezhao 插件记录。
5. 点击“添加”，选择新的 `PS-Sezhao.lrplugin` 文件夹。

不要把新文件直接覆盖到旧插件目录。高精度 16 位 TIFF 菜单使用包内独立处理器；原生直接转正不需要本地处理器。

## 撤销、裁切和 RAW

- 撤销：`Ctrl/Cmd + Z`
- 重做：`Ctrl/Cmd + Y` 或 `Ctrl/Cmd + Shift + Z`
- 独立版按每张照片分别保留历史；
- 裁切、旋转、拉直、翻转和四角透视不会修改原图；
- 支持 CR2、CR3、NEF、ARW、RAF、RW2、ORF、PEF、SRW、DNG 等常见 RAW；
- 完整 RAW 解码使用 16 位、线性 Gamma、关闭自动提亮和 ProPhoto RGB。

## 关于第三方修改版 Adobe 软件

本项目不提供绕过 Adobe 授权、修改 Creative Cloud 或破解插件验证的方法。无法使用 Adobe 宿主时，可使用独立桌面版。
