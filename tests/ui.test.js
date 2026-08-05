"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");
const version = read("VERSION").trim();
const coreVersion = version.split("-", 1)[0];
const manifest = JSON.parse(read("plugin/manifest.json"));
const html = read("plugin/index.html");
const css = read("plugin/styles.css");
const common = read("plugin/runtime-common.js");
const preview = read("plugin/runtime-preview.js");
const sampler = read("plugin/runtime-sampler.js");
const runtime = read("plugin/runtime-v022.js");
const numeric = read("plugin/runtime-controls-v050.js");
const finalOps = read("plugin/runtime-final.js");
const engine = read("plugin/engine.js");
const standaloneMain = read("standalone/main.py");
const standaloneApp = read("standalone/ps_sezhao/app.py");
const groups = read("standalone/ps_sezhao/integration_groups.py");
const lifecycle = read("standalone/ps_sezhao/services/lifecycle_facade.py");
const rawIo = read("standalone/ps_sezhao/raw_io.py");
const workflow = read(".github/workflows/release.yml");
const buildScript = read("scripts/build-release.sh");
const lrRoot = "lightroom-classic/PS-Sezhao.lrplugin/";
const lrInfo = read(lrRoot + "Info.lua");
const lrNative = read(lrRoot + "ApplyNative.lua");
const lrRestore = read(lrRoot + "RestoreNative.lua");
const lrProfiles = read(lrRoot + "NativeProfiles.lua");
const lrProcess = read(lrRoot + "ProcessSelected.lua");

test("Beta release keeps UXP numeric core version and full visible version", function () {
  const [major, minor, revision] = coreVersion.split(".").map(Number);
  assert.equal(manifest.version, coreVersion);
  assert.equal(manifest.host.minVersion, "25.0.0");
  assert.match(runtime, new RegExp(`const VERSION = "${version.replaceAll(".", "\\.")}"`));
  assert.match(finalOps, new RegExp(`const VERSION = "${version.replaceAll(".", "\\.")}"`));
  assert.match(lrInfo, /LrSdkMinimumVersion = 15\.4/);
  assert.match(lrInfo, new RegExp(`major = ${major}, minor = ${minor}, revision = ${revision}, build = 1`));
});

test("Lightroom retains native, restore and high precision workflows", function () {
  const nativeIndex = lrInfo.indexOf("file = 'ApplyNative.lua'");
  const tiffIndex = lrInfo.indexOf("file = 'ProcessSelected.lua'");
  assert.ok(nativeIndex >= 0);
  assert.ok(tiffIndex > nativeIndex);
  assert.match(lrInfo, /file = 'RestoreNative\.lua'/);
  assert.match(lrNative, /photo:getDevelopSettings\(\)/);
  assert.match(lrNative, /photo:applyDevelopSettings/);
  assert.match(lrNative, /photo:createDevelopSnapshot/);
  assert.match(lrRestore, /photo:applyDevelopSnapshot/);
  assert.match(lrProfiles, /ExtendedToneCurvePV2012/);
  assert.match(lrProcess, /LrFunctionContext\.postAsyncTaskWithContext/);
  assert.match(lrProcess, /LR_export_bitDepth = 16/);
  assert.match(lrProcess, /LR_colorSpace = 'ProPhotoRGB'/);
});

test("Photoshop current runtime remains Photoshop 2024 compatible", function () {
  [common, preview, sampler, finalOps, runtime, numeric].forEach(function (source) {
    assert.doesNotMatch(source, /\btimeOut\s*:/);
  });
  assert.match(preview, /core\.executeAsModal/);
  assert.match(preview, /interactive:\s*true/);
  assert.match(finalOps, /storedSource\(\)/);
  assert.match(finalOps, /componentSize/);
});

test("Photoshop panel retains live preview, eyedroppers and numeric controls", function () {
  assert.match(html, /class="panel-scroll"/);
  assert.match(html, /class="action-dock"/);
  assert.match(css, /\.panel-scroll\s*\{[^}]*overflow-y:\s*auto/s);
  for (const id of ["temperature", "tint", "redGain", "greenGain", "blueGain", "styleStrength", "pickBase", "pickNeutral"]) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  assert.match(engine, /applyTemperatureTint/);
  assert.match(sampler, /layerID:\s*source\.layer\.id/);
  assert.match(runtime, /initializeNumericControls\(\)/);
  assert.match(numeric, /numeric-step-button/);
});

test("standalone launcher and lifecycle use the unified grouped entrypoint", function () {
  assert.match(standaloneMain, /from ps_sezhao\.bootstrap import run_application/);
  assert.doesNotMatch(standaloneMain, /app_v050_patch|apply_raw_patch|apply_v054_patch/);
  for (const token of [
    "apply_v050_patch",
    "apply_raw_patch",
    "apply_source_crop_patch",
    "apply_v054_patch",
    "apply_proxy_pipeline",
    "apply_output_pipeline",
    "apply_project_session",
    "apply_roll_project_pipeline",
  ]) assert.match(groups, new RegExp(token));
  for (const method of ["_build_ui", "_store_current_state", "load_index", "_save_project_session_now", "_restore_project_session", "_handle_export_event"]) {
    assert.match(lifecycle, new RegExp(method));
  }
  assert.match(standaloneApp, /ttk\.Treeview/);
  assert.match(standaloneApp, /export_selected/);
  assert.match(standaloneApp, /export_all/);
});

test("RAW and release workflows remain complete on both platforms", function () {
  assert.match(rawIo, /output_bps": 16/);
  assert.match(rawIo, /ColorSpace\.ProPhoto/);
  assert.match(rawIo, /extract_thumb\(\)/);
  assert.match(buildScript, /PS-Sezhao-Photoshop-v\$\{VERSION\}\.ccx/);
  assert.match(buildScript, /PS-Sezhao-LightroomClassic-Source-v\$\{VERSION\}\.zip/);
  assert.equal((workflow.match(/--collect-all rawpy/g) || []).length, 2);
  assert.equal((workflow.match(/--collect-all tkinterdnd2/g) || []).length, 2);
  assert.match(workflow, /--gui-smoke-test --require-dnd/);
  assert.match(workflow, /--prerelease --latest=false/);
});
