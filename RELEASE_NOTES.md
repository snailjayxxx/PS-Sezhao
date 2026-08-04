# PS-Sezhao v0.3.2

这是修复 Lightroom Classic 导出任务线程错误的维护版本。Photoshop、Lightroom Classic 与独立桌面版继续使用统一版本号构建。

## Lightroom Classic 关键修复

修复点击：

```text
图库 → 增效工具额外功能 → PS-Sezhao：转正所选负片
```

后出现的错误：

```text
AgExportSession:addRenditionsForPhotos: must not call on main UI task
```

根因是 `LrExportSession:renditions()` 的内部 rendition 创建仍可能落在菜单主 UI 调用栈。v0.3.2 做了以下调整：

- 使用 `LrFunctionContext.postAsyncTaskWithContext` 启动完整处理流程；
- 在创建 `LrExportSession` 和遍历 renditions 前确认任务可以 yield；
- 主动执行一次 `LrTasks.yield()`，确保 Lightroom 已离开菜单 UI 回调；
- 将 `progressScope` 和 `renderProgressPortion` 传给 rendition 任务；
- 统一处理进度条关闭，避免失败或取消后残留任务；
- 增加自动测试，禁止重新使用顶层 `LrTasks.startAsyncTask` 调用导出会话。

## Lightroom Classic 安装提醒

升级时请完全退出 Lightroom Classic，删除或移走旧的 `PS-Sezhao.lrplugin` 文件夹，再安装 v0.3.2。不要直接把新文件覆盖到旧目录，否则旧 Lua 文件或本地处理器可能残留。

## Photoshop 2024+

- 最低宿主版本继续为 Photoshop 2024（25.0.0）。
- 保留点击式胶片基底吸管、点击式中性色吸管、大图预览、连续画布预览和完整分辨率输出。
- 继续避免使用需要 Photoshop 25.10 的 `executeAsModal.timeOut`。

## Photoshop 安装文件

- `PS-Sezhao-Photoshop-v0.3.2.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.3.2.zip`

CCX 构建后会自动验证 `manifest.json` 位于包根目录，并核对版本号、Photoshop 宿主声明和 25.0.0 最低版本。

## Lightroom Classic 与独立桌面版

- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.3.2.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.3.2.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.3.2.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.3.2.zip`

Lightroom 插件包继续包含对应平台的本地处理器，不要求用户安装 Python。

## 自动检查

GitHub Actions 会自动完成：

- Lightroom 后台任务调用方式回归测试
- Lightroom Lua 语法检查
- Photoshop 2024 兼容性与 JavaScript 语法检查
- Photoshop 图像引擎和界面回归测试
- CCX 根目录结构与清单复核
- Python 图像引擎测试
- macOS Apple Silicon 与 Windows x64 构建
- 所有发行文件的 SHA-256 校验
