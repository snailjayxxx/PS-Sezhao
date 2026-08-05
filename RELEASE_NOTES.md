# PS-Sezhao v0.7.0-beta.5

本版本修复 macOS 标准拖拽安装后，`project`、`lut` 文件夹不会自动出现，以及窗口版启动失败时没有任何错误信息的问题。v0.6.3 继续保留为 Latest 稳定版。

## macOS 首次启动目录

标准安装方式仍然是：

```text
打开 DMG → 将 PS-Sezhao.app 拖到 Applications → 从“应用程序”打开
```

首次成功启动时，程序会自动创建：

```text
~/Library/Application Support/PS-Sezhao/
├── workspace.sqlite3
├── project/
│   └── README.txt
├── lut/
│   └── README.txt
└── logs/
    ├── README.txt
    └── startup.log
```

- `workspace.sqlite3` 保持旧版本原位置，不强制迁移；
- `project` 用于项目归档、数据库备份和迁移文件；
- `lut` 用于用户添加的 1D/3D `.cube` LUT；
- `logs/startup.log` 用于启动和崩溃诊断；
- 更新或替换 `/Applications/PS-Sezhao.app` 不会删除这些用户数据。

拖动安装本身只复制 `.app`，不能在 `/Applications` 旁边创建可写数据目录。因此目录初始化由 App 的首次启动完成。

## 启动失败诊断

- 在 Tk 窗口创建之前先初始化数据目录和日志；
- 记录版本、系统、Python、可执行文件、App 容器、数据库、项目目录和 LUT 目录；
- 记录主线程与后台线程未捕获异常；
- 启动阶段崩溃时，在 macOS 显示系统提示并给出日志路径；
- 日志自动轮换，单个文件上限 2 MiB，保留最近 3 份。

默认日志位置：

```text
~/Library/Application Support/PS-Sezhao/logs/startup.log
```

## 便携版

便携 ZIP 继续使用 App/EXE 同级数据结构：

```text
PS-Sezhao/
├── PS-Sezhao.app 或 PS-Sezhao.exe
├── project/
├── lut/
├── logs/
└── .ps-sezhao-portable
```

## macOS 安全提示

当前仓库尚未配置 Apple Developer ID 签名和公证凭据，因此未签名测试包仍可能被 Gatekeeper 阻止。Beta 5 增加的启动日志只能记录 App 已经获准执行之后发生的程序错误，无法绕过 Gatekeeper。

要让普通用户首次双击直接打开，仍需配置：

```text
APPLE_CERTIFICATE_P12_BASE64
APPLE_CERTIFICATE_PASSWORD
APPLE_SIGNING_IDENTITY
APPLE_ID
APPLE_APP_SPECIFIC_PASSWORD
APPLE_TEAM_ID
```

## 自动验证

- macOS 安装版数据库保持原位置；
- 首次启动创建 `project`、`lut`、`logs`；
- 启动日志写入版本和目录信息；
- 窗口创建前异常写入日志；
- Linux 真实 Tk 窗口；
- macOS Apple Silicon 打包后窗口；
- Windows 安装器实际安装与启动；
- Photoshop、Lightroom、RAW、LUT、项目和输出既有测试。

## 发行文件

- `PS-Sezhao-Photoshop-v0.7.0-beta.5.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.7.0-beta.5.zip`
- `PS-Sezhao-LightroomClassic-Source-v0.7.0-beta.5.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.7.0-beta.5.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.7.0-beta.5.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.7.0-beta.5.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.7.0-beta.5.zip`
- `PS-Sezhao-Installer-macOS-arm64-v0.7.0-beta.5.dmg`
- `PS-Sezhao-Installer-Windows-x64-v0.7.0-beta.5.exe`
- `CHECKSUMS.txt`
