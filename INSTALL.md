# PS-Sezhao v0.5.4 安装与使用说明

## Photoshop 2024（25.0）或更高版本

1. 下载 `PS-Sezhao-Photoshop-v0.5.4.ccx`。
2. 完全退出 Photoshop。
3. 双击 CCX，通过 Creative Cloud Desktop 安装。
4. 重新打开 Photoshop，从 `插件 → 胶片去色罩` 启动。
5. 确认顶部显示 `PS-SEZHAO · 0.5.4`。

开发者加载版文件为 `PS-Sezhao-Photoshop-Developer-v0.5.4.zip`。通过 UXP Developer Tool 选择其中的 `manifest.json` 并点击 `Load`。

## Lightroom Classic 15.4+

- Apple Silicon Mac：`PS-Sezhao-LightroomClassic-macOS-arm64-v0.5.4.zip`
- Windows x64：`PS-Sezhao-LightroomClassic-Windows-x64-v0.5.4.zip`

升级时完全退出 Lightroom Classic，移除旧的 `PS-Sezhao.lrplugin`，再添加新目录。不要把新文件直接覆盖到旧插件目录。

原生直接转正继续使用 Lightroom 自身历史记录和插件恢复快照。高精度 16 位 TIFF 会打开与独立版相同的 v0.5.4 多图窗口，支持撤销、重做、直接基底数值和中性灰增益编辑。

## 独立桌面版

### macOS Apple Silicon

1. 下载并解压 `PS-Sezhao-Standalone-macOS-arm64-v0.5.4.zip`。
2. 将 `PS-Sezhao.app` 移到“应用程序”。
3. 首次启动提示无法验证开发者时，在 Finder 中右键应用并选择“打开”。
4. 仍被阻止时进入 `系统设置 → 隐私与安全性`，找到 PS-Sezhao 后选择“仍要打开”。

### Windows x64

1. 下载并解压 `PS-Sezhao-Standalone-Windows-x64-v0.5.4.zip`。
2. 运行 `PS-Sezhao.exe`。
3. SmartScreen 出现时，确认文件来自本仓库 Release，再选择“更多信息 → 仍要运行”。

## 撤销和重做

工具栏提供：

```text
↶ 撤销
↷ 重做
```

快捷键：

```text
撤销：Ctrl/Cmd + Z
重做：Ctrl/Cmd + Y
重做：Ctrl/Cmd + Shift + Z
```

独立版按每张照片分别保留最多 60 项历史，可恢复调色、胶片基底、中性灰吸管、自动分析和裁切。切换照片不会混用历史。

## 直接修改胶片基底

右侧滚动到：

```text
胶片基底（直接数值） · v0.5.4
```

界面显示：

```text
原图识别 R/G/B：212 / 143 / 82
最终使用：212 / 143 / 82
```

现在填写的是最终使用值，不是识别值上的偏移量。可拖动滑块、直接输入数字或使用 `− / +`。点击“恢复为识别值”可回到自动分析或吸管结果。

Photoshop 版直接值范围为 0～255。独立版保留扩展上限用于极端素材，常规胶片通常使用 0～255。

## 中性灰吸管

中性灰吸管修改的是：

```text
R 输出增益
G 输出增益
B 输出增益
```

它不会重新修改胶片基底，也不会直接修改色温和色调。`1.000` 表示不额外校正。吸取后可在“中性灰校正（RGB 输出增益）”中继续手动输入或用 `− / +` 调整；“中性灰校正恢复 1.000”可取消该校正。

## 侧栏、裁切和 RAW

- 右侧参数栏和左侧图片列表都支持鼠标滚轮上下浏览；
- 中间预览区滚轮继续用于缩放；
- 裁切完成后只显示保留区域，再次点击“裁切”可编辑旧裁切框；
- 自动分析边框只分析当前裁切范围；
- 支持 CR2、CR3、NEF、ARW、RAF、RW2、ORF、PEF、SRW、DNG 等常见 RAW；
- 完整 RAW 解码使用 16 位、线性 Gamma、关闭自动提亮和 ProPhoto RGB。

## 关于第三方修改版 Adobe 软件

本项目不提供绕过 Adobe 授权、修改 Creative Cloud 或破解插件验证的方法。无法使用 Adobe 宿主时，可使用独立桌面版。
