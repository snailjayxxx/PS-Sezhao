"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const plugin = path.join(root, "plugin");
const html = fs.readFileSync(path.join(plugin, "index.html"), "utf8");
const css = fs.readFileSync(path.join(plugin, "styles.css"), "utf8");
const common = fs.readFileSync(path.join(plugin, "runtime-common.js"), "utf8");
const preview = fs.readFileSync(path.join(plugin, "runtime-preview.js"), "utf8");
const finalRuntime = fs.readFileSync(path.join(plugin, "runtime-final.js"), "utf8");
const entry = fs.readFileSync(path.join(plugin, "runtime-v021.js"), "utf8");
const engine = fs.readFileSync(path.join(plugin, "engine.js"), "utf8");

test("panel keeps a bounded scroll area and fixed action dock", function () {
  assert.match(html, /class="panel-scroll"/);
  assert.match(html, /class="action-dock"/);
  assert.match(css, /\.panel-scroll\s*\{[^}]*overflow-y:\s*auto/s);
  assert.match(css, /\.panel-shell\s*\{[^}]*height:\s*100%/s);
});

test("index loads the 0.2.1 modular runtime", function () {
  assert.match(html, /PS-SEZHAO · 0\.2\.1/);
  assert.match(html, /<script src="runtime-v021\.js"><\/script>/);
  assert.match(entry, /require\("\.\/runtime-common\.js"\)/);
  assert.match(entry, /require\("\.\/runtime-preview\.js"\)/);
  assert.match(entry, /require\("\.\/runtime-final\.js"\)/);
});

test("advanced color controls remain present", function () {
  ["temperature", "tint", "redGain", "greenGain", "blueGain", "baseAdjustR", "baseAdjustG", "baseAdjustB", "styleStrength"].forEach(function (id) {
    assert.match(html, new RegExp(`id="${id}"`));
  });
  assert.match(engine, /applyTemperatureTint/);
  assert.match(engine, /estimateNeutralGains/);
});

test("preview reads source pixels at native document depth", function () {
  assert.match(common, /componentSize:\s*-1/);
  assert.match(common, /result\.imageData\.componentSize/);
  assert.match(common, /fullRange:\s*fullRange/);
  assert.match(common, /cloneTypedArray\(raw\)/);
});

test("preview buffer depth and ICC profile match the source document", function () {
  assert.match(preview, /thumbnail\.componentSize/);
  assert.match(preview, /thumbnail\.fullRange/);
  assert.match(preview, /colorProfile:\s*c\.resolveColorProfile\(thumbnail, source\.doc\)/);
  assert.match(common, /sRGB IEC61966-2\.1/);
});

test("slider input is coalesced into continuous live preview updates", function () {
  assert.match(common, /PREVIEW_DEBOUNCE_MS = 70/);
  assert.match(entry, /addEventListener\("input", onAdjustmentInput\)/);
  assert.match(entry, /addEventListener\("change", onAdjustmentChange\)/);
  assert.match(preview, /state\.previewQueued = true/);
  assert.match(preview, /schedulePreview\(0\)/);
});

test("preview reuses one scaled temporary layer after initial geometry setup", function () {
  assert.match(common, /async function writePreviewPixels/);
  assert.match(common, /state\.previewGeometryKey/);
  assert.match(common, /imaging\.putPixels/);
  assert.match(common, /layer\.scale\(/);
  assert.doesNotMatch(preview, /deletePreviewInsideModal\(\)[\s\S]{0,400}writePreviewPixels/);
});

test("analysis, preview and final writes use modal scopes", function () {
  assert.match(preview, /core\.executeAsModal/);
  assert.match(preview, /interactive:\s*true/);
  assert.match(finalRuntime, /core\.executeAsModal/);
  assert.match(finalRuntime, /source = storedSource\(\)/);
});

test("UI initialization remains retryable", function () {
  assert.match(entry, /function scheduleInitialize\(/);
  assert.match(entry, /setTimeout\(function \(\)/);
});
