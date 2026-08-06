# PS-Sezhao v0.7.1 安装与使用说明

## macOS Apple Silicon

1. 下载 `PS-Sezhao-Installer-macOS-arm64-v0.7.1.dmg`。
2. 打开 DMG。
3. 将 `PS-Sezhao.app` 拖到右侧 `Applications` 文件夹。
4. 从 Finder 的“应用程序”中打开 PS-Sezhao。

拖动安装只复制 `.app`。首次成功启动时，程序会自动创建：

```text
~/Library/Application Support/PS-Sezhao/
├── workspace.sqlite3
├── project/
├── lut/
└── logs/
    └── startup.log
```

- 数据库保持在旧版本使用的根目录；
- `project` 用于项目归档和备份；
- `lut` 用于用户 `.cube` LUT；
- `logs/startup.log` 记录启动错误；
- 更新或替换 App 不会删除上述目录。

当前未配置 Apple Developer ID 的发行包仍会被 Gatekeeper 要求确认。程序代码无法安全绕过 Gatekeeper；只有 Developer ID 签名和 Apple 公证后才能让普通用户直接双击打开。

程序获准运行后若仍启动失败，会弹出错误提示并显示日志路径。也可以在 Finder 中使用“前往文件夹”打开：

```text
~/Library/Application Support/PS-Sezhao/logs/
```

## Windows x64

1. 下载并运行 `PS-Sezhao-Installer-Windows-x64-v0.7.1.exe`。
2. 默认安装到 `%LOCALAPPDATA%\Programs\PS-Sezhao\`。
3. 安装器会创建开始菜单快捷方式，并可选择创建桌面快捷方式。
4. SmartScreen 出现时，确认文件来自本仓库 Release，再选择“更多信息 → 仍要运行”。

Windows 安装版使用应用同级的：

```text
project\workspace.sqlite3
lut\
logs\
```

## 便携 ZIP

- `PS-Sezhao-Standalone-macOS-arm64-v0.7.1.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.7.1.zip`

便携版必须保留完整外层 `PS-Sezhao` 文件夹：

```text
PS-Sezhao/
├── PS-Sezhao.app 或 PS-Sezhao.exe
├── project/
│   └── workspace.sqlite3
├── lut/
├── logs/
├── 安装说明.html
└── .ps-sezhao-portable
```

## 裁切工具

点击“裁切”后会进入完整画面编辑模式：

- 按钮文字变为“完成裁切”；
- 显示黄色裁切边框和八个控制点；
- 可拖动角点、边框中点改变范围；
- 可拖动框内区域移动裁切框；
- 可在框外重新拖出一个裁切范围；
- 再次点击“完成裁切”后应用范围并回到普通预览；
- “重置裁切”恢复完整画面。

## 旋转与几何调整

- “左转 90°”“右转 90°”会立即更新预览、裁切方向和导出方向；
- “水平翻转”“垂直翻转”会立即更新当前照片的几何状态；
- 拉直、四角透视和重置几何继续使用同一套每张照片独立设置；
- 操作失败时会显示具体错误，不再静默无反应。

## 风格选择

右侧“扫描仪与胶卷风格”区域使用内嵌选择器：

```text
扫描仪风格  [完整宽度选择框 ▼]
胶卷风格    [完整宽度选择框 ▼]
```

- 选择框紧跟在标签后面并占满右侧剩余宽度；
- 点击选择框或箭头后，候选列表直接在选择框下方展开；
- 候选列表位于应用右侧栏内部，不会跑到屏幕左上角；
- 用户 LUT 会自动加入胶卷风格列表；
- 超过 12 个选项时使用滚动条。

## 启动与关闭

- 普通启动不自动打开上次关闭时的照片；
- 已保存胶卷项目通过左侧“打开”手动恢复；
- 关闭且当前有照片时，询问是否保存本次胶卷项目；
- “是”保存后退出；“否”直接退出；“取消”返回程序；
- 临时工作区保存时要求输入胶卷项目名称。

## 用户 LUT

右侧“胶卷风格”区域提供“添加 LUT…”和“打开 LUT 文件夹”。支持标准 1D/3D `.cube` 文件。

## Photoshop 2024（25.0）或更高版本

1. 下载 `PS-Sezhao-Photoshop-v0.7.1.ccx`。
2. 完全退出 Photoshop。
3. 双击 CCX，通过 Creative Cloud Desktop 安装。
4. 重新打开 Photoshop，从 `插件 → 胶片去色罩` 启动。

## Lightroom Classic 15.4+

- Apple Silicon Mac：`PS-Sezhao-LightroomClassic-macOS-arm64-v0.7.1.zip`
- Windows x64：`PS-Sezhao-LightroomClassic-Windows-x64-v0.7.1.zip`

退出 Lightroom Classic，解压下载文件，在插件管理器中移除旧记录后，重新添加完整的 `PS-Sezhao.lrplugin` 文件夹。
