"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const version = fs.readFileSync(path.join(root, "VERSION"), "utf8").trim();
const html = fs.readFileSync(path.join(root, "plugin/index.html"), "utf8");
const css = fs.readFileSync(path.join(root, "plugin/styles.css"), "utf8");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "plugin/manifest.json"), "utf8"));
const common = fs.readFileSync(path.join(root, "plugin/runtime-common.js"), "utf8");
const preview = fs.readFileSync(path.join(root, "plugin/runtime-preview.js"), "utf8");
const sampler = fs.readFileSync(path.join(root, "plugin/runtime-sampler.js"), "utf8");
const panelPreview = fs.readFileSync(path.join(root, "plugin/runtime-panel-preview.js"), "utf8");
const runtime = fs.readFileSync(path.join(root, "plugin/runtime-v022.js"), "utf8");
const numeric = fs.readFileSync(path.join(root, "plugin/runtime-controls-v050.js"), "utf8");
const finalOps = fs.readFileSync(path.join(root, "plugin/runtime-final.js"), "utf8");
const engine = fs.readFileSync(path.join(root, "plugin/engine.js"), "utf8");
const standaloneApp = fs.readFileSync(path.join(root, "standalone/ps_sezhao/app.py"), "utf8");
const standaloneWorkspace = fs.readFileSync(path.join(root, "standalone/ps_sezhao/workspace.py"), "utf8");
const standaloneJobs = fs.readFileSync(path.join(root, "standalone/ps_sezhao/jobs.py"), "utf8");
const rawIo = fs.readFileSync(path.join(root, "standalone/ps_sezhao/raw_io.py"), "utf8");
const rawPatch = fs.readFileSync(path.join(root, "standalone/ps_sezhao/app_v051_raw_patch.py"), "utf8");
const cropPatch = fs.readFileSync(path.join(root, "standalone/ps_sezhao/app_v052_source_crop_patch.py"), "utf8");
const cropUi = fs.readFileSync(path.join(root, "standalone/ps_sezhao/crop_ui.py"), "utf8");
const lrRoot = path.join(root, "lightroom-classic/PS-Sezhao.lrplugin");
const lrInfo = fs.readFileSync(path.join(lrRoot, "Info.lua"), "utf8");
const lrNative = fs.readFileSync(path.join(lrRoot, "ApplyNative.lua"), "utf8");
const lrProfiles = fs.readFileSync(path.join(lrRoot, "NativeProfiles.lua"), "utf8");
const lrRestore = fs.readFileSync(path.join(lrRoot, "RestoreNative.lua"), "utf8");
const lrProcess = fs.readFileSync(path.join(lrRoot, "ProcessSelected.lua"), "utf8");
const workflow = fs.readFileSync(path.join(root, ".github/workflows/release.yml"), "utf8");
const buildScript = fs.readFileSync(path.join(root, "scripts/build-release.sh"), "utf8");
const developerGuide = fs.readFileSync(path.join(root, "PHOTOSHOP_DEVELOPER_LOAD.md"), "utf8");

test("unified release supports Photoshop 2024 and Lightroom Classic 15.4", function () {
  const [major, minor, revision] = version.split(".").map(Number);
  assert.equal(manifest.version, version);
  assert.equal(manifest.host.minVersion, "25.0.0");
  assert.match(runtime, new RegExp(`const VERSION = "${version.replaceAll(".", "\\.")}"`));
  assert.match(finalOps, new RegExp(`const VERSION = "${version.replaceAll(".", "\\.")}"`));
  assert.match(lrInfo, /LrSdkMinimumVersion = 15\.4/);
  assert.match(lrInfo, new RegExp(`major = ${major}, minor = ${minor}, revision = ${revision}`));
});

test("Lightroom presents native mode first and retains high precision mode", function () {
  const nativeIndex = lrInfo.indexOf("file = 'ApplyNative.lua'");
  const tiffIndex = lrInfo.indexOf("file = 'ProcessSelected.lua'");
  assert.ok(nativeIndex >= 0);
  assert.ok(tiffIndex > nativeIndex);
  assert.match(lrInfo, /file = 'RestoreNative\.lua'/);
  assert.match(lrInfo, /原生直接转正所选照片（默认）/);
  assert.match(lrInfo, /高精度 16 位 TIFF/);
});

