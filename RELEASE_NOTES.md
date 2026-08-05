# PS-Sezhao v0.6.3

本版本修复 macOS 独立版在加载拖放组件时可能无法启动的问题，并加强 Windows 与 macOS 发行包的真实窗口启动验证。

## 拖放组件兼容处理

程序不再使用拖放专用根窗口直接启动，而是先创建普通 Tk 窗口，再尝试把拖放能力加载到当前 Tcl/Tk 解释器中。

处理结果分为两种：

- 拖放组件加载成功：支持从 Finder 或资源管理器拖入图片和文件夹；
- 拖放组件加载失败：自动保留普通 Tk 窗口，程序继续正常打开。

降级后仅暂时不能直接拖入文件，“添加图像”和“添加文件夹”按钮仍可正常使用。拖放动态库与系统 Tcl/Tk 不兼容时，不再出现启动阶段崩溃。

## 拖放运行时更新

- 将 `tkinterdnd2` 更新到 `0.6.2` 系列；
- 收集新版提供的平台动态库与 Tcl 脚本；
- 增加独立 PyInstaller hook；
- 保留 Windows、macOS 和 Linux 的运行时检测。

## 真实发行包启动检查

以前只执行 `--help`，不会创建图形窗口，因此无法发现 TkDND 加载错误。

现在 Windows 和 macOS 构建完成后会：

1. 启动打包后的可执行程序；
2. 创建真实 Tk 根窗口；
3. 建立文件列表、图片画布和参数栏；
4. 验证 TkDND 运行时可以在构建环境加载；
5. 完成 `update_idletasks()` 后关闭窗口。

只有真实窗口和拖放运行时均通过，发行任务才会继续。

## 保留功能

- RAW 解码和嵌入预览；
- 三栏自由调整；
- 裁切、旋转与批量输出；
- 扫描仪与胶卷双风格；
- Lightroom 高精度流程；
- Photoshop 插件。

## 发行文件

- `PS-Sezhao-Photoshop-v0.6.3.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.6.3.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.6.3.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.6.3.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.6.3.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.6.3.zip`
