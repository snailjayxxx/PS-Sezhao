# PS-Sezhao v0.6.2

本版本修复 v0.6.1 独立版和 Lightroom 高精度窗口启动时出现的 `TclError: invalid command name` 崩溃，同时保留三栏宽度自由调整和右侧参数栏自适应功能。

## 崩溃原因

v0.6.1 为了建立新的三栏布局，在所有旧版界面补丁完成后销毁并重建了整个主界面。RAW 白平衡模块、胶片基底模块等功能仍保存着旧输入框的 Python 引用。

旧界面被销毁后，这些引用所对应的 Tk 控件已经不存在。重建 RAW 参数区时再次更新旧输入框状态，就会出现：

`_tkinter.TclError: invalid command name`

## 修复方式

v0.6.2 不再销毁或重建任何现有界面控件，而是直接增强程序原本已经存在的三栏 `ttk.Panedwindow`：

- 保留 RAW 白平衡输入框及其原始引用；
- 保留胶片基底、中性灰、撤销重做和历史记录控件；
- 保留文件列表、预览画布、拖放和滚轮绑定；
- 只调整三栏权重、初始分隔位置和最小可用宽度；
- 右侧滚动画布仍实时跟随当前右栏宽度；
- 下拉框、滑块和说明文字仍会随栏宽横向伸缩。

## 三栏调整

- 左侧：相片文件列表；
- 中间：图片预览与裁切；
- 右侧：输出与参数调整。

两条分隔线可以继续自由拖动。程序仅在鼠标释放或窗口尺寸变化后限制三栏的最小可用宽度，不会锁定固定比例。

## 回归测试

新增测试明确检查：

- 布局补丁中不再执行 `old_body.destroy()`；
- 不再第二次调用 `_build_controls_panel()` 重建参数控件；
- 不同窗口宽度下三栏均保持最低可用宽度；
- 用户拖动后的分隔位置只在超出最低宽度时进行修正；
- Windows、macOS、Photoshop、Lightroom、RAW 和拖放打包流程继续验证。

## 发行文件

- `PS-Sezhao-Photoshop-v0.6.2.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.6.2.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.6.2.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.6.2.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.6.2.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.6.2.zip`
