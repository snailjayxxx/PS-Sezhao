import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const root = path.resolve(process.cwd());
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");
const requireFile = (relative) => {
  const target = path.join(root, relative);
  if (!fs.existsSync(target) || fs.statSync(target).size === 0) {
    throw new Error(`Missing or empty project file: ${relative}`);
  }
};
const requireTokens = (source, tokens, label) => {
  for (const token of tokens) {
    if (!source.includes(token)) throw new Error(`${label} is missing: ${token}`);
  }
};

const version = read("VERSION").trim();
const packageJson = JSON.parse(read("package.json"));
const manifest = JSON.parse(read("plugin/manifest.json"));

if (!/^\d+\.\d+\.\d+$/.test(version)) throw new Error("VERSION must be semver x.y.z");
if (packageJson.version !== version) throw new Error(`VERSION (${version}) does not match package.json (${packageJson.version})`);
if (manifest.version !== version) throw new Error(`VERSION (${version}) does not match manifest (${manifest.version})`);
if (manifest.manifestVersion !== 5 || manifest.host?.app !== "PS") throw new Error("Photoshop manifest is invalid");
if (manifest.host?.minVersion !== "25.0.0") throw new Error("Photoshop minimum version must be 25.0.0");
if (!manifest.entrypoints?.some((item) => item.type === "panel" && item.id === "sezhaoPanel")) {
  throw new Error("Photoshop panel entrypoint is missing");
}

const runtimeScripts = [
  "plugin/engine.js",
  "plugin/runtime-common.js",
  "plugin/runtime-engine-v053.js",
  "plugin/runtime-history-v054.js",
  "plugin/runtime-panel-preview.js",
  "plugin/runtime-sampler.js",
  "plugin/runtime-preview.js",
  "plugin/runtime-final.js",
  "plugin/runtime-controls-v050.js",
  "plugin/runtime-v022.js",
];
const requiredFiles = [
  "plugin/index.html",
  "plugin/styles.css",
  ...runtimeScripts,
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
  "standalone/ps_sezhao/app_v054_sync_patch.py",
  "standalone/ps_sezhao/app_v055_import_drop_patch.py",
  "standalone/ps_sezhao/history_state.py",
  "standalone/ps_sezhao/raw_io.py",
  "standalone/ps_sezhao/workspace.py",
  "standalone/hooks/hook-tkinterdnd2.py",
  "standalone/tests/test_history_v054.py",
  "standalone/tests/test_import_drop_v055.py",
  "tests/v055.test.js",
  "scripts/build-release.sh",
  "PHOTOSHOP_DEVELOPER_LOAD.md",
];
requiredFiles.forEach(requireFile);

const runtimeEntry = read("plugin/runtime-v022.js");
requireTokens(runtimeEntry, [
  `const VERSION = "${version}"`,
  'require("./runtime-controls-v050.js")',
  'require("./runtime-history-v054.js")',
  "initializeNumericControls()",
  "history.initialize()",
], "Photoshop runtime");
if (!read("plugin/runtime-final.js").includes(`const VERSION = "${version}"`)) {
  throw new Error("Photoshop output layer version is stale");
}
requireTokens(read("plugin/runtime-history-v054.js"), [
  "undoEdit",
  "redoEdit",
  "resetNeutralGains",
  "directBaseValue(index) - Number(detected[index]",
  "中性灰吸管修改的是下方红、绿、蓝输出增益",
], "Photoshop history/direct-base runtime");

for (const relative of runtimeScripts) {
  const source = read(relative);
  if (/\btimeOut\s*:/.test(source)) throw new Error(`${relative} uses the Photoshop 25.10-only timeOut option`);
  const result = spawnSync(process.execPath, ["--check", path.join(root, relative)], { encoding: "utf8" });
  if (result.status !== 0) throw new Error(`${relative} syntax check failed:\n${result.stderr || result.stdout}`);
}

