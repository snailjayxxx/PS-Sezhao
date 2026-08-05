"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const main = fs.readFileSync(path.join(root, "standalone/main.py"), "utf8");
const patch = fs.readFileSync(path.join(root, "standalone/ps_sezhao/app_v052_source_crop_patch.py"), "utf8");
const sampler = fs.readFileSync(path.join(root, "plugin/runtime-sampler.js"), "utf8");

test("standalone launcher applies v0.5.2 after RAW integration", function () {
  const rawIndex = main.indexOf("apply_raw_patch(app_module.SezhaoApp)");
  const cropIndex = main.indexOf("apply_source_crop_patch(app_module.SezhaoApp)");
  assert.ok(rawIndex >= 0);
  assert.ok(cropIndex > rawIndex);
});

test("standalone base sampling never samples the processed display array", function () {
  assert.match(patch, /sample_median_rgb\(self\.preview_source/);
  assert.doesNotMatch(patch, /sample_median_rgb\(self\._display_full_array/);
  assert.doesNotMatch(patch, /sample_median_rgb\(self\.preview_result/);
});

test("Photoshop sampler reads pixels from the remembered source layer", function () {
  assert.match(sampler, /layerID:\s*source\.layer\.id/);
  assert.match(sampler, /state\.analysis \? storedSource\(\) : ensureActiveCandidate\(\)/);
});

test("crop editing and applied crop display are separate states", function () {
  assert.match(patch, /if self\.crop_editing or self\.preview_source is None or crop_is_full/);
  assert.match(patch, /shown = crop_array\(self\._display_full_array, self\.crop_norm\)/);
  assert.match(patch, /self\.crop_toggle_button\.configure\(text="完成裁切"\)/);
  assert.match(patch, /self\.crop_toggle_button\.configure\(text="裁切"\)/);
});
