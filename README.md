# PS-Sezhao 胶片去色罩

PS-Sezhao 是面向彩色负片扫描和相机翻拍的本地图像处理项目。同一个仓库同时发布：

- **Photoshop 版**：UXP `.ccx` 插件，直接读取和写入图层。
- **Lightroom Classic 版**：Lua `.lrplugin` 插件，渲染所选照片、打开调色窗口、生成 16 位 TIFF 并自动导回目录。
- **独立桌面版**：不依赖 Adobe，适合未安装 Photoshop/Lightroom、使用其他修图软件或只需要胶片转正的用户。

照片只在本机处理，不上传服务器。

## 当前版本

统一版本：**v0.3.0**

目标宿主：

- Photoshop 27.8 或更高版本
- Lightroom Classic 15.4 / 15.4.1 或更高版本
- macOS Apple Silicon
- Windows x64

## Release 文件怎么选

| 使用场景 | 下载文件 |
|---|---|
| Photoshop | `PS-Sezhao-Photoshop-v0.3.0.ccx` |
| Lightroom Classic on Apple Silicon Mac | `PS-Sezhao-LightroomClassic-macOS-arm64-v0.3.0.zip` |
| Lightroom Classic on Windows x64 | `PS-Sezhao-LightroomClassic-Windows-x64-v0.3.0.zip` |
| 不使用 Adobe 的 Mac 用户 | `PS-Sezhao-Standalone-macOS-arm64-v0.3.0.zip` |
| 不使用 Adobe 的 Windows 用户 | `PS-Sezhao-Standalone-Windows-x64-v0.3.0.zip` |

本项目不提供破解 Adobe 软件、绕过授权或适配修改版宿主的方法。没有 Adobe 正版环境的用户直接使用独立桌面版，核心转正与校色功能不受影响。

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

## 目录结构

```text
plugin/                                  Photoshop UXP 插件
lightroom-classic/PS-Sezhao.lrplugin/    Lightroom Classic Lua 插件
standalone/                              跨平台本地处理器与桌面界面
scripts/                                 打包脚本
.github/workflows/                        PS、LR、独立版统一发布流程
```

## Lightroom Classic 工作流

1. 在图库中选择一张或多张负片。
2. 打开 `图库 → 增效工具额外功能 → PS-Sezhao：转正所选负片`。
3. Lightroom Classic 将当前编辑后的照片渲染为临时 16 位 ProPhoto RGB TIFF。
4. PS-Sezhao 打开独立大预览窗口。
5. 通过吸管和滑块完成调色，点击“批量应用并完成”。
6. 成品写入每张原图所在目录的 `PS-Sezhao` 子文件夹，并自动导入 Lightroom Classic。

## 独立版输入限制

v0.3.0 直接支持 TIFF、JPEG、PNG、BMP 和 WebP。相机 RAW 建议先由相机厂商软件、Darktable、RawTherapee 或其他合法 RAW 工具导出为 16 位 TIFF。后续版本会评估直接 RAW 解码。

## 开发检查

```bash
node scripts/validate.mjs
node --test tests/*.test.js
PYTHONPATH=standalone python -m unittest discover -s standalone/tests -v
bash scripts/build-release.sh
```

## 许可证

MIT。Adobe、Photoshop 和 Lightroom 是 Adobe 的商标；本项目与 Adobe 无隶属或背书关系。
