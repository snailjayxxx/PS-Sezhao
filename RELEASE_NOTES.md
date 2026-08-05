# PS-Sezhao v0.7.0-beta.6

本版本修复 Windows 独立版中扫描仪风格与胶卷风格候选菜单跑到屏幕左上角的问题，并按照右侧栏的实际宽度重新设计风格选择区域。v0.6.3 继续保留为 Latest 稳定版。

## 风格选择器

风格区域现在采用明确的一行布局：

```text
扫描仪风格  [选择框占满本行剩余宽度 ▼]
胶卷风格    [选择框占满本行剩余宽度 ▼]
```

- 标签保持固定宽度；
- 选择框紧跟在“扫描仪风格”和“胶卷风格”文字后面；
- 选择框使用右侧栏剩余的全部宽度；
- 当前风格名称不会再被压缩到只显示前几个字；
- 点击输入区域或箭头都可以展开选项。

## 内嵌候选列表

- 删除依赖屏幕绝对坐标的独立 `Toplevel` 浮动菜单；
- 候选列表直接嵌入右侧风格栏内部；
- 列表出现在对应选择框正下方；
- 列表宽度与选择框一致，不会越过应用窗口；
- Windows 多显示器、缩放比例和窗口未完全显示时也不会跑到屏幕左上角；
- 最多显示 12 行，更多项目通过滚动条查看；
- 打开胶卷风格列表前自动刷新用户 LUT；
- 选择项目后继续触发现有预览、撤销历史和项目自动保存。

## 保留的 Beta 5 修复

- macOS 首次启动自动创建 `project`、`lut` 和 `logs`；
- macOS 数据库保持在 `~/Library/Application Support/PS-Sezhao/workspace.sqlite3`；
- 启动失败日志位于 `~/Library/Application Support/PS-Sezhao/logs/startup.log`；
- 普通启动不恢复上次照片；
- 关闭程序时询问是否保存本次胶卷项目；
- 右上角显示程序、旋转、裁切和几何状态；
- 用户 1D/3D `.cube` LUT；
- 标准 macOS Applications DMG 与 Windows 安装器。

## 自动验证

- 风格选择框宽度必须覆盖右栏中标签后的剩余空间；
- 展开风格列表时不得创建新的顶层窗口；
- 候选列表必须位于右栏内部并与选择框等宽；
- 选择内嵌列表项目后必须更新原有风格变量；
- 顶部状态面板和本地状态标签继续保持正确；
- Linux 真实 Tk 窗口；
- macOS Apple Silicon 打包后窗口；
- Windows x64 打包后窗口和安装器实际安装；
- Photoshop、Lightroom、RAW、LUT、项目和输出既有测试。

## 发行文件

- `PS-Sezhao-Photoshop-v0.7.0-beta.6.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.7.0-beta.6.zip`
- `PS-Sezhao-LightroomClassic-Source-v0.7.0-beta.6.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.7.0-beta.6.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.7.0-beta.6.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.7.0-beta.6.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.7.0-beta.6.zip`
- `PS-Sezhao-Installer-macOS-arm64-v0.7.0-beta.6.dmg`
- `PS-Sezhao-Installer-Windows-x64-v0.7.0-beta.6.exe`
- `CHECKSUMS.txt`
