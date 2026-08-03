"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "plugin/index.html"), "utf8");
const css = fs.readFileSync(path.join(root, "plugin/styles.css"), "utf8");
const main = fs.readFileSync(path.join(root, "plugin/main.js"), "utf8");
const engine = fs.readFileSync(path.join(root, "plugin/engine.js"), "utf8");

test("panel keeps a bounded scroll area and fixed action dock", function () {
  assert.match(html, /class="panel-scroll"/);
  assert.match(html, /class="action-dock"/);
  assert.match(css, /\.panel-scroll\s*\{[^}]*overflow-y:\s*auto/s);
  assert.match(css, /\.panel-shell\s*\{[^}]*height:\s*100%/s);
});

test("advanced color controls are present", function () {
  ["temperature", "tint", "redGain", "greenGain", "blueGain", "baseAdjustR", "baseAdjustG", "baseAdjustB", "styleStrength"].forEach(function (id) {
    assert.match(html, new RegExp(`id="${id}"`));
  });
  assert.match(engine, /applyTemperatureTint/);
  assert.match(engine, /estimateNeutralGains/);
});

test("preview uses debounce, a temporary canvas layer and supported layer scaling", function () {
  assert.match(main, /PREVIEW_DEBOUNCE_MS/);
  assert.match(main, /PS-Sezhao · 实时预览/);
  assert.match(main, /async function replaceScaledPreview/);
  assert.match(main, /layer\.scale\(scaleX, scaleY/);
  assert.doesNotMatch(main, /imaging\.putPixels\(\{[\s\S]{0,500}targetSize:/);
  assert.match(main, /interactive:\s*true/);
});

test("analysis and image writes stay inside modal scopes", function () {
  const analyzeStart = main.indexOf("async function analyze");
  const previewStart = main.indexOf("async function renderPreview");
  const convertStart = main.indexOf("async function convert");
  assert.ok(analyzeStart >= 0 && previewStart > analyzeStart && convertStart > previewStart);
  const analyzeBlock = main.slice(analyzeStart, previewStart);
  const previewBlock = main.slice(previewStart, convertStart);
  assert.match(analyzeBlock, /core\.executeAsModal/);
  assert.match(analyzeBlock, /readThumbnail/);
  assert.match(previewBlock, /core\.executeAsModal/);
  assert.match(main, /async function replaceScaledPreview[\s\S]*imaging\.putPixels/);
});

test("final render uses stored source rather than the active preview layer", function () {
  assert.match(main, /function storedSource\(/);
  assert.match(main, /source = storedSource\(\)/);
  assert.match(main, /sourceLayerId/);
});

test("UI initialization remains retryable", function () {
  assert.match(main, /function scheduleInitialize\(/);
  assert.match(main, /setTimeout\(function \(\)/);
});
