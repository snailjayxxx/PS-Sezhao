"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const main = fs.readFileSync(path.join(root, "standalone/main.py"), "utf8");
const rawIo = fs.readFileSync(path.join(root, "standalone/ps_sezhao/raw_io.py"), "utf8");
const rawPatch = fs.readFileSync(path.join(root, "standalone/ps_sezhao/app_v051_raw_patch.py"), "utf8");
const jobs = fs.readFileSync(path.join(root, "standalone/ps_sezhao/jobs.py"), "utf8");
const workspace = fs.readFileSync(path.join(root, "standalone/ps_sezhao/workspace.py"), "utf8");
const requirements = fs.readFileSync(path.join(root, "standalone/requirements.txt"), "utf8");
const workflow = fs.readFileSync(path.join(root, ".github/workflows/release.yml"), "utf8");

test("standalone launcher enables v0.5.1 RAW integration", function () {
  assert.match(main, /from ps_sezhao\.app_v051_raw_patch import apply_raw_patch/);
  assert.match(main, /apply_raw_patch\(app_module\.SezhaoApp\)/);
});

test("RAW decoder uses deterministic 16-bit linear ProPhoto settings", function () {
  assert.match(rawIo, /output_bps": 16/);
  assert.match(rawIo, /gamma": \(1\.0, 1\.0\)/);
  assert.match(rawIo, /no_auto_bright": True/);
  assert.match(rawIo, /ColorSpace\.ProPhoto/);
  assert.match(rawIo, /extract_thumb\(\)/);
  assert.match(rawIo, /prepare_save_output/);
});

test("RAW interface exposes white balance, preview and re-decode controls", function () {
  assert.match(rawPatch, /相机拍摄白平衡/);
  assert.match(rawPatch, /日光白平衡/);
  assert.match(rawPatch, /自动白平衡/);
  assert.match(rawPatch, /自定义通道倍率/);
  assert.match(rawPatch, /优先读取 RAW 内嵌预览/);
  assert.match(rawPatch, /重新解码当前 RAW/);
  assert.match(rawPatch, /threading\.Thread/);
});

test("common RAW formats participate in file and folder import", function () {
  [".cr2", ".cr3", ".nef", ".arw", ".raf", ".rw2", ".orf", ".dng"].forEach(function (extension) {
    assert.match(rawIo, new RegExp(`"\\${extension}"`));
  });
  assert.match(workspace, /RAW_EXTENSIONS/);
});

test("batch processing keeps RAW decode and output color management", function () {
  assert.match(jobs, /RawDecodeSettings/);
  assert.match(jobs, /load_image\(input_path, raw_settings=raw_settings\)/);
  assert.match(jobs, /prepare_save_output\(result, metadata\)/);
});

test("release packages include rawpy and LibRaw on both platforms", function () {
  assert.match(requirements, /rawpy>=0\.27,<0\.28/);
  assert.equal((workflow.match(/--collect-all rawpy/g) || []).length, 2);
  assert.match(workflow, /Verify RAW runtime/);
});
