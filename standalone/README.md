# 独立桌面版与共用处理器

该目录包含不依赖 Adobe 的 GUI 程序，同时也是 Lightroom Classic 高精度模式调用的本地图像引擎。

## v0.5.1 输入格式

常规图像：

```text
TIFF / JPEG / PNG / BMP / WebP
```

相机 RAW：

```text
CR2 / CR3 / NEF / NRW / ARW / RAF / RW2 / ORF / PEF / SRW / DNG 等
```

RAW 通过 rawpy / LibRaw 解码。完整处理固定使用16位、线性Gamma、ProPhoto RGB，并关闭自动提亮。RAW面板可选择白平衡、高光方式、去马赛克算法和预览策略。

## 开发运行

```bash
python -m pip install -r requirements.txt
PYTHONPATH=. python main.py
```

确认 RAW 运行时：

```bash
PYTHONPATH=. python -c "import rawpy; print(rawpy.__version__, rawpy.libraw_version)"
```

## 无界面任务

```bash
PYTHONPATH=. python main.py --batch-job /path/to/job.json
```

任务格式：

```json
{
  "items": [
    {
      "input": "/photos/input.nef",
      "output": "/photos/output.tif",
      "bit_depth": 16,
      "raw_decode": {
        "wb_mode": "camera",
        "highlight_mode": "blend",
        "demosaic": "ahd",
        "use_embedded_preview": true,
        "half_size_preview": true
      }
    }
  ],
  "result_manifest": "/tmp/outputs.txt",
  "settings": {
    "analysis": null,
    "controls": {"profile": "portra", "exposure": 0.2},
    "crop": [0, 0, 1, 1]
  }
}
```

每个 item 可以单独提供 `analysis`、`controls`、`crop` 和 `raw_decode`。批量任务逐张加载、处理和保存，避免同时解码整卷 RAW。

## RAW 预览

GUI 首先尝试读取 RAW 内嵌预览。内嵌预览不存在时，可使用半尺寸快速解码；后台完整解码完成后会自动替换预览。最终导出只使用完整解码数据。

## 色彩管理

rawpy 输出线性 ProPhoto RGB。保存时将结果编码到内置 ProPhoto RGB v2 配置文件并写入 TIFF ICC 标签。内置配置文件来自 Compact ICC Profiles，按 CC0 发布。

## 已知限制

- 支持范围取决于随包附带的 LibRaw；
- 某些新机型、特殊压缩、多帧或厂家私有 RAW 可能暂不支持；
- Tk 预览画布不执行完整 ICC 显示转换，预览使用近似显示 Gamma；
- 最终16位TIFF含ICC，适合在支持色彩管理的软件中继续精修。
