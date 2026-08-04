# PS-Sezhao v0.3.3

这是继续修复 Lightroom Classic 导出协程问题的维护版本。Photoshop、Lightroom Classic 与独立桌面版继续使用统一版本号构建。

## Lightroom Classic 关键修复

v0.3.2 已使用 `LrFunctionContext.postAsyncTaskWithContext` 启动导出，但其内部又用普通 Lua `pcall` 包裹 `processSelected`。Lightroom 使用的 Lua 5.1 协程不能跨普通 `pcall` 边界安全 `yield`，因此实际测试中出现：

```text
PS-Sezhao 未能进入 Lightroom 后台任务
```

v0.3.3 将该保护调用改为：

```lua
LrTasks.pcall(processSelected, functionContext)
```

这使 `LrTasks.canYield()` 在处理函数中保持为真，导出流程可以：

- 主动执行 `LrTasks.yield()`；
- 创建 `LrExportSession`；
- 等待 `rendition:waitForRender()`；
- 调用本地 PS-Sezhao 调整窗口；
- 将生成的 16 位 TIFF 导回 Lightroom Classic。

自动检查新增规则：禁止普通 `pcall` 包裹 `processSelected`，并强制使用 `LrTasks.pcall`。

## Lightroom Classic 安装提醒

升级时请完全退出 Lightroom Classic，删除或移走旧的 `PS-Sezhao.lrplugin` 文件夹，再安装 v0.3.3。不要直接把新文件覆盖到旧目录。

## Photoshop 2024+

- 最低宿主版本继续为 Photoshop 2024（25.0.0）。
- 保留点击式胶片基底吸管、点击式中性色吸管、大图预览、连续画布预览和完整分辨率输出。
- 继续避免使用需要 Photoshop 25.10 的 `executeAsModal.timeOut`。

## 发行文件

- `PS-Sezhao-Photoshop-v0.3.3.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.3.3.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.3.3.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.3.3.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.3.3.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.3.3.zip`

Lightroom 插件包继续包含对应平台的本地处理器，不要求用户安装 Python。

## 自动检查

GitHub Actions 会自动完成：

- Lightroom yield-safe 保护调用回归测试
- Lightroom Lua 语法检查
- Photoshop 2024 兼容性与 JavaScript 语法检查
- Photoshop 图像引擎和界面回归测试
- CCX 根目录结构与清单复核
- Python 图像引擎测试
- macOS Apple Silicon 与 Windows x64 构建
- 所有发行文件的 SHA-256 校验
