# PS-Sezhao v0.7.0-beta.7

本版本恢复完整裁切编辑，并修复独立版中旋转、水平翻转、垂直翻转和拉直操作无反应的问题。v0.6.3 继续保留为 Latest 稳定版。

## 裁切功能恢复

工具栏重新使用完整的双状态裁切入口：

```text
裁切 → 完成裁切
```

- 点击“裁切”后显示完整画面；
- 显示黄色裁切边框和八个控制点；
- 可拖动四个角点和四个边框中点改变范围；
- 可拖动框内区域移动裁切框；
- 可在框外重新拖出裁切范围；
- 点击“完成裁切”后应用范围并返回普通预览；
- “重置裁切”恢复完整画面；
- 顶部状态区域显示当前裁切操作和保留比例。

## 旋转与翻转修复

- 左转 90°、右转 90°重新绑定到最终旋转服务；
- 旋转同步更新当前照片状态、编辑代理、裁切方向和最终导出；
- 水平翻转与垂直翻转重新绑定到最终几何服务；
- 修复几何设置入口未发布导致的按钮异常；
- 同一问题涉及的拉直操作也已恢复；
- 操作异常时会弹出具体错误并更新顶部状态，不再静默无反应。

## 保留的界面与数据优化

- 扫描仪风格与胶卷风格使用右栏内嵌完整宽度选择器；
- 用户 1D/3D `.cube` LUT；
- macOS 首次启动自动创建 `project`、`lut` 和 `logs`；
- 普通启动不恢复上次照片；
- 关闭程序时询问是否保存本次胶卷项目；
- 标准 macOS Applications DMG 与 Windows 安装器。

## 自动验证

- 真实 Tk 窗口实际点击“裁切”，确认进入完整裁切编辑；
- 确认按钮切换为“完成裁切”并生成裁切叠加框；
- 实际点击左右旋转按钮并检查照片方向和代理尺寸；
- 实际点击水平翻转和垂直翻转并检查几何状态；
- 确认按钮点击时调用最终安装的服务方法；
- Linux 真实 Tk 窗口；
- macOS Apple Silicon 打包后窗口；
- Windows x64 打包后窗口和安装器实际安装；
- Photoshop、Lightroom、RAW、LUT、项目和输出既有测试。

## 发行文件

- `PS-Sezhao-Photoshop-v0.7.0-beta.7.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.7.0-beta.7.zip`
- `PS-Sezhao-LightroomClassic-Source-v0.7.0-beta.7.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.7.0-beta.7.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.7.0-beta.7.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.7.0-beta.7.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.7.0-beta.7.zip`
- `PS-Sezhao-Installer-macOS-arm64-v0.7.0-beta.7.dmg`
- `PS-Sezhao-Installer-Windows-x64-v0.7.0-beta.7.exe`
- `CHECKSUMS.txt`
