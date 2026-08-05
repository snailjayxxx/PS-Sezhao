# PS-Sezhao v0.5.5

本版本修复独立程序无法通过“添加图像”或“添加文件夹”导入素材的问题，并加入从 Windows 资源管理器或 macOS Finder 直接拖入图片、RAW 文件和文件夹的功能。

## 修复添加图像和文件夹

v0.5.4 的历史记录补丁只把若干方法注册成带下划线的内部名称，但导入流程调用的是公开名称。首次读取当前控制参数时会触发 `AttributeError`，Tkinter 回调又没有把错误显示在界面上，因此表现为点击按钮后没有反应。

v0.5.5 重新发布这些方法，并让按钮导入、文件夹导入和拖放导入统一使用同一套路径处理。

## 拖放添加

独立版现在支持把以下内容拖到主窗口、图像预览区域或文件列表：

- 单张或多张常规图片；
- 单张或多张 RAW 文件；
- 包含图片和 RAW 的文件夹；
- 同时拖入文件和文件夹。

文件夹会递归查找支持的素材，重复路径不会再次添加。支持格式包括 TIFF、JPEG、PNG、BMP、WebP、DNG、CR2、CR3、NEF、ARW、RAF、RW2、ORF、PEF 和 SRW。

## 打包修复

Windows 和 macOS 构建现在都会显式收集 `tkinterdnd2` 与 TkDND 运行库。自动构建同时检查：

- Photoshop、Lightroom、独立版和 package.json 的版本号均为 0.5.5；
- 导入所需的 v0.5.4 方法别名已经恢复；
- 文件夹能够识别常规图片和 RAW；
- Windows/macOS 安装包包含拖放运行库；
- 原有 RAW、历史记录、裁切和调色测试继续通过。

## 发行文件

- `PS-Sezhao-Photoshop-v0.5.5.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.5.5.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.5.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.5.5.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.5.5.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.5.5.zip`
