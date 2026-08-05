import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const root = path.resolve(process.cwd());
const plugin = path.join(root, "plugin");
const lrPlugin = path.join(root, "lightroom-classic/PS-Sezhao.lrplugin");
const manifest = JSON.parse(fs.readFileSync(path.join(plugin, "manifest.json"), "utf8"));
const runtimeScripts = [
  "engine.js",
  "runtime-common.js",
  "runtime-engine-v053.js",
  "runtime-history-v054.js",
  "runtime-panel-preview.js",
  "runtime-sampler.js",
  "runtime-preview.js",
  "runtime-final.js",
  "runtime-controls-v050.js",
  "runtime-v022.js"
];
const requiredPluginFiles = ["manifest.json", "index.html", "styles.css", ...runtimeScripts];
const requiredProjectFiles = [
  "lightroom-classic/PS-Sezhao.lrplugin/Info.lua",
  "lightroom-classic/PS-Sezhao.lrplugin/ApplyNative.lua",
  "lightroom-classic/PS-Sezhao.lrplugin/NativeProfiles.lua",
  "lightroom-classic/PS-Sezhao.lrplugin/RestoreNative.lua",
  "lightroom-classic/PS-Sezhao.lrplugin/ProcessSelected.lua",
  "lightroom-classic/PS-Sezhao.lrplugin/PluginInfoProvider.lua",
  "lightroom-classic/tests/native_profiles_test.lua",
  "standalone/main.py",
  "standalone/ps_sezhao/__init__.py",
  "standalone/ps_sezhao/app.py",
  "standalone/ps_sezhao/app_v050_patch.py",
  "standalone/ps_sezhao/app_v051_raw_patch.py",
  "standalone/ps_sezhao/app_v052_source_crop_patch.py",
  "standalone/ps_sezhao/app_v053_scroll_patch.py",
  "standalone/ps_sezhao/app_v054_history_direct_patch.py",
  "standalone/ps_sezhao/history_state.py",
  "standalone/ps_sezhao/color_profiles.py",
  "standalone/ps_sezhao/engine.py",
  "standalone/ps_sezhao/engine_v053_patch.py",
  "standalone/ps_sezhao/io_utils.py",
  "standalone/ps_sezhao/jobs.py",
  "standalone/ps_sezhao/processing.py",
  "standalone/ps_sezhao/raw_io.py",
  "standalone/ps_sezhao/workspace.py",
  "standalone/tests/test_workspace.py",
  "standalone/tests/test_raw_io.py",
  "standalone/tests/test_history_v054.py",
  "PHOTOSHOP_DEVELOPER_LOAD.md",
  "scripts/build-release.sh"
];

for (const file of requiredPluginFiles) {
  const filePath = path.join(plugin, file);
  if (!fs.existsSync(filePath) || fs.statSync(filePath).size === 0) {
    throw new Error(`Missing or empty Photoshop plugin file: ${file}`);
  }
}
for (const file of requiredProjectFiles) {
  const filePath = path.join(root, file);
  if (!fs.existsSync(filePath) || fs.statSync(filePath).size === 0) {
    throw new Error(`Missing or empty unified project file: ${file}`);
  }
}

if (manifest.manifestVersion !== 5) throw new Error("manifestVersion must be 5");
if (manifest.host?.app !== "PS") throw new Error("host.app must be PS");
if (manifest.host?.minVersion !== "25.0.0") throw new Error("Photoshop minVersion must target Photoshop 2024 (25.0.0)");
if (!/^\d+\.\d+\.\d+$/.test(manifest.version)) throw new Error("manifest.version must be semver x.y.z");
if (!manifest.entrypoints?.some((item) => item.type === "panel" && item.id === "sezhaoPanel")) {
  throw new Error("sezhaoPanel entrypoint is missing");
}

const version = fs.readFileSync(path.join(root, "VERSION"), "utf8").trim();
const packageJson = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
if (version !== manifest.version) throw new Error(`VERSION (${version}) does not match manifest (${manifest.version})`);
if (version !== packageJson.version) throw new Error(`VERSION (${version}) does not match package.json (${packageJson.version})`);

const html = fs.readFileSync(path.join(plugin, "index.html"), "utf8");
if (!html.includes('src="runtime-v022.js"')) throw new Error("index.html must load runtime-v022.js");
const runtimeEntry = fs.readFileSync(path.join(plugin, "runtime-v022.js"), "utf8");
if (!runtimeEntry.includes(`const VERSION = "${version}"`)) throw new Error("Photoshop runtime version label is stale");
if (!runtimeEntry.includes('require("./runtime-controls-v050.js")')) throw new Error("Photoshop numeric controls are not loaded");
if (!runtimeEntry.includes('require("./runtime-history-v054.js")')) throw new Error("Photoshop history/direct-base runtime is not loaded");
if (!/initializeNumericControls\(\)/.test(runtimeEntry)) throw new Error("Photoshop numeric controls are not initialized");
if (!/history\.initialize\(\)/.test(runtimeEntry)) throw new Error("Photoshop undo/redo history is not initialized");
const finalRuntime = fs.readFileSync(path.join(plugin, "runtime-final.js"), "utf8");
if (!finalRuntime.includes(`const VERSION = "${version}"`)) throw new Error("Photoshop output layer version is stale");

