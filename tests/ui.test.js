"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "plugin/index.html"), "utf8");
const css = fs.readFileSync(path.join(root, "plugin/styles.css"), "utf8");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "plugin/manifest.json"), "utf8"));
const common = fs.readFileSync(path.join(root, "plugin/runtime-common.js"), "utf8");
const preview = fs.readFileSync(path.join(root, "plugin/runtime-preview.js"), "utf8");
const sampler = fs.readFileSync(path.join(root, "plugin/runtime-sampler.js"), "utf8");
const panelPreview = fs.readFileSync(path.join(root, "plugin/runtime-panel-preview.js"), "utf8");
const runtime = fs.readFileSync(path.join(root, "plugin/runtime-v022.js"), "utf8");
const finalOps = fs.readFileSync(path.join(root, "plugin/runtime-final.js"), "utf8");
const engine = fs.readFileSync(path.join(root, "plugin/engine.js"), "utf8");
const lrInfo = fs.readFileSync(path.join(root, "lightroom-classic/PS-Sezhao.lrplugin/Info.lua"), "utf8");
const lrProcess = fs.readFileSync(path.join(root, "lightroom-classic/PS-Sezhao.lrplugin/ProcessSelected.lua"), "utf8");
const workflow = fs.readFileSync(path.join(root, ".github/workflows/release.yml"), "utf8");

test("unified release targets current Photoshop and Lightroom Classic generations", function () {
  assert.equal(manifest.version, "0.3.0");
  assert.equal(manifest.host.minVersion, "27.8.0");
  assert.match(html, /PS-SEZHAO · 0\.3\.0/);
  assert.match(finalOps, /const VERSION = "0\.3\.0"/);
  assert.match(lrInfo, /LrSdkMinimumVersion = 15\.4/);
  assert.match(lrInfo, /major = 0, minor = 3, revision = 0/);
});

test("panel keeps a bounded scroll area and fixed action dock", function () {
  assert.match(html, /class="panel-scroll"/);
  assert.match(html, /class="action-dock"/);
  assert.match(css, /\.panel-scroll\s*\{[^}]*overflow-y:\s*auto/s);
  assert.match(css, /\.panel-shell\s*\{[^}]*height:\s*100%/s);
});

test("advanced color controls remain present", function () {
  ["temperature", "tint", "redGain", "greenGain", "blueGain", "baseAdjustR", "baseAdjustG", "baseAdjustB", "styleStrength"].forEach(function (id) {
    assert.match(html, new RegExp(`id="${id}"`));
  });
  assert.match(engine, /applyTemperatureTint/);
  assert.match(engine, /estimateNeutralGains/);
});

test("large preview supports fit, 100 percent, 200 percent and expansion", function () {
  ["panelPreviewStage", "panelPreviewImage", "panelPreviewZoom", "panelPreviewExpand"].forEach(function (id) {
    assert.match(html, new RegExp(`id="${id}"`));
  });
  assert.match(html, /value="fit"/);
  assert.match(html, /value="100"/);
  assert.match(html, /value="200"/);
  assert.match(css, /\.panel-preview-stage\.expanded/);
  assert.match(css, /height:\s*680px/);
  assert.match(panelPreview, /mapEventToDocument/);
});

test("large preview is encoded from Photoshop image data", function () {
  assert.match(preview, /imaging\.encodeImageData/);
  assert.match(preview, /data:image\/jpeg;base64/);
  assert.match(preview, /panelPreview\.setImage/);
});

test("click eyedroppers use native color sampler tool with panel fallback", function () {
  ["pickBase", "pickNeutral", "cancelPicker", "sampleSize"].forEach(function (id) {
    assert.match(html, new RegExp(`id="${id}"`));
  });
  assert.match(sampler, /colorSamplerTool/);
  assert.match(sampler, /doc\.colorSamplers/);
  assert.match(sampler, /action\.batchPlay/);
  assert.match(sampler, /handlePanelPreviewClick/);
  assert.match(sampler, /readPatch/);
  assert.match(sampler, /estimateNeutralGains/);
});

test("sampling options include point and area averages", function () {
  ["1", "3", "5", "11", "21"].forEach(function (value) {
    assert.match(html, new RegExp(`<option value="${value}"`));
  });
});

test("canvas preview preserves document depth and profile", function () {
  assert.match(common, /componentSize:\s*-1/);
  assert.match(common, /fullRange/);
  assert.match(common, /resolveColorProfile/);
  assert.match(preview, /colorProfile:\s*c\.resolveColorProfile/);
});

test("analysis and image writes stay inside modal scopes", function () {
  assert.match(preview, /core\.executeAsModal/);
  assert.match(preview, /writePreviewPixels/);
  assert.match(sampler, /core\.executeAsModal/);
  assert.match(sampler, /imaging\.getPixels/);
});

test("final render uses stored source rather than active preview layer", function () {
  assert.match(finalOps, /storedSource\(\)/);
  assert.match(finalOps, /sourceLayerId/);
});

test("Photoshop runtime initializes preview and sampler modules", function () {
  assert.match(runtime, /panelPreview\.initialize\(\)/);
  assert.match(runtime, /sampler\.initialize\(\)/);
  assert.match(runtime, /function scheduleInitialize\(/);
  assert.match(html, /src="runtime-v022\.js"/);
});

test("Lightroom workflow renders 16-bit TIFFs, starts local editor and imports outputs", function () {
  assert.match(lrProcess, /LrExportSession/);
  assert.match(lrProcess, /LR_export_bitDepth = 16/);
  assert.match(lrProcess, /--lr-job/);
  assert.match(lrProcess, /catalog:addPhoto/);
  assert.match(lrProcess, /PS-Sezhao/);
});

test("release workflow builds Photoshop, Lightroom and standalone assets on both platforms", function () {
  assert.match(workflow, /PS-Sezhao-Photoshop/);
  assert.match(workflow, /LightroomClassic-macOS-arm64/);
  assert.match(workflow, /LightroomClassic-Windows-x64/);
  assert.match(workflow, /Standalone-macOS-arm64/);
  assert.match(workflow, /Standalone-Windows-x64/);
  assert.match(workflow, /pyinstaller/);
});
