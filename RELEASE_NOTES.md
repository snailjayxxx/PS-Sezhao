# PS-Sezhao v0.5.6

本版本是 v0.5.5 的启动崩溃热修复版。

## 修复 Windows 启动递归崩溃

v0.5.5 为启用拖放功能，直接把全局 `tkinter.Tk` 替换成了 `TkinterDnD.Tk`。但 `TkinterDnD.Tk.__init__()` 内部仍会调用 `tkinter.Tk.__init__()`，因此启动时不断调用自身，最终出现：

```text
RecursionError: maximum recursion depth exceeded
```

v0.5.6 不再修改系统级 `tkinter.Tk`。程序改用一个仅对 PS-Sezhao 启动模块生效的轻量代理：

- PS-Sezhao 创建窗口时使用 `TkinterDnD.Tk`；
- `tkinterdnd2` 内部仍能调用原始 `tkinter.Tk`；
- 其他 Canvas、StringVar、Frame 等 tkinter 组件保持原样；
- 重复初始化拖放模块也不会形成嵌套代理。

## 回归测试

新增专门测试确认：

- 启用拖放前后的全局 `tkinter.Tk` 完全相同；
- PS-Sezhao 自己的根窗口使用 `TkinterDnD.Tk`；
- 其他 tkinter 类仍由原始模块提供；
- 连续安装两次拖放根窗口配置不会递归。

同时保留 v0.5.5 的功能：

- 修复“添加图像”和“添加文件夹”无响应；
- 支持拖入单张、多张图片和 RAW；
- 支持拖入文件夹并递归查找图片和 RAW；
- 自动去除重复路径；
- Windows 和 macOS 安装包包含 TkDND 运行库。

## 发行文件

- `PS-Sezhao-Photoshop-v0.5.6.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.5.6.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.6.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.5.6.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.5.6.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.5.6.zip`
