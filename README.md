# PS-Sezhao 胶片去色罩

PS-Sezhao 是面向彩色负片扫描和相机翻拍的本地图像处理项目。照片只在本机处理，不上传服务器。

同一个仓库发布：

- **Photoshop 版**：UXP `.ccx` 插件，直接读取和写入 Photoshop 图层；
- **Photoshop 开发者加载版**：完整 UXP 插件目录；
- **Lightroom Classic 版**：原生直接转正、高精度 16 位 TIFF、恢复快照；
- **独立桌面版**：不依赖 Adobe，支持相机 RAW、整卷项目、几何校正、用户 LUT 和批量输出。

## 当前版本

统一测试版本：**v0.7.0-beta.3**

Latest 稳定版继续保留为 **v0.6.3**。

支持环境：

- Photoshop 2024（25.0）或更高版本；
- Lightroom Classic 15.4 或更高版本；
- macOS Apple Silicon；
- Windows x64。

## Release 文件

| 使用场景 | 下载文件 |
|---|---|
| macOS 独立版安装器 | `PS-Sezhao-Installer-macOS-arm64-v0.7.0-beta.3.dmg` |
| Windows 独立版安装器 | `PS-Sezhao-Installer-Windows-x64-v0.7.0-beta.3.exe` |
| macOS 独立版便携包 | `PS-Sezhao-Standalone-macOS-arm64-v0.7.0-beta.3.zip` |
| Windows 独立版便携包 | `PS-Sezhao-Standalone-Windows-x64-v0.7.0-beta.3.zip` |
| Photoshop 正常安装 | `PS-Sezhao-Photoshop-v0.7.0-beta.3.ccx` |
| Photoshop 开发者加载 | `PS-Sezhao-Photoshop-Developer-v0.7.0-beta.3.zip` |
| Lightroom Classic · Apple Silicon | `PS-Sezhao-LightroomClassic-macOS-arm64-v0.7.0-beta.3.zip` |
| Lightroom Classic · Windows x64 | `PS-Sezhao-LightroomClassic-Windows-x64-v0.7.0-beta.3.zip` |
| Lightroom 插件源码 | `PS-Sezhao-LightroomClassic-Source-v0.7.0-beta.3.zip` |

完整安装步骤见 [`INSTALL.md`](INSTALL.md)。

## 独立版目录结构

安装版和便携版都使用应用同级数据目录：

```text
PS-Sezhao/
├── PS-Sezhao.app 或 PS-Sezhao.exe
├── project/
│   └── workspace.sqlite3
├── lut/
├── 安装说明.html
└── .ps-sezhao-portable
```

`project/workspace.sqlite3` 保存普通工作区、多个胶卷项目、每张图片参数和输出预设。Beta 3 首次启动会从旧位置自动复制数据库，旧文件继续保留。

## 用户 Cube LUT

独立版右侧“胶卷风格”区域支持导入标准 `.cube` LUT：

- 支持 1D 和 3D Cube LUT；
- 导入时验证尺寸、数据行数和 Domain；
- 3D LUT 使用三线性插值；
- LUT 文件复制到同级 `lut` 文件夹；
- 使用“胶卷强度”控制混合比例；
- LUT 缺失时项目仍可打开，不会损坏项目数据。

## 整卷项目与输出

- 多个胶卷项目和跨会话恢复；
- 图片顺序、当前图片和项目级元数据；
- 每张图片独立保存转正、RAW、裁切、旋转、拉直、翻转、透视和输出参数；
- 缩略图、编辑代理和完整分辨率输出三级读取；
- 可取消的后台输出队列；
- 16 位 TIFF、8 位 TIFF、PNG、JPEG；
- ICC、尺寸调整、最终锐化、命名模板和重名策略；
- 接触印样和 `.psszproj` 项目归档。

## 风格与手动校正

- 扫描仪风格与胶卷风格独立选择；
- 胶片基底自动分析和原图吸管；
- 中性灰吸管修改 RGB 输出增益；
- 曝光、对比度、中间调、饱和度、色温、色调、RGB 增益、黑白点、阴影和高光；
- 每张照片独立撤销与重做；
- 裁切、旋转、自动范围、拉直、翻转和四角透视均为非破坏处理。

## 相机 RAW

独立版可直接加入常见 RAW：

```text
CR2 / CR3 / NEF / NRW / ARW / RAF / RW2 / ORF / PEF / SRW / DNG
```

完整解码采用 16 位、线性 Gamma、关闭自动提亮和 ProPhoto RGB。具体相机及压缩格式支持范围取决于发行包内的 rawpy / LibRaw。

## 开发检查

```bash
node scripts/validate.mjs
node --test tests/*.test.js
PYTHONPATH=standalone python -m unittest discover -s standalone/tests -v
bash scripts/build-release.sh
```

GitHub Actions 还会验证：

- Linux 虚拟显示器中的真实 Tk 窗口；
- macOS Apple Silicon 打包后窗口；
- Windows x64 打包后窗口；
- macOS DMG 结构；
- Windows 安装器静默安装后的目录和真实窗口；
- RAW、拖放、项目迁移、Cube LUT、Photoshop 和 Lightroom 功能。

## 第三方组件

- rawpy：LibRaw 的 Python 封装，用于相机 RAW 解码；
- LibRaw：随 rawpy 平台包提供的 RAW 解码运行库；
- Compact ICC Profiles：内置 `ProPhoto-v2-micro.icc`，按 CC0 发布。

## 许可证

MIT。Adobe、Photoshop 和 Lightroom 是 Adobe 的商标；本项目与 Adobe 无隶属或背书关系。
