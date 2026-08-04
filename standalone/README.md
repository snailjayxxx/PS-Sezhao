# 独立桌面版与共用处理器

该目录包含不依赖 Adobe 的 GUI 程序，同时也是 Lightroom Classic 插件调用的本地图像引擎。

## 开发运行

```bash
python -m pip install -r requirements.txt
PYTHONPATH=. python main.py
```

## 无界面任务

```bash
PYTHONPATH=. python main.py --batch-job /path/to/job.json
```

任务格式：

```json
{
  "items": [
    {"input": "/tmp/input.tif", "output": "/photos/output.tif", "bit_depth": 16}
  ],
  "result_manifest": "/tmp/outputs.txt",
  "settings": {
    "analysis": null,
    "controls": {"profile": "portra", "exposure": 0.2}
  }
}
```
