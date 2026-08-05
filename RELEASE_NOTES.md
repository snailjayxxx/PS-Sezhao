# PS-Sezhao v0.5.5

这是修复 v0.5.4 桌面版图片导入失效问题的维护版本，并新增从系统文件管理器拖放图片或文件夹。

## 修复“添加图像/添加文件夹无反应”

v0.5.4 的历史记录补丁把若干方法注册为带下划线的内部名称，例如：

```text
_history_for
```

但加载第一张图片时调用了不存在的公开名称：

```text
history_for
```

因此文件选择完成后在 `load_index()` 中触发 `AttributeError`。Windows 和 macOS 发行版使用无控制台窗口构建，异常没有显示出来，用户看到的现象就是按钮选择文件后没有任何反应。文件夹导入最终也调用同一条加载路径，因此同样失效。

v0.5.5 在创建程序实例前修复全部相关方法别名，包括胶片基底直接值和撤销/重做历史方法。普通图片、相机 RAW、单文件添加、批量添加和文件夹添加恢复正常。

## 导入错误不再静默

`open_paths()` 外层新增异常处理。以后导入链路若再发生错误，程序会：

- 在状态栏显示“添加图片失败”；
- 弹出具体异常内容；
- 提示保留错误信息用于反馈。

不再出现点击后完全无提示的情况。

## 从资源管理器或 Finder 拖放添加

独立桌面版和 Lightroom 高精度窗口现在支持将以下内容直接拖入程序窗口、中央图片区域或左侧图片列表：

- 一张图片；
- 多张图片；
- 相机 RAW；
- 一个或多个文件夹。

拖入文件夹时会递归查找其中支持的图像和 RAW，自动去重后加入左侧列表。支持带空格、中文和其他 Unicode 字符的路径。

拖动进入窗口时状态栏显示“松开鼠标即可添加”，离开窗口时显示拖放已取消，完成后显示实际新增数量。

## 支持格式

```text
TIFF / JPEG / PNG / BMP / WebP
CR2 / CR3 / NEF / NRW / ARW / RAF / RW2 / ORF / PEF / SRW / DNG
```

## 拖放运行库打包

桌面版使用 TkinterDnD2 / TkDnD 提供 Windows、macOS 和 Linux/X11 的系统级文件拖放。

GitHub Actions 构建时会：

- 使用专用 PyInstaller hook 收集 TkDnD 的 Tcl 脚本和平台共享库；
- 在 macOS 应用包中检查 TkDnD 文件；
- 在 Windows EXE 归档中检查 `tkinterdnd2` 和原生 `tkdnd` 运行库；
- 同时继续检查 rawpy 和 LibRaw。

## 继续保留 v0.5.4 功能

- 每张照片独立的撤销和重做；
- 胶片基底直接编辑最终 R/G/B；
- 中性灰吸管对应的 R/G/B 输出增益可手动修改；
- 原图胶片基底吸管；
- 左右侧栏滚轮；
- 多图、裁切、同步和批量导出；
- 相机 RAW 直读与16位线性 ProPhoto 解码；
- Lightroom 原生直接转正和高精度16位TIFF；
- Photoshop 2024+。

## 发行文件

- `PS-Sezhao-Photoshop-v0.5.5.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.5.5.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.5.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.5.5.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.5.5.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.5.5.zip`
