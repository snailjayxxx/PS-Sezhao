# PS-Sezhao v0.7.1

v0.7.1 是结束 v0.7.0 Beta 测试后的首个稳定版本。该版本冻结当前 `main` 的功能和数据格式，不再使用 Beta 标记，并作为 GitHub Latest 稳定版发布。

## 独立版主要功能

- 彩色负片和相机翻拍本地转正；
- 常见相机 RAW 直接读取；
- 缩略图、编辑代理和完整分辨率输出三级处理；
- 多个胶卷项目、项目级信息、画面编号和输出预设；
- 启动时不自动恢复上次照片；
- 关闭时询问是否保存本次胶卷项目；
- `.psszproj` 项目归档、跨电脑导入、原图重新定位和数据库备份恢复；
- 用户 1D/3D `.cube` LUT；
- TIFF、PNG、JPEG、ICC、尺寸调整、锐化、命名模板和接触印样；
- 可取消的后台输出队列。

## 裁切与几何校正

稳定版保留完整的双状态裁切入口：

```text
裁切 → 完成裁切
```

- 显示黄色裁切边框和八个控制点；
- 支持角点、边框中点、框内移动和框外重新绘制；
- “重置裁切”恢复完整画面；
- 左转 90°、右转 90°；
- 自动范围、拉直、水平翻转、垂直翻转和四角透视；
- 几何操作同步更新预览、裁切方向、项目状态和最终导出；
- 操作异常时显示具体错误，不再静默无反应。

## 风格与用户 LUT

- 扫描仪风格和胶卷风格独立选择；
- 选择框直接跟在标签后面并占满右栏剩余宽度；
- 候选列表嵌在右侧栏内部，不创建独立浮动窗口；
- 用户 LUT 自动加入胶卷风格列表；
- 胶卷强度控制 LUT 混合比例。

## 数据目录

macOS 标准安装版：

```text
~/Library/Application Support/PS-Sezhao/
├── workspace.sqlite3
├── project/
├── lut/
└── logs/
```

Windows 安装版和便携版使用应用外层同级的 `project`、`lut` 和 `logs` 目录。升级应用不会删除已有数据库、项目和 LUT。

## Adobe 版本

- Photoshop 2024（25.0）及以上：UXP CCX 和开发者加载包；
- Lightroom Classic 15.4 及以上：原生直接转正、高精度 16 位 TIFF 和恢复快照；
- 原始图片不会被覆盖。

## 自动验证

正式发布前执行：

- Photoshop 引擎与界面测试；
- Lightroom Lua 语法和原生配置测试；
- 独立版完整单元测试和真实 Tk 窗口测试；
- 实际点击裁切、旋转、水平翻转和垂直翻转；
- macOS Apple Silicon 打包后窗口；
- Windows x64 打包后窗口和安装器实际安装；
- RAW、拖放、项目迁移、Cube LUT、归档和输出回归测试；
- Photoshop、Lightroom、macOS、Windows 全部发行资产及 SHA-256 校验文件。

## 发行文件

- `PS-Sezhao-Photoshop-v0.7.1.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.7.1.zip`
- `PS-Sezhao-LightroomClassic-Source-v0.7.1.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.7.1.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.7.1.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.7.1.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.7.1.zip`
- `PS-Sezhao-Installer-macOS-arm64-v0.7.1.dmg`
- `PS-Sezhao-Installer-Windows-x64-v0.7.1.exe`
- `CHECKSUMS.txt`
