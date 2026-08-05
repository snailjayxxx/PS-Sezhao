# PS-Sezhao v0.6.0

本版本加入首批扫描仪风格与热门胶卷风格，并把两者设计为两个完全独立的选项。用户可以先选择扫描观感，再选择胶卷色彩，并分别调整强度。

## 扫描仪风格

首批内置 6 种扫描观感：

- 中性实验室 · 干净扫描
- Hasselblad Flextight X5 · 高端扫描风格参考
- Noritsu HS-1800 · 日系冲扫风格参考
- Fujifilm Frontier SP-3000 · 柔和风格参考
- Fujifilm Frontier SP-3000 · 浓郁风格参考
- Archive Flatbed · 档案平板扫描

扫描仪风格主要影响基础反差、饱和度、通道关系和整体冷暖倾向。

## 胶卷风格

首批内置 16 种胶卷选项：

- 无胶卷风格 · 中性转正
- Kodak Portra 160 · 细腻低饱和
- Kodak Portra 400 · 柔和人像
- Kodak Portra 800 · 暖调高感
- Kodak Gold 200 · 暖色复古
- Kodak Ektar 100 · 高饱和风光
- Kodak Ultramax 400 · 通用日常
- Fujifilm Pro 400H · 清淡粉绿
- Fujifilm Superia X-TRA 400 · 清爽日常
- Fujifilm C200 · 轻复古日常
- CineStill 50D · 日光电影感
- CineStill 800T · 钨丝霓虹
- Kodak Vision3 250D · 电影日光
- Kodak Vision3 500T · 电影夜景
- Ilford HP5 Plus 400 · 经典黑白
- Kodak Tri-X 400 · 纪实黑白

胶卷风格主要影响色彩矩阵、反差、饱和度、通道伽马和风格冷暖。

## 两套风格独立组合

扫描仪风格与胶卷风格不会互相替代，可以自由组合，例如：

- Hasselblad Flextight X5 + Kodak Portra 400
- Noritsu HS-1800 + Kodak Gold 200
- Frontier SP-3000 柔和 + Fujifilm Pro 400H
- Archive Flatbed + 无胶卷风格

扫描仪强度和胶卷强度均可在 0%～200% 范围调整。设为 0% 时，可以单独关闭其中一套风格。

## Photoshop、独立版与 Lightroom

- Photoshop 面板新增独立的扫描仪风格和胶卷风格选择器。
- 独立版右侧参数面板新增同样的两套独立选择器。
- 每张图片分别保存扫描仪风格、胶卷风格和强度。
- 多图参数同步会同时同步两套风格。
- Lightroom 高精度 16 位流程复用独立版窗口，因此支持同样的风格组合。
- 旧版 `Portra`、`Gold`、`Fuji` 和 `ECN-2` 参数会自动迁移到对应的新命名。

## 名称和色彩说明

本版本使用摄影用户熟悉的产品和扫描设备名称，方便快速理解预期观感。所有效果均为 PS-Sezhao 自行设计的非官方风格参考，并非相关厂商提供或认证的 ICC、DCP、扫描配置或官方 LUT。

## 发行文件

- `PS-Sezhao-Photoshop-v0.6.0.ccx`
- `PS-Sezhao-Photoshop-Developer-v0.6.0.zip`
- `PS-Sezhao-LightroomClassic-macOS-arm64-v0.6.0.zip`
- `PS-Sezhao-LightroomClassic-Windows-x64-v0.6.0.zip`
- `PS-Sezhao-Standalone-macOS-arm64-v0.6.0.zip`
- `PS-Sezhao-Standalone-Windows-x64-v0.6.0.zip`