const [major, minor, revision] = version.split(".").map(Number);
const lrInfo = fs.readFileSync(path.join(lrPlugin, "Info.lua"), "utf8");
const lrVersionPattern = new RegExp(`major\\s*=\\s*${major},\\s*minor\\s*=\\s*${minor},\\s*revision\\s*=\\s*${revision}`);
if (!lrVersionPattern.test(lrInfo)) throw new Error("Lightroom plugin version is stale");
const nativeMenuIndex = lrInfo.indexOf("file = 'ApplyNative.lua'");
const tiffMenuIndex = lrInfo.indexOf("file = 'ProcessSelected.lua'");
if (nativeMenuIndex < 0 || tiffMenuIndex <= nativeMenuIndex) throw new Error("Lightroom native mode must be the first release menu entry");
if (!lrInfo.includes("file = 'RestoreNative.lua'")) throw new Error("Lightroom native restore entry is missing");

const lrProcess = fs.readFileSync(path.join(lrPlugin, "ProcessSelected.lua"), "utf8");
if (!/LrFunctionContext\.postAsyncTaskWithContext/.test(lrProcess)) {
  throw new Error("Lightroom export must start through postAsyncTaskWithContext");
}
if (!/LrTasks\.pcall\(processSelected, functionContext\)/.test(lrProcess)) {
  throw new Error("Lightroom export must use the yield-safe LrTasks.pcall wrapper");
}
if (!/LrExportSession/.test(lrProcess) || !/LR_export_bitDepth = 16/.test(lrProcess)) {
  throw new Error("Lightroom high-precision mode must retain 16-bit TIFF export");
}

const lrNative = fs.readFileSync(path.join(lrPlugin, "ApplyNative.lua"), "utf8");
const lrProfiles = fs.readFileSync(path.join(lrPlugin, "NativeProfiles.lua"), "utf8");
const lrRestore = fs.readFileSync(path.join(lrPlugin, "RestoreNative.lua"), "utf8");
if (!/photo:getDevelopSettings\(\)/.test(lrNative)) throw new Error("Native mode must read current Lightroom develop settings");
if (!/photo:applyDevelopSettings/.test(lrNative)) throw new Error("Native mode must directly apply Lightroom develop settings");
if (!/photo:createDevelopSnapshot/.test(lrNative)) throw new Error("Native mode must create an optional recovery snapshot");
if (!/catalog:withWriteAccessDo/.test(lrNative)) throw new Error("Native develop edits must use a catalog write gate");
if (!/LrTasks\.pcall/.test(lrNative)) throw new Error("Native mode must use yield-safe protected calls");
if (!/ExtendedToneCurvePV2012/.test(lrProfiles)) throw new Error("Native mode must define a modern Lightroom inversion curve");
if (!/EnableToneCurve = true/.test(lrProfiles)) throw new Error("Native mode must explicitly enable the tone curve");
if (!/photo:applyDevelopSnapshot/.test(lrRestore)) throw new Error("Native restore must apply the saved develop snapshot");

