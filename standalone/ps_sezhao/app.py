from __future__ import annotations

import argparse
import json
import threading
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

from . import __version__
from .engine import Analysis, Controls, PROFILES, analyze_image, neutral_gains, process_image, sample_median_rgb
from .io_utils import load_image, make_preview, save_image
from .jobs import run_job


class SezhaoApp:
    def __init__(self, root: tk.Tk, *, lr_job: str | None = None, initial_files: list[str] | None = None) -> None:
        self.root = root
        self.root.title(f"PS-Sezhao {__version__} · 胶片去色罩")
        self.root.geometry("1280x880")
        self.root.minsize(960, 680)

        self.lr_job_path = Path(lr_job) if lr_job else None
        self.lr_job_data: dict[str, Any] | None = None
        self.files: list[Path] = []
        self.current_path: Path | None = None
        self.full_image: np.ndarray | None = None
        self.preview_source: np.ndarray | None = None
        self.preview_result: np.ndarray | None = None
        self.metadata: dict[str, Any] = {}
        self.analysis: Analysis | None = None
        self.photo_image: ImageTk.PhotoImage | None = None
        self.canvas_geometry = (0.0, 0.0, 1.0, 1.0)
        self.pick_mode: str | None = None
        self.render_after: str | None = None
        self.render_generation = 0

        self._build_variables()
        self._build_ui()

        if self.lr_job_path:
            self._load_lr_job(self.lr_job_path)
        elif initial_files:
            self.open_paths([Path(path) for path in initial_files])

    def _build_variables(self) -> None:
        self.profile = tk.StringVar(value="generic")
        self.sample_size = tk.IntVar(value=11)
        self.status = tk.StringVar(value="打开一张扫描或翻拍负片开始处理。")
        self.auto_preview = tk.BooleanVar(value=True)
        self.vars: dict[str, tk.DoubleVar] = {
            "style_strength": tk.DoubleVar(value=1.0),
            "exposure": tk.DoubleVar(value=0.0),
            "contrast": tk.DoubleVar(value=1.0),
            "gamma": tk.DoubleVar(value=1.0),
            "saturation": tk.DoubleVar(value=1.0),
            "temperature": tk.DoubleVar(value=0.0),
            "tint": tk.DoubleVar(value=0.0),
            "red_gain": tk.DoubleVar(value=1.0),
            "green_gain": tk.DoubleVar(value=1.0),
            "blue_gain": tk.DoubleVar(value=1.0),
            "black_point": tk.DoubleVar(value=0.0),
            "white_point": tk.DoubleVar(value=0.0),
            "shadows": tk.DoubleVar(value=0.0),
            "highlights": tk.DoubleVar(value=0.0),
        }

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self.root, padding=(10, 8))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(8, weight=1)
        ttk.Button(toolbar, text="打开图像", command=self.open_dialog).grid(row=0, column=0, padx=3)
        ttk.Button(toolbar, text="自动分析边框", command=self.auto_analyze).grid(row=0, column=1, padx=3)
        ttk.Button(toolbar, text="吸管：胶片基底", command=lambda: self.start_pick("base")).grid(row=0, column=2, padx=3)
        ttk.Button(toolbar, text="吸管：中性色", command=lambda: self.start_pick("neutral")).grid(row=0, column=3, padx=3)
        ttk.Label(toolbar, text="取样").grid(row=0, column=4, padx=(12, 3))
        ttk.Combobox(toolbar, textvariable=self.sample_size, values=(1, 3, 5, 11, 21), width=5, state="readonly").grid(row=0, column=5)
        ttk.Checkbutton(toolbar, text="自动预览", variable=self.auto_preview).grid(row=0, column=6, padx=10)
        ttk.Button(toolbar, text="恢复默认", command=self.reset_controls).grid(row=0, column=7, padx=3)
        ttk.Label(toolbar, textvariable=self.status, anchor="e").grid(row=0, column=8, sticky="ew", padx=(12, 3))

        body = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        body.grid(row=1, column=0, sticky="nsew")
        preview_frame = ttk.Frame(body, padding=8)
        controls_outer = ttk.Frame(body, padding=(4, 8, 8, 8))
        body.add(preview_frame, weight=4)
        body.add(controls_outer, weight=1)

        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(preview_frame, bg="#191919", highlightthickness=0, cursor="crosshair")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Configure>", lambda _event: self.draw_preview())

        controls_canvas = tk.Canvas(controls_outer, width=315, highlightthickness=0)
        scrollbar = ttk.Scrollbar(controls_outer, orient="vertical", command=controls_canvas.yview)
        self.controls = ttk.Frame(controls_canvas)
        self.controls.bind("<Configure>", lambda _event: controls_canvas.configure(scrollregion=controls_canvas.bbox("all")))
        controls_canvas.create_window((0, 0), window=self.controls, anchor="nw", width=300)
        controls_canvas.configure(yscrollcommand=scrollbar.set)
        controls_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        row = 0
        ttk.Label(self.controls, text="胶片起始配置", font=("TkDefaultFont", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(2, 4)); row += 1
        profile_box = ttk.Combobox(self.controls, textvariable=self.profile, state="readonly", width=27)
        profile_box["values"] = tuple(PROFILES.keys())
        profile_box.grid(row=row, column=0, sticky="ew", pady=(0, 8)); row += 1
        profile_box.bind("<<ComboboxSelected>>", lambda _event: self.schedule_render())

        specs = [
            ("style_strength", "风格强度", 0.0, 2.0, 0.01),
            ("exposure", "曝光 EV", -3.0, 3.0, 0.02),
            ("contrast", "对比度", 0.5, 2.0, 0.01),
            ("gamma", "中间调", 0.5, 2.0, 0.01),
            ("saturation", "饱和度", 0.0, 2.5, 0.01),
            ("temperature", "色温", -3.0, 3.0, 0.02),
            ("tint", "色调（绿↔洋红）", -2.0, 2.0, 0.02),
            ("red_gain", "红色增益", 0.25, 3.0, 0.01),
            ("green_gain", "绿色增益", 0.25, 3.0, 0.01),
            ("blue_gain", "蓝色增益", 0.25, 3.0, 0.01),
            ("black_point", "黑点", -1.0, 1.0, 0.01),
            ("white_point", "白点", -1.0, 1.0, 0.01),
            ("shadows", "阴影", -1.0, 1.0, 0.01),
            ("highlights", "高光", -1.0, 1.0, 0.01),
        ]
        for key, label, start, end, resolution in specs:
            row = self._add_scale(row, key, label, start, end, resolution)

        action_frame = ttk.Frame(self.controls)
        action_frame.grid(row=row, column=0, sticky="ew", pady=(12, 4)); row += 1
        action_frame.columnconfigure((0, 1), weight=1)
        ttk.Button(action_frame, text="保存当前图像", command=self.save_current).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(action_frame, text="批量应用并完成", command=self.apply_all).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        ttk.Label(self.controls, text="提示：吸管启动后，直接点击左侧大图。", foreground="#666").grid(row=row, column=0, sticky="w", pady=(6, 12))

    def _add_scale(self, row: int, key: str, label: str, start: float, end: float, resolution: float) -> int:
        frame = ttk.Frame(self.controls)
        frame.grid(row=row, column=0, sticky="ew", pady=2)
        frame.columnconfigure(0, weight=1)
        value_label = ttk.Label(frame, text="0", width=7, anchor="e")
        ttk.Label(frame, text=label).grid(row=0, column=0, sticky="w")
        value_label.grid(row=0, column=1, sticky="e")
        scale = tk.Scale(
            frame,
            from_=start,
            to=end,
            resolution=resolution,
            orient=tk.HORIZONTAL,
            variable=self.vars[key],
            showvalue=False,
            highlightthickness=0,
            command=lambda _value, k=key, target=value_label: self.on_scale(k, target),
        )
        scale.grid(row=1, column=0, columnspan=2, sticky="ew")
        value_label.configure(text=f"{self.vars[key].get():.2f}")
        return row + 1

    def on_scale(self, key: str, label: ttk.Label) -> None:
        label.configure(text=f"{self.vars[key].get():.2f}")
        self.schedule_render()

    def controls_value(self) -> Controls:
        return Controls(profile=self.profile.get(), **{key: variable.get() for key, variable in self.vars.items()}).sanitized()

    def reset_controls(self) -> None:
        defaults = Controls()
        self.profile.set(defaults.profile)
        for key, variable in self.vars.items():
            variable.set(getattr(defaults, key))
        self.schedule_render(0)

    def open_dialog(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择扫描或翻拍负片",
            filetypes=[("图像", "*.tif *.tiff *.jpg *.jpeg *.png *.bmp *.webp"), ("全部文件", "*.*")],
        )
        if paths:
            self.open_paths([Path(path) for path in paths])

    def open_paths(self, paths: list[Path]) -> None:
        self.files = paths
        self.load_path(paths[0])

    def load_path(self, path: Path) -> None:
        try:
            self.status.set(f"正在读取 {path.name}…")
            self.root.update_idletasks()
            image, metadata = load_image(path)
            self.current_path = path
            self.full_image = image
            self.preview_source = make_preview(image, 1800)
            self.preview_result = None
            self.metadata = metadata
            self.analysis = None
            self.auto_analyze()
        except Exception as error:
            messagebox.showerror("无法打开图像", str(error))
            self.status.set("打开失败。")

    def auto_analyze(self) -> None:
        if self.preview_source is None:
            return
        try:
            self.status.set("正在分析胶片边框…")
            self.analysis = analyze_image(self.preview_source, border_fraction=0.07)
            self.status.set(f"基底分析完成，可信度 {self.analysis.confidence * 100:.0f}%")
            self.schedule_render(0)
        except Exception as error:
            self.analysis = None
            self.draw_preview(self.preview_source)
            messagebox.showwarning("自动分析失败", f"{error}\n\n请点击“吸管：胶片基底”，再点击未曝光的橙色边框。")
            self.status.set("请使用胶片基底吸管。")

    def start_pick(self, mode: str) -> None:
        if self.preview_source is None:
            messagebox.showinfo("尚未打开图像", "请先打开一张负片图像。")
            return
        if mode == "neutral" and self.analysis is None:
            messagebox.showinfo("尚未转正", "请先分析或吸取胶片基底。")
            return
        self.pick_mode = mode
        self.status.set("请在左侧大图点击未曝光橙色边框。" if mode == "base" else "请在左侧大图点击白色、灰色或应为中性的区域。")

    def on_canvas_click(self, event: tk.Event) -> None:
        if not self.pick_mode or self.preview_source is None:
            return
        offset_x, offset_y, scale, _ = self.canvas_geometry
        x = round((event.x - offset_x) / scale)
        y = round((event.y - offset_y) / scale)
        height, width, _ = self.preview_source.shape
        if x < 0 or y < 0 or x >= width or y >= height:
            return
        try:
            if self.pick_mode == "base":
                base = sample_median_rgb(self.preview_source, x, y, self.sample_size.get())
                self.analysis = analyze_image(self.preview_source, base=base, method="eyedropper")
                self.status.set("胶片基底已更新，正在刷新预览。")
            else:
                assert self.analysis is not None
                gains = neutral_gains(self.preview_source, self.analysis, self.controls_value(), x, y, self.sample_size.get())
                self.vars["red_gain"].set(gains[0])
                self.vars["green_gain"].set(gains[1])
                self.vars["blue_gain"].set(gains[2])
                self.status.set("中性色校正完成，正在刷新预览。")
            self.pick_mode = None
            self.schedule_render(0)
        except Exception as error:
            messagebox.showerror("取样失败", str(error))

    def schedule_render(self, delay: int = 120) -> None:
        if not self.auto_preview.get() or self.analysis is None or self.preview_source is None:
            return
        if self.render_after:
            self.root.after_cancel(self.render_after)
        self.render_after = self.root.after(delay, self.render_preview)

    def render_preview(self) -> None:
        self.render_after = None
        if self.analysis is None or self.preview_source is None:
            return
        self.render_generation += 1
        generation = self.render_generation
        controls = self.controls_value()
        analysis = self.analysis
        source = self.preview_source.copy()
        self.status.set("正在更新大图预览…")

        def worker() -> None:
            try:
                result = process_image(source, analysis, controls)
                self.root.after(0, lambda: self._accept_render(generation, result))
            except Exception as error:
                trace = traceback.format_exc()
                self.root.after(0, lambda: self._render_error(error, trace))

        threading.Thread(target=worker, daemon=True).start()

    def _accept_render(self, generation: int, result: np.ndarray) -> None:
        if generation != self.render_generation:
            return
        self.preview_result = result
        self.draw_preview(result)
        self.status.set("预览已更新；拖动滑块或使用吸管继续调整。")

    def _render_error(self, error: Exception, trace: str) -> None:
        print(trace)
        self.status.set(f"预览失败：{error}")

    def draw_preview(self, image: np.ndarray | None = None) -> None:
        if image is None:
            image = self.preview_result if self.preview_result is not None else self.preview_source
        if image is None:
            self.canvas.delete("all")
            return
        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())
        height, width, _ = image.shape
        scale = min(canvas_width / width, canvas_height / height)
        target_width = max(1, round(width * scale))
        target_height = max(1, round(height * scale))
        data8 = np.round(np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)
        pil_image = Image.fromarray(data8, mode="RGB")
        if target_width != width or target_height != height:
            pil_image = pil_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        self.photo_image = ImageTk.PhotoImage(pil_image)
        offset_x = (canvas_width - target_width) / 2.0
        offset_y = (canvas_height - target_height) / 2.0
        self.canvas.delete("all")
        self.canvas.create_image(offset_x, offset_y, anchor="nw", image=self.photo_image)
        self.canvas_geometry = (offset_x, offset_y, scale, 1.0)

    def save_current(self) -> None:
        if self.full_image is None or self.analysis is None or self.current_path is None:
            return
        default_name = self.current_path.stem + "_PS-Sezhao.tif"
        target = filedialog.asksaveasfilename(
            title="保存正片",
            initialfile=default_name,
            defaultextension=".tif",
            filetypes=[("16 位 TIFF", "*.tif"), ("JPEG", "*.jpg"), ("PNG", "*.png")],
        )
        if not target:
            return
        self._process_and_save(self.full_image, Path(target), self.analysis)

    def _process_and_save(self, image: np.ndarray, target: Path, analysis: Analysis) -> None:
        controls = self.controls_value()
        self.status.set(f"正在生成 {target.name}…")

        def worker() -> None:
            try:
                result = process_image(image, analysis, controls)
                save_image(target, result, bit_depth=16, icc_profile=self.metadata.get("icc_profile"))
                self.root.after(0, lambda: self.status.set(f"已保存：{target}"))
            except Exception as error:
                self.root.after(0, lambda: messagebox.showerror("保存失败", str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def apply_all(self) -> None:
        if self.analysis is None:
            messagebox.showinfo("尚未分析", "请先分析或吸取胶片基底。")
            return
        if self.lr_job_data is not None and self.lr_job_path is not None:
            self._run_lr_job()
            return
        if not self.files:
            return
        destination = filedialog.askdirectory(title="选择批量输出文件夹")
        if not destination:
            return
        controls = self.controls_value()
        analysis = self.analysis
        files = list(self.files)
        output_dir = Path(destination)
        self.status.set(f"正在批量处理 {len(files)} 张照片…")

        def worker() -> None:
            try:
                for index, source in enumerate(files, start=1):
                    image, metadata = load_image(source)
                    result = process_image(image, analysis, controls)
                    target = output_dir / f"{source.stem}_PS-Sezhao.tif"
                    save_image(target, result, bit_depth=16, icc_profile=metadata.get("icc_profile"))
                    self.root.after(0, lambda i=index, name=source.name: self.status.set(f"正在处理 {i}/{len(files)}：{name}"))
                self.root.after(0, lambda: self.status.set(f"批量处理完成：{output_dir}"))
            except Exception as error:
                self.root.after(0, lambda: messagebox.showerror("批量处理失败", str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def _load_lr_job(self, job_path: Path) -> None:
        try:
            data = json.loads(job_path.read_text(encoding="utf-8"))
            self.lr_job_data = data
            items = data.get("items") or []
            if not items:
                raise ValueError("Lightroom 任务中没有照片。")
            self.files = [Path(item["input"]) for item in items]
            self.load_path(self.files[0])
            self.status.set(f"Lightroom 已发送 {len(items)} 张照片。调整后点击“批量应用并完成”。")
        except Exception as error:
            messagebox.showerror("无法读取 Lightroom 任务", str(error))

    def _run_lr_job(self) -> None:
        assert self.lr_job_data is not None and self.lr_job_path is not None and self.analysis is not None
        self.lr_job_data.setdefault("settings", {})["analysis"] = self.analysis.to_dict()
        self.lr_job_data["settings"]["controls"] = self.controls_value().to_dict()
        self.lr_job_path.write_text(json.dumps(self.lr_job_data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status.set("正在生成 Lightroom 正片文件…")

        def progress(done: int, total: int, name: str) -> None:
            self.root.after(0, lambda: self.status.set(f"Lightroom 批量处理 {done}/{total}：{name}"))

        def worker() -> None:
            try:
                run_job(self.lr_job_path, progress)
                self.root.after(0, self._finish_lr_job)
            except Exception as error:
                self.root.after(0, lambda: messagebox.showerror("Lightroom 处理失败", str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_lr_job(self) -> None:
        self.status.set("Lightroom 正片已生成，正在返回目录。")
        self.root.after(400, self.root.destroy)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PS-Sezhao 胶片去色罩")
    parser.add_argument("files", nargs="*", help="启动时打开的图像")
    parser.add_argument("--lr-job", help="由 Lightroom Classic 创建的任务 JSON")
    parser.add_argument("--batch-job", help="无界面执行任务 JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.batch_job:
        run_job(args.batch_job)
        return 0
    root = tk.Tk()
    SezhaoApp(root, lr_job=args.lr_job, initial_files=args.files)
    root.mainloop()
    return 0
