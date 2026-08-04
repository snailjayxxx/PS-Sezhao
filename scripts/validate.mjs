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
  "runtime-panel-preview.js",
  "runtime-sampler.js",
  "runtime-preview.js",
  "runtime-final.js",
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
  "standalone/main.py",
  "standalone/ps_sezhao/__init__.py",
  "standalone/ps_sezhao/app.py",
  "standalone/ps_sezhao/engine.py",
  "standalone/ps_sezhao/io_utils.py",
  "standalone/ps_sezhao/jobs.py",
  "standalone/ps_sezhao/processing.py",
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
if (!html.includes(`PS-SEZHAO · ${version}`)) throw new Error("index.html version label is stale");
if (!html.includes('src="runtime-v022.js"')) throw new Error("index.html must load runtime-v022.js");

const [major, minor, revision] = version.split(".").map(Number);
const lrInfo = fs.readFileSync(path.join(lrPlugin, "Info.lua"), "utf8");
const lrVersionPattern = new RegExp(`major\\s*=\\s*${major},\\s*minor\\s*=\\s*${minor},\\s*revision\\s*=\\s*${revision}`);
if (!lrVersionPattern.test(lrInfo)) throw new Error("Lightroom plugin version is stale");
if (!lrInfo.includes("file = 'ApplyNative.lua'")) throw new Error("Lightroom native mode must be the first release menu entry");
if (!lrInfo.includes("file = 'ProcessSelected.lua'")) throw new Error("Lightroom high-precision TIFF mode is missing");
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

for (const script of runtimeScripts) {
  const scriptPath = path.join(plugin, script);
  const source = fs.readFileSync(scriptPath, "utf8");
  if (/\btimeOut\s*:/.test(source)) {
    throw new Error(`${script} uses executeAsModal.timeOut, which breaks early Photoshop 2024 releases`);
  }
  const result = spawnSync(process.execPath, ["--check", scriptPath], { encoding: "utf8" });
  if (result.status !== 0) throw new Error(`${script} syntax check failed:\n${result.stderr || result.stdout}`);
}

const buildScript = fs.readFileSync(path.join(root, "scripts/build-release.sh"), "utf8");
if (!buildScript.includes("PS-Sezhao-Photoshop-v${VERSION}.ccx")) throw new Error("Photoshop CCX is missing from common release build");
if (!buildScript.includes("PS-Sezhao-Photoshop-Developer-v${VERSION}.zip")) throw new Error("Developer-load ZIP is missing from common release build");
if (!buildScript.includes("unzip -Z1")) throw new Error("CCX root structure validation is missing");
if (!buildScript.includes("manifest.host?.minVersion !== \"25.0.0\"")) throw new Error("CCX Photoshop 2024 validation is missing");

console.log(`Validated unified PS-Sezhao ${version} with Lightroom native and 16-bit TIFF modes`);