const [major, minor, revision] = version.split(".").map(Number);
const lrInfo = read("lightroom-classic/PS-Sezhao.lrplugin/Info.lua");
const lrVersion = new RegExp(`major\\s*=\\s*${major},\\s*minor\\s*=\\s*${minor},\\s*revision\\s*=\\s*${revision}`);
if (!lrVersion.test(lrInfo)) throw new Error("Lightroom plugin version is stale");
requireTokens(lrInfo, ["ApplyNative.lua", "ProcessSelected.lua", "RestoreNative.lua"], "Lightroom menu");
const lrProcess = read("lightroom-classic/PS-Sezhao.lrplugin/ProcessSelected.lua");
requireTokens(lrProcess, ["LrFunctionContext.postAsyncTaskWithContext", "LrTasks.pcall(processSelected, functionContext)", "LrExportSession", "LR_export_bitDepth = 16"], "Lightroom high-precision workflow");
const lrNative = read("lightroom-classic/PS-Sezhao.lrplugin/ApplyNative.lua");
requireTokens(lrNative, ["photo:getDevelopSettings()", "photo:applyDevelopSettings", "photo:createDevelopSnapshot", "catalog:withWriteAccessDo", "LrTasks.pcall"], "Lightroom native workflow");
requireTokens(read("lightroom-classic/PS-Sezhao.lrplugin/NativeProfiles.lua"), ["ExtendedToneCurvePV2012", "EnableToneCurve = true"], "Lightroom native profiles");
if (!read("lightroom-classic/PS-Sezhao.lrplugin/RestoreNative.lua").includes("photo:applyDevelopSnapshot")) {
  throw new Error("Lightroom native restore is incomplete");
}

if (!read("standalone/ps_sezhao/__init__.py").includes(`__version__ = "${version}"`)) {
  throw new Error("Standalone version is stale");
}
const standaloneMain = read("standalone/main.py");
requireTokens(standaloneMain, [
  "apply_raw_patch",
  "apply_v054_patch",
  "apply_v054_sync_patch",
  "apply_v055_import_drop_patch",
  "install_drag_drop_root",
], "Standalone launcher");
requireTokens(read("standalone/ps_sezhao/app_v055_import_drop_patch.py"), [
  '("history_for", "_history_for")',
  "drop_target_register(DND_FILES)",
  'dnd_bind("<<Drop>>"',
  "root.tk.splitlist",
  'folder.rglob("*")',
  "self.open_paths(unique)",
  "添加图片失败",
], "v0.5.5 import/drag-drop patch");
requireTokens(read("standalone/ps_sezhao/app_v054_history_direct_patch.py"), [
  "HistoryStack",
  "undo_edit",
  "redo_edit",
  "胶片基底（直接数值）",
  "中性灰校正（RGB 输出增益）",
  "direct - self.detected_base()",
], "v0.5.4 history/direct-base patch");

const rawIo = read("standalone/ps_sezhao/raw_io.py");
requireTokens(rawIo, ["rawpy", "output_bps\": 16", "gamma\": (1.0, 1.0)", "ColorSpace.ProPhoto", "no_auto_bright\": True", "extract_thumb", "prepare_save_output"], "RAW decoder");
for (const extension of [".cr2", ".cr3", ".nef", ".arw", ".raf", ".rw2", ".orf", ".dng"]) {
  if (!rawIo.includes(`"${extension}"`)) throw new Error(`RAW extension is missing: ${extension}`);
}
const requirements = read("standalone/requirements.txt");
requireTokens(requirements, ["rawpy>=0.27,<0.28", "tkinterdnd2>=0.4.3,<0.5"], "Standalone dependencies");
if (!read("standalone/hooks/hook-tkinterdnd2.py").includes('collect_data_files("tkinterdnd2")')) {
  throw new Error("TkinterDnD2 PyInstaller hook is missing");
}

const workflow = read(".github/workflows/release.yml");
if ((workflow.match(/--collect-all rawpy/g) || []).length < 2) throw new Error("Both desktop packages must collect rawpy");
if ((workflow.match(/--additional-hooks-dir standalone\/hooks/g) || []).length < 2) throw new Error("Both desktop packages must use the TkDnD hook directory");
requireTokens(workflow, [
  "Verify RAW and drag-drop runtimes",
  "The macOS app does not contain TkDnD runtime files",
  "The Windows executable archive does not contain the native TkDnD runtime",
], "CI workflow");

const buildScript = read("scripts/build-release.sh");
requireTokens(buildScript, [
  "PS-Sezhao-Photoshop-v${VERSION}.ccx",
  "PS-Sezhao-Photoshop-Developer-v${VERSION}.zip",
  "unzip -Z1",
  'manifest.host?.minVersion !== "25.0.0"',
], "Release packaging");

console.log(`Validated PS-Sezhao ${version}: import fix, Explorer/Finder drag-drop, RAW, Lightroom and Photoshop workflows`);
