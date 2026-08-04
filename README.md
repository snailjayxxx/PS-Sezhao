# PS-Sezhao 胶片去色罩

PS-Sezhao 是面向彩色负片扫描和相机翻拍的本地图像处理项目。同一个仓库同时发布：

- **Photoshop 版**：UXP `.ccx` 插件，直接读取和写入图层。
- **Photoshop 开发者加载版**：完整插件目录，用 UXP Developer Tool 加载。
- **Lightroom Classic 版**：同时提供“原生直接转正”和“高精度 16 位 TIFF”两种模式。
- **独立桌面版**：不依赖 Adobe，适合只需要胶片转正或无法使用 Adobe 宿主的用户。

照片只在本机处理，不上传服务器。

## 当前版本

统一版本：**v0.4.0**

目标环境：

- Photoshop 2024（25.0）或更高版本
- Lightroom Classic 15.4 / 15.4.1 或更高版本
- macOS Apple Silicon
- Windows x64

## Release 文件怎么选

| 使用场景 | 下载文件 |
|---|---|
| Photoshop 正常安装 | `PS-Sezhao-Photoshop-v0.4.0.ccx` |
| Photoshop 开发/调试或 CCX 安装器不可用 | `PS-Sezhao-Photoshop-Developer-v0.4.0.zip` |
| Lightroom Classic on Apple Silicon Mac | `PS-Sezhao-LightroomClassic-macOS-arm64-v0.4.0.zip` |
| Lightroom Classic on Windows x64 | `PS-Sezhao-LightroomClassic-Windows-x64-v0.4.0.zip` |
| 不使用 Adobe 的 Mac 用户 | `PS-Sezhao-Standalone-macOS-arm64-v0.4.0.zip` |
| 不使用 Adobe 的 Windows 用户 | `PS-Sezhao-Standalone-Windows-x64-v0.4.0.zip` |

## Lightroom Classic：两种转正模式

### 1. 原生直接转正（默认）

菜单：

```text
图库 → 增效工具额外功能
→ PS-Sezhao：原生直接转正所选照片（默认）
```

该模式不会生成新的 TIFF，而是把非破坏性参数直接写入 Lightroom 当前照片：

- 反相点曲线
- 红、绿、蓝通道曲线
- 曝光、对比度、高光、阴影、白色和黑色
- 色温、色调、自然饱和度和饱和度
- 通用 C-41、Portra、Gold、Fujifilm、ECN-2 起始风格
- 所选照片批量应用

默认会在每张照片上创建：

```text
PS-Sezhao 原生转正前 YYYY-MM-DD HH:MM:SS
```

恢复方法：

```text
图库 → 增效工具额外功能
→ PS-Sezhao：恢复原生转正前状态
```

原文件不会改写。应用后可直接进入“修改照片”模块继续使用 Lightroom 的全部滑块、曲线、HSL 和局部工具。

### 2. 高精度 16 位 TIFF

菜单：

```text
图库 → 增效工具额外功能
→ PS-Sezhao：高精度 16 位 TIFF
```

该模式保留原有逐像素算法：

1. Lightroom 渲染临时 16 位 ProPhoto RGB TIFF；
2. PS-Sezhao 独立窗口执行色罩分析和光密度转正；
3. 输出新的 16 位 TIFF；
4. 自动导回 Lightroom 目录。

适合严重偏色、需要胶片基底吸管、要求与 Photoshop/独立版逐像素算法一致的照片。

## 两种 Lightroom 模式如何选择

| 需求 | 推荐模式 |
|---|---|
| 希望直接修改 Lightroom 当前照片 | 原生直接转正 |
| 不想生成新文件 | 原生直接转正 |
| 需要批量快速套用整卷 | 原生直接转正 |
| 希望继续自由使用 Lightroom 修改模块 | 原生直接转正 |
| 需要点击胶片基底吸管和逐像素去色罩 | 高精度 16 位 TIFF |
| 严重偏色或要求最高一致性 | 高精度 16 位 TIFF |

原生模式使用 Lightroom 的公开 Develop Settings 接口和曲线参数，结果可以继续编辑，但不保证与逐像素光密度算法完全一致。

## Photoshop 2024 兼容性

v0.3.1 起将宿主最低版本降到 `25.0.0`，覆盖 Photoshop 2024 系列。插件避免使用只在 Photoshop 25.10 之后才可用的模态超时选项。

## 独立版输入限制

v0.4.0 直接支持 TIFF、JPEG、PNG、BMP 和 WebP。相机 RAW 建议先导出为 16 位 TIFF。

## 开发检查

```bash
node scripts/validate.mjs
node --test tests/*.test.js
PYTHONPATH=standalone python -m unittest discover -s standalone/tests -v
bash scripts/build-release.sh
```

## 许可证

MIT。Adobe、Photoshop 和 Lightroom 是 Adobe 的商标；本项目与 Adobe 无隶属或背书关系。