const standaloneInit = fs.readFileSync(path.join(root, "standalone/ps_sezhao/__init__.py"), "utf8");
if (!standaloneInit.includes(`__version__ = "${version}"`)) throw new Error("Standalone version is stale");
const standaloneMain = fs.readFileSync(path.join(root, "standalone/main.py"), "utf8");
const standaloneApp = fs.readFileSync(path.join(root, "standalone/ps_sezhao/app.py"), "utf8");
const standaloneJobs = fs.readFileSync(path.join(root, "standalone/ps_sezhao/jobs.py"), "utf8");
const rawIo = fs.readFileSync(path.join(root, "standalone/ps_sezhao/raw_io.py"), "utf8");
const rawPatch = fs.readFileSync(path.join(root, "standalone/ps_sezhao/app_v051_raw_patch.py"), "utf8");
const historyPatch = fs.readFileSync(path.join(root, "standalone/ps_sezhao/app_v054_history_direct_patch.py"), "utf8");
const historyState = fs.readFileSync(path.join(root, "standalone/ps_sezhao/history_state.py"), "utf8");
const workspace = fs.readFileSync(path.join(root, "standalone/ps_sezhao/workspace.py"), "utf8");
const requirements = fs.readFileSync(path.join(root, "standalone/requirements.txt"), "utf8");
for (const token of ["ttk.Treeview", "open_folder_dialog", "zoom_at", "crop_norm", "sync_controls_selected", "sync_crop_selected", "export_selected", "export_all", "commit_entry", "adjust_control"]) {
  if (!standaloneApp.includes(token)) throw new Error(`Standalone v0.5.0 feature is missing: ${token}`);
}
if (!standaloneJobs.includes("crop_array")) throw new Error("Standalone/Lightroom batch jobs must apply non-destructive crop");
if (!standaloneMain.includes("apply_raw_patch")) throw new Error("Standalone launcher does not enable v0.5.1 RAW support");
if (!standaloneMain.includes("apply_v054_patch")) throw new Error("Standalone launcher does not enable v0.5.4 history/direct-base support");
for (const token of ["HistoryStack", "undo_edit", "redo_edit", "胶片基底（直接数值）", "中性灰校正（RGB 输出增益）", "direct - self.detected_base()"] ) {
  if (!historyPatch.includes(token)) throw new Error(`Standalone v0.5.4 feature is missing: ${token}`);
}
if (!historyState.includes("redo_items") || !historyState.includes("def undo") || !historyState.includes("def redo")) {
  throw new Error("Standalone undo/redo history stack is incomplete");
}
for (const token of ["rawpy", "output_bps\": 16", "gamma\": (1.0, 1.0)", "ColorSpace.ProPhoto", "no_auto_bright\": True", "extract_thumb", "LibRawFileUnsupportedError", "prepare_save_output"]) {
  const literal = token.replace(/\\"/g, '"');
  if (!rawIo.includes(literal)) throw new Error(`RAW decoder feature is missing: ${literal}`);
}
for (const token of ["重新解码当前 RAW", "相机拍摄白平衡", "自定义通道倍率", "优先读取 RAW 内嵌预览", "16 位线性解码", "extract_raw_preview"]) {
  if (!rawPatch.includes(token)) throw new Error(`RAW user interface feature is missing: ${token}`);
}
for (const extension of [".cr2", ".cr3", ".nef", ".arw", ".raf", ".rw2", ".orf", ".dng"]) {
  if (!rawIo.includes(`"${extension}"`)) throw new Error(`Common RAW extension is missing: ${extension}`);
}
if (!workspace.includes("RAW_EXTENSIONS")) throw new Error("Folder discovery does not include RAW files");
if (!requirements.includes("rawpy>=0.27,<0.28")) throw new Error("rawpy runtime dependency is missing or unpinned");
if (!standaloneJobs.includes("RawDecodeSettings") || !standaloneJobs.includes("prepare_save_output")) {
  throw new Error("Batch jobs do not preserve RAW decode/output settings");
}

for (const script of runtimeScripts) {
  const scriptPath = path.join(plugin, script);
  const source = fs.readFileSync(scriptPath, "utf8");
  if (/\btimeOut\s*:/.test(source)) {
    throw new Error(`${script} uses executeAsModal.timeOut, which breaks early Photoshop 2024 releases`);
  }
  const result = spawnSync(process.execPath, ["--check", scriptPath], { encoding: "utf8" });
  if (result.status !== 0) throw new Error(`${script} syntax check failed:\n${result.stderr || result.stdout}`);
}

const numericRuntime = fs.readFileSync(path.join(plugin, "runtime-controls-v050.js"), "utf8");
for (const token of ["numeric-value-input", "numeric-step-button", "dispatchRange", "ArrowUp", "ArrowDown"]) {
  if (!numericRuntime.includes(token)) throw new Error(`Photoshop numeric interaction is missing: ${token}`);
}
const historyRuntime = fs.readFileSync(path.join(plugin, "runtime-history-v054.js"), "utf8");
for (const token of ["undoEdit", "redoEdit", "resetNeutralGains", "directBaseValue(index) - Number(detected[index]", "中性灰吸管修改的是下方红、绿、蓝输出增益"]) {
  if (!historyRuntime.includes(token)) throw new Error(`Photoshop v0.5.4 history/direct-base feature is missing: ${token}`);
}
const css = fs.readFileSync(path.join(plugin, "styles.css"), "utf8");
if (!css.includes(".numeric-stepper") || !css.includes(".numeric-value-input")) {
  throw new Error("Photoshop numeric control styles are missing");
}

const buildScript = fs.readFileSync(path.join(root, "scripts/build-release.sh"), "utf8");
if (!buildScript.includes("PS-Sezhao-Photoshop-v${VERSION}.ccx")) throw new Error("Photoshop CCX is missing from common release build");
if (!buildScript.includes("PS-Sezhao-Photoshop-Developer-v${VERSION}.zip")) throw new Error("Developer-load ZIP is missing from common release build");
if (!buildScript.includes("unzip -Z1")) throw new Error("CCX root structure validation is missing");
if (!buildScript.includes("manifest.host?.minVersion !== \"25.0.0\"")) throw new Error("CCX Photoshop 2024 validation is missing");
const workflow = fs.readFileSync(path.join(root, ".github/workflows/release.yml"), "utf8");
if ((workflow.match(/--collect-all rawpy/g) || []).length < 2) {
  throw new Error("Both macOS and Windows packages must collect rawpy/LibRaw binaries");
}
if (!workflow.includes("Verify RAW runtime")) throw new Error("CI does not verify the RAW runtime");

console.log(`Validated unified PS-Sezhao ${version} with undo/redo, direct base RGB, editable neutral gains and camera RAW support`);
