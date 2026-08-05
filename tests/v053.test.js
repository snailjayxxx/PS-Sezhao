"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const runtime = fs.readFileSync(path.join(root, "plugin/runtime-v022.js"), "utf8");
const wideEngine = fs.readFileSync(path.join(root, "plugin/runtime-engine-v053.js"), "utf8");
const main = fs.readFileSync(path.join(root, "standalone/main.py"), "utf8");
const scrollPatch = fs.readFileSync(path.join(root, "standalone/ps_sezhao/app_v053_scroll_patch.py"), "utf8");
const pythonEnginePatch = fs.readFileSync(path.join(root, "standalone/ps_sezhao/engine_v053_patch.py"), "utf8");

test("Photoshop base adjustment expands to full 8-bit equivalent range", function () {
  const engine = require(path.join(root, "plugin/engine.js"));
  require(path.join(root, "plugin/runtime-engine-v053.js")).apply(engine);
  assert.deepEqual(engine.safeControls({ baseAdjust: [-2, 0.5, 2] }).baseAdjust, [-1, 0.5, 1]);
  assert.match(runtime, /runtime-engine-v053\.js/);
  assert.match(runtime, /range\.min = "-255"/);
  assert.match(runtime, /range\.max = "255"/);
  assert.match(wideEngine, /baseAdjust: baseAdjust\.map/);
  assert.match(wideEngine, /-1, 1/);
});

test("standalone and Lightroom high precision share expanded base range", function () {
  assert.match(main, /apply_engine_patch\(\)/);
  assert.match(main, /apply_scroll_patch\(app_module\.SezhaoApp\)/);
  assert.match(scrollPatch, /BASE_MIN_UNITS = -255/);
  assert.match(scrollPatch, /BASE_MAX_UNITS = 255/);
  assert.match(scrollPatch, /widget\.configure\(from_=BASE_MIN_UNITS, to=BASE_MAX_UNITS/);
  assert.match(pythonEnginePatch, /np\.clip\(value, -1\.0, 1\.0\)/);
});

test("right controls and left photo list accept cross-platform wheel scrolling", function () {
  assert.match(scrollPatch, /<MouseWheel>/);
  assert.match(scrollPatch, /<Button-4>/);
  assert.match(scrollPatch, /<Button-5>/);
  assert.match(scrollPatch, /self\.controls\.master\.yview_scroll/);
  assert.match(scrollPatch, /self\.file_tree\.yview_scroll/);
  assert.match(scrollPatch, /return "break"/);
});