test("Lightroom native mode writes non-destructive develop settings", function () {
  assert.match(lrNative, /photo:getDevelopSettings\(\)/);
  assert.match(lrNative, /photo:applyDevelopSettings/);
  assert.match(lrNative, /catalog:withWriteAccessDo/);
  assert.match(lrNative, /LrTasks\.pcall/);
  assert.doesNotMatch(lrNative, /LrExportSession/);
});

test("Lightroom native mode creates a recovery snapshot and restore command", function () {
  assert.match(lrNative, /photo:createDevelopSnapshot/);
  assert.match(lrProfiles, /SNAPSHOT_PREFIX/);
  assert.match(lrRestore, /photo:getDevelopSnapshots\(\)/);
  assert.match(lrRestore, /photo:applyDevelopSnapshot/);
});

test("Lightroom native conversion uses modern and compatibility tone curves", function () {
  assert.match(lrProfiles, /EnableToneCurve = true/);
  assert.match(lrProfiles, /ExtendedToneCurvePV2012/);
  assert.match(lrProfiles, /ToneCurvePV2012/);
  assert.match(lrProfiles, /ExtendedToneCurvePV2012Red/);
  assert.match(lrProfiles, /ExtendedToneCurvePV2012Green/);
  assert.match(lrProfiles, /ExtendedToneCurvePV2012Blue/);
  assert.match(lrProfiles, /WhiteBalance = 'Custom'/);
});

test("Lightroom high precision export remains yield-safe and 16-bit", function () {
  assert.match(lrProcess, /LrFunctionContext\.postAsyncTaskWithContext/);
  assert.match(lrProcess, /LrTasks\.pcall\(processSelected, functionContext\)/);
  assert.match(lrProcess, /LrTasks\.canYield\(\)/);
  assert.match(lrProcess, /LrExportSession/);
  assert.match(lrProcess, /LR_export_bitDepth = 16/);
  assert.match(lrProcess, /LR_colorSpace = 'ProPhotoRGB'/);
  assert.match(lrProcess, /catalog:addPhoto/);
});

test("Photoshop 2024 compatibility avoids the 25.10-only modal timeout option", function () {
  [common, preview, sampler, finalOps, runtime, numeric].forEach(function (source) {
    assert.doesNotMatch(source, /\btimeOut\s*:/);
  });
  assert.match(preview, /interactive:\s*true/);
  assert.match(preview, /core\.executeAsModal/);
});

test("Photoshop panel keeps scroll, live preview and advanced controls", function () {
  assert.match(html, /class="panel-scroll"/);
  assert.match(html, /class="action-dock"/);
  assert.match(css, /\.panel-scroll\s*\{[^}]*overflow-y:\s*auto/s);
  ["temperature", "tint", "redGain", "greenGain", "blueGain", "styleStrength"].forEach(function (id) {
    assert.match(html, new RegExp(`id="${id}"`));
  });
  assert.match(engine, /applyTemperatureTint/);
});

test("Photoshop range controls gain manual numeric input and step buttons", function () {
  assert.match(runtime, /runtime-controls-v050\.js/);
  assert.match(runtime, /initializeNumericControls\(\)/);
  assert.match(numeric, /numeric-value-input/);
  assert.match(numeric, /numeric-step-button/);
  assert.match(numeric, /dispatchRange/);
  assert.match(numeric, /ArrowUp/);
  assert.match(numeric, /ArrowDown/);
  assert.match(css, /\.numeric-stepper/);
  assert.match(css, /\.numeric-value-input/);
});

test("Photoshop eyedroppers sample the remembered original layer, not preview pixels", function () {
  ["panelPreviewStage", "panelPreviewImage", "panelPreviewZoom", "pickBase", "pickNeutral", "sampleSize"].forEach(function (id) {
    assert.match(html, new RegExp(`id="${id}"`));
  });
  assert.match(preview, /imaging\.encodeImageData/);
  assert.match(panelPreview, /mapEventToDocument/);
  assert.match(sampler, /layerID:\s*source\.layer\.id/);
  assert.match(sampler, /state\.analysis \? storedSource\(\) : ensureActiveCandidate\(\)/);
  assert.match(sampler, /handlePanelPreviewClick/);
  assert.match(html, /id="baseAdjustR"/);
  assert.match(html, /id="baseAdjustG"/);
  assert.match(html, /id="baseAdjustB"/);
});

