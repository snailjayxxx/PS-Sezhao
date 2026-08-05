# PS-Sezhao v0.7.0-beta.4

本版本调整独立版启动与关闭流程，修复风格列表和状态文字在 macOS 下仍然显示不完整的问题，并把 macOS 安装方式改为标准 Applications DMG。v0.6.3 继续保留为 Latest 稳定版。

## 启动和关闭

- 普通启动时不再自动打开上次关闭时的照片；
- 上次临时工作区的照片列表会在干净启动时清除；
- 已保存胶卷项目仍保留在数据库中，可通过左侧“打开”手动恢复；
- 关闭且当前有照片时，弹出“是 / 否 / 取消”询问；
- 选择“是”保存本次胶卷项目后退出；
- 临时工作区选择保存时，会要求输入胶卷项目名称；
- 选择“否”直接关闭并清除临时照片列表；
- 选择“取消”返回程序，不关闭窗口。

## 风格完整宽度列表

- 扫描仪风格和胶卷风格不再使用 macOS 原生窄弹出列表；
- 点击后会在右侧风格栏内部展开完整宽度列表；
- 列表左边缘与风格区域对齐，右边缘不会越出程序窗口；
- 最多显示 14 行并提供滚动条；
- 用户 LUT 会在打开胶卷列表前自动刷新；
- 选择后继续触发现有预览、历史和项目保存流程。

## 顶部状态空间

- 右上角空白区域改为“当前状态”面板；
- 程序状态、旋转状态、裁切状态和几何状态集中显示；
- 旋转工具组不再因为状态文字过长而被截断；
- 裁切和几何工具栏只保留实际工具，按钮间距保持固定。

## macOS 标准安装

- DMG 改为标准拖拽安装：把 `PS-Sezhao.app` 拖到 `Applications`；
- 不再包含或执行 `.command` 安装脚本；
- App 会直接显示在 Finder 的“应用程序”窗口；
- macOS 标准安装版数据库恢复为原位置：`~/Library/Application Support/PS-Sezhao/workspace.sqlite3`；
- 用户 LUT 位于 `~/Library/Application Support/PS-Sezhao/lut/`；
- 便携 ZIP 仍保留应用同级 `project` 和 `lut` 结构。

## Apple 签名与公证

- 构建流程新增 Developer ID 签名和 Apple 公证支持；
- 配置完整 Apple 证书与公证 Secrets 时，自动签名 App、提交公证、装订票据、签名并公证 DMG；
- 未配置凭据时仍生成未签名测试包，并在 Actions 中明确显示警告；
- 未签名包仍需要用户在 macOS“隐私与安全性”中手动确认，这无法通过普通脚本安全绕过。

需要配置的仓库 Secrets：

```text
APPLE_CERTIFICATE_P12_BASE64
APPLE_CERTIFICATE_PASSWORD
APPLE_SIGNING_IDENTITY
APPLE_ID
APPLE_APP_SPECIFIC_PASSWORD
APPLE_TEAM_ID
```

## 自动验证

- 普通启动为空白工作区；
- 已保存胶卷项目不会自动打开，但可手动恢复；
- 关闭保存、不保存和取消三条路径；
- 临时工作区保存为命名胶卷项目；
- 风格完整宽度弹窗和顶部状态面板；
- macOS 标准 DMG 中存在 Applications 链接且不含 `.command`；
- Windows 安装器、便携目录和安装后真实窗口；
- Photoshop、Lightroom、RAW、用户 LUT、输出和项目归档既有功能。

## 发行文件

- `PS-Sezhao-Photoshop-v0.7.0-beta.4.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.7.0-beta.4.zip`
- `PS-Sezhao-LightroomClassic-Source-v0.7.0-beta.4.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.7.0-beta.4.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.7.0-beta.4.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.7.0-beta.4.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.7.0-beta.4.zip`
- `PS-Sezhao-Installer-macOS-arm64-v0.7.0-beta.4.dmg`
- `PS-Sezhao-Installer-Windows-x64-v0.7.0-beta.4.exe`
- `CHECKSUMS.txt`
