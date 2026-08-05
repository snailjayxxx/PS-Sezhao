"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const runtime = fs.readFileSync(path.join(root, "plugin/runtime-v022.js"), "utf8");
const history = fs.readFileSync(path.join(root, "plugin/runtime-history-v054.js"), "utf8");
const standaloneMain = fs.readFileSync(path.join(root, "standalone/main.py"), "utf8");
const standalonePatch = fs.readFileSync(path.join(root, "standalone/ps_sezhao/app_v054_history_direct_patch.py"), "utf8");
const historyState = fs.readFileSync(path.join(root, "standalone/ps_sezhao/history_state.py"), "utf8");

test("Photoshop uses direct final base RGB values instead of visible offsets", function () {
  assert.match(runtime, /configureDirectBaseRanges/);
  assert.match(runtime, /range\.min = "0"/);
  assert.match(runtime, /range\.max = "255"/);
  assert.match(history, /directBaseValue\(index\) - Number\(detected\[index\]/);
  assert.match(history, /胶片基底（直接 R\/G\/B）/);
  assert.match(history, /最终使用的 8 位 R\/G\/B 数值/);
});

test("Photoshop panel exposes undo redo and keyboard shortcuts", function () {
  assert.match(history, /id = "undoEdit"/);
  assert.match(history, /id = "redoEdit"/);
  assert.match(history, /function undo\(/);
  assert.match(history, /function redo\(/);
  assert.match(history, /event\.ctrlKey \|\| event\.metaKey/);
  assert.match(history, /event\.shiftKey/);
  assert.match(runtime, /history\.record\("control"/);
});

test("neutral picker is documented as editable RGB output gains", function () {
  assert.match(history, /中性灰吸管修改的是下方红、绿、蓝输出增益/);
  assert.match(history, /resetNeutralGains/);
  assert.match(history, /\["redGain", "greenGain", "blueGain"\]/);
  assert.match(standalonePatch, /中性灰校正（RGB 输出增益）/);
  assert.match(standalonePatch, /中性灰吸管只修改下面三个输出增益/);
  assert.match(standalonePatch, /reset_neutral_gains/);
});

test("standalone and Lightroom high precision share per-photo undo redo", function () {
  assert.match(standaloneMain, /apply_v054_patch\(app_module\.SezhaoApp\)/);
  assert.match(standalonePatch, /HistoryStack\(limit=60\)/);
  assert.match(standalonePatch, /Ctrl\/Cmd\+Z/);
  assert.match(standalonePatch, /def undo_edit/);
  assert.match(standalonePatch, /def redo_edit/);
  assert.match(historyState, /redo_items/);
});

test("standalone base controls display direct values and preserve detected base internally", function () {
  assert.match(standalonePatch, /BASE_DIRECT_MIN = 0/);
  assert.match(standalonePatch, /BASE_DIRECT_MAX = 384/);
  assert.match(standalonePatch, /direct - self\.detected_base\(\)/);
  assert.match(standalonePatch, /原图识别 R\/G\/B/);
  assert.match(standalonePatch, /最终使用/);
});