test("standalone edition exposes multi-photo navigation and synchronization", function () {
  assert.match(standaloneApp, /ttk\.Treeview/);
  assert.match(standaloneApp, /open_folder_dialog/);
  assert.match(standaloneApp, /step_item/);
  assert.match(standaloneApp, /sync_controls_selected/);
  assert.match(standaloneApp, /sync_crop_selected/);
  assert.match(standaloneApp, /export_selected/);
  assert.match(standaloneApp, /export_all/);
});

test("standalone v0.5.2 shows only the applied crop and restores full image for editing", function () {
  assert.match(cropPatch, /self\.crop_editing/);
  assert.match(cropPatch, /text="完成裁切"/);
  assert.match(cropPatch, /shown = crop_array\(self\._display_full_array, self\.crop_norm\)/);
  assert.match(cropPatch, /if not self\.crop_editing/);
  assert.match(cropPatch, /app_class\._draw_crop_overlay = draw_crop_overlay/);
  assert.match(cropPatch, /crop_hit_test/);
  assert.match(cropUi, /update_crop_from_drag/);
});

test("standalone base picker reads original source and exposes manual RGB base adjustment", function () {
  assert.match(cropPatch, /sample_median_rgb\(self\.preview_source/);
  assert.match(cropPatch, /map_view_point_to_source/);
  assert.match(cropPatch, /base_adjust_units/);
  assert.match(cropPatch, /胶片基底手动微调/);
  assert.match(cropPatch, /payload\["base_adjust"\]/);
});

test("automatic border analysis and unsaved batch analysis use the crop", function () {
  assert.match(cropPatch, /return crop_array\(self\.preview_source, self\.crop_norm\)/);
  assert.match(cropPatch, /method="crop-border"/);
  assert.match(standaloneJobs, /source = crop_array\(image, crop\)/);
  assert.ok(standaloneJobs.indexOf("source = crop_array(image, crop)") < standaloneJobs.indexOf("analysis_source = make_preview(source, 1800)"));
});

test("standalone sliders support entry and plus-minus micro adjustment", function () {
  assert.match(standaloneApp, /ttk\.Entry/);
  assert.match(standaloneApp, /commit_entry/);
  assert.match(standaloneApp, /adjust_control/);
  assert.match(standaloneApp, /text="−"/);
  assert.match(standaloneApp, /text="\+"/);
});

test("standalone directly decodes camera RAW", function () {
  assert.match(rawIo, /class RawDecodeSettings/);
  assert.match(rawIo, /output_bps": 16/);
  assert.match(rawIo, /ColorSpace\.ProPhoto/);
  assert.match(rawIo, /extract_thumb\(\)/);
  assert.match(rawPatch, /重新解码当前 RAW/);
  assert.match(rawPatch, /自定义通道倍率/);
  assert.match(standaloneWorkspace, /RAW_EXTENSIONS/);
});

test("Photoshop final render preserves depth, profile and original source", function () {
  assert.match(common, /componentSize:\s*-1/);
  assert.match(common, /resolveColorProfile/);
  assert.match(preview, /colorProfile:\s*c\.resolveColorProfile/);
  assert.match(finalOps, /storedSource\(\)/);
  assert.match(finalOps, /sourceLayerId/);
});

test("release workflow builds Photoshop, Lightroom and RAW-capable standalone assets", function () {
  assert.match(buildScript, /PS-Sezhao-Photoshop-v\$\{VERSION\}\.ccx/);
  assert.match(buildScript, /unzip -Z1/);
  assert.match(buildScript, /PS-Sezhao-Photoshop-Developer-v\$\{VERSION\}\.zip/);
  assert.match(developerGuide, /Add Plugin/);
  assert.match(workflow, /LightroomClassic-macOS-arm64/);
  assert.match(workflow, /LightroomClassic-Windows-x64/);
  assert.match(workflow, /Standalone-macOS-arm64/);
  assert.match(workflow, /Standalone-Windows-x64/);
  assert.equal((workflow.match(/--collect-all rawpy/g) || []).length, 2);
  assert.match(workflow, /pyinstaller/);
});
