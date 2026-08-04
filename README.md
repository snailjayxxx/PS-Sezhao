# PS-Sezhao 胶片去色罩

PS-Sezhao 是面向彩色负片扫描和相机翻拍的本地图像处理项目。同一个仓库同时发布：

- **Photoshop 版**：UXP `.ccx` 插件，直接读取和写入图层。
- **Photoshop 开发者加载版**：完整插件目录，用 UXP Developer Tool 加载。
- **Lightroom Classic 版**：Lua `.lrplugin` 插件，渲染所选照片、打开调色窗口、生成 16 位 TIFF 并自动导回目录。
- **独立桌面版**：不依赖 Adobe，适合只需要胶片转正或无法使用 Adobe 宿主的用户。

照片只在本机处理，不上传服务器。

## 当前版本

统一版本：**v0.3.3**

目标环境：

- Photoshop 2024（25.0）或更高版本
- Lightroom Classic 15.4 / 15.4.1 或更高版本
- macOS Apple Silicon
- Windows x64

## Release 文件怎么选

| 使用场景 | 下载文件 |
|---|---|
| Photoshop 正常安装 | `PS-Sezhao-Photoshop-v0.3.3.ccx` |
| Photoshop 开发/调试或 CCX 安装器不可用 | `PS-Sezhao-Photoshop-Developer-v0.3.3.zip` |
| Lightroom Classic on Apple Silicon Mac | `PS-Sezhao-LightroomClassic-macOS-arm64-v0.3.3.zip` |
| Lightroom Classic on Windows x64 | `PS-Sezhao-LightroomClassic-Windows-x64-v0.3.3.zip` |
| 不使用 Adobe 的 Mac 用户 | `PS-Sezhao-Standalone-macOS-arm64-v0.3.3.zip` |
| 不使用 Adobe 的 Windows 用户 | `PS-Sezhao-Standalone-Windows-x64-v0.3.3.zip` |

CCX 发布前会自动验证：`manifest.json` 位于压缩包根目录、版本号一致、宿主为 Photoshop、最低版本为 25.0.0。开发者加载版的使用步骤见 [PHOTOSHOP_DEVELOPER_LOAD.md](PHOTOSHOP_DEVELOPER_LOAD.md)。

## 共同功能

- 自动估算未曝光胶片边框的橙色色罩
- 点击式胶片基底吸管
- 点击式中性色吸管
- 光密度空间转正
- 通用 C-41、Portra、Gold、Fujifilm、ECN-2 起始配置
- 曝光、对比度、中间调、饱和度
- 色温、绿—洋红色调、RGB 独立增益
- 黑点、白点、阴影、高光
- 大图预览和批量整卷处理
- 16 位 TIFF 输出

## Photoshop 2024 兼容性

v0.3.1 起将宿主最低版本降到 `25.0.0`，覆盖 Photoshop 2024 系列。插件同时移除了只在 Photoshop 25.10 及之后版本才可使用的 `executeAsModal.timeOut` 选项。

## Lightroom Classic v0.3.3 修复

v0.3.2 已改用 `LrFunctionContext.postAsyncTaskWithContext`，但错误处理仍使用普通 Lua `pcall`。在 Lightroom 使用的 Lua 5.1 协程模型中，普通 `pcall` 会让内部调用无法 `yield`，所以实际运行时仍会出现：

```text
PS-Sezhao 未能进入 Lightroom 后台任务
```

v0.3.3 将外层保护调用改为 Lightroom SDK 提供的：

```lua
LrTasks.pcall(processSelected, functionContext)
```

这样导出会话可以安全执行 `LrTasks.yield()`、等待 rendition 渲染，并避免重新落回主 UI 任务。自动测试同时检查：

- 必须通过 `postAsyncTaskWithContext` 启动；
- 必须使用 `LrTasks.pcall`；
- 禁止用普通 `pcall` 包裹 `processSelected`；
- 导出仍为 16 位 ProPhoto RGB TIFF。

## Lightroom Classic 工作流

1. 在图库中选择一张或多张负片。
2. 打开 `图库 → 增效工具额外功能 → PS-Sezhao：转正所选负片`。
3. Lightroom Classic 将当前编辑后的照片渲染为临时 16 位 ProPhoto RGB TIFF。
4. PS-Sezhao 打开独立大预览窗口。
5. 通过吸管和滑块完成调色，点击“批量应用并完成”。
6. 成品写入每张原图所在目录的 `PS-Sezhao` 子文件夹，并自动导入 Lightroom Classic。

## 独立版输入限制

v0.3.3 直接支持 TIFF、JPEG、PNG、BMP 和 WebP。相机 RAW 建议先导出为 16 位 TIFF。

## 开发检查

```bash
node scripts/validate.mjs
node --test tests/*.test.js
PYTHONPATH=standalone python -m unittest discover -s standalone/tests -v
bash scripts/build-release.sh
```

## 许可证

MIT。Adobe、Photoshop 和 Lightroom 是 Adobe 的商标；本项目与 Adobe 无隶属或背书关系。
