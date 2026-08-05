import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const root = path.resolve(process.cwd());
const plugin = path.join(root, "plugin");
const lrPlugin = path.join(root, "lightroom-classic/PS-Sezhao.lrplugin");

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}
function requireFile(relativePath) {
  const filePath = path.join(root, relativePath);
  if (!fs.existsSync(filePath) || fs.statSync(filePath).size === 0) {
    throw new Error(`Missing or empty project file: ${relativePath}`);
  }
  return filePath;
}
function requireToken(source, token, message) {
  if (!source.includes(token)) throw new Error(message || `Missing token: ${token}`);
}

const version = read("VERSION").trim();
if (!/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(version)) {
  throw new Error(`VERSION is not a supported semantic version: ${version}`);
}
const coreVersion = version.split("-", 1)[0];
const prerelease = version.includes("-");
const [major, minor, revision] = coreVersion.split(".").map(Number);
const betaBuildMatch = version.match(/-beta\.(\d+)$/);
const expectedLrBuild = betaBuildMatch ? Number(betaBuildMatch[1]) : 0;

const packageJson = JSON.parse(read("package.json"));
const manifest = JSON.parse(read("plugin/manifest.json"));
if (packageJson.version !== version) {
  throw new Error(`package.json (${packageJson.version}) does not match VERSION (${version})`);
}
if (manifest.version !== coreVersion) {
  throw new Error(`Photoshop manifest (${manifest.version}) must use numeric core version ${coreVersion}`);
}
if (manifest.manifestVersion !== 5) throw new Error("manifestVersion must be 5");
if (manifest.host?.app !== "PS") throw new Error("host.app must be PS");
if (manifest.host?.minVersion !== "25.0.0") throw new Error("Photoshop minVersion must be 25.0.0");
if (!/^\d+\.\d+\.\d+$/.test(manifest.version)) {
  throw new Error("Photoshop manifest version must remain numeric x.y.z");
}
if (!manifest.entrypoints?.some((item) => item.type === "panel" && item.id === "sezhaoPanel")) {
  throw new Error("sezhaoPanel entrypoint is missing");
}

const requiredFiles = [
  "plugin/index.html",
  "plugin/styles.css",
  "plugin/runtime-v022.js",
  "plugin/runtime-final.js",
  "plugin/runtime-common.js",
  "plugin/runtime-engine-v053.js",
  "plugin/runtime-engine-style-v060.js",
  "plugin/runtime-style-v060.js",
  "plugin/runtime-history-v054.js",
  "plugin/runtime-controls-v050.js",
  "lightroom-classic/PS-Sezhao.lrplugin/Info.lua",
  "lightroom-classic/PS-Sezhao.lrplugin/ApplyNative.lua",
  "lightroom-classic/PS-Sezhao.lrplugin/NativeProfiles.lua",
  "lightroom-classic/PS-Sezhao.lrplugin/RestoreNative.lua",
  "lightroom-classic/PS-Sezhao.lrplugin/ProcessSelected.lua",
  "lightroom-classic/PS-Sezhao.lrplugin/PluginInfoProvider.lua",
  "standalone/main.py",
  "standalone/ps_sezhao/__init__.py",
  "standalone/ps_sezhao/bootstrap.py",
  "standalone/ps_sezhao/integration_groups.py",
  "standalone/ps_sezhao/services/lifecycle_facade.py",
  "standalone/ps_sezhao/services/proxy_service.py",
  "standalone/ps_sezhao/services/output_service.py",
  "standalone/ps_sezhao/services/project_session.py",
  "standalone/ps_sezhao/services/roll_project_pipeline.py",
  "standalone/ps_sezhao/storage/project_archive.py",
  "standalone/ps_sezhao/validation/real_roll.py",
  "scripts/validate-real-roll.py",
  "scripts/build-release.sh",
  "hook-tkinterdnd2.py",
  "docs/architecture-refactor-plan.md",
  "docs/project-archive-migration.md",
];
requiredFiles.forEach(requireFile);

const runtimeEntry = read("plugin/runtime-v022.js");
const runtimeFinal = read("plugin/runtime-final.js");
requireToken(runtimeEntry, `const VERSION = "${version}"`, "Photoshop panel version label is stale");
requireToken(runtimeFinal, `const VERSION = "${version}"`, "Photoshop output version label is stale");
for (const token of [
  'require("./runtime-engine-style-v060.js")',
  'require("./runtime-style-v060.js")',
  'require("./runtime-history-v054.js")',
  'require("./runtime-controls-v050.js")',
  "initializeNumericControls()",
  "history.initialize()",
]) {
  requireToken(runtimeEntry, token, `Photoshop runtime integration is missing: ${token}`);
}

const standaloneInit = read("standalone/ps_sezhao/__init__.py");
requireToken(standaloneInit, `__version__ = "${version}"`, "Standalone version is stale");
const standaloneMain = read("standalone/main.py");
requireToken(standaloneMain, "run_application", "Standalone launcher must call the unified entrypoint");
for (const forbidden of ["apply_patch", "apply_raw_patch", "app_v050_patch"] ) {
  if (standaloneMain.includes(forbidden)) throw new Error(`Standalone launcher still contains patch wiring: ${forbidden}`);
}

const bootstrap = read("standalone/ps_sezhao/bootstrap.py");
const groups = read("standalone/ps_sezhao/integration_groups.py");
const lifecycle = read("standalone/ps_sezhao/services/lifecycle_facade.py");
for (const stage of [
  "engine.processing",
  "runtime.bindings",
  "ui.compatibility",
  "services.processing",
  "services.persistence",
  "lifecycle.facade",
  "runtime.drag_drop_root",
]) {
  requireToken(bootstrap, `IntegrationStep("${stage}"`, `Missing integration stage: ${stage}`);
}
for (const method of [
  "__init__",
  "_build_ui",
  "_store_current_state",
  "load_index",
  "_save_project_session_now",
  "_restore_project_session",
  "_handle_export_event",
]) {
  requireToken(lifecycle, `"${method}"`, `Lifecycle facade is missing: ${method}`);
}
for (const installer of [
  "apply_v055_import_drop_patch",
  "apply_v061_resizable_layout_patch",
  "apply_proxy_pipeline",
  "apply_output_pipeline",
  "apply_complete_output_pipeline",
  "apply_project_session",
  "apply_roll_project_pipeline",
  "apply_project_archive_pipeline",
  "install_drag_drop_root",
]) {
  requireToken(groups, installer, `Grouped integration is missing: ${installer}`);
}

const lrInfo = read("lightroom-classic/PS-Sezhao.lrplugin/Info.lua");
const lrVersionPattern = new RegExp(
  `major\\s*=\\s*${major},\\s*minor\\s*=\\s*${minor},\\s*revision\\s*=\\s*${revision},\\s*build\\s*=\\s*${expectedLrBuild}`,
);
if (!lrVersionPattern.test(lrInfo)) throw new Error("Lightroom plugin version/build is stale");
const pluginInfo = read("lightroom-classic/PS-Sezhao.lrplugin/PluginInfoProvider.lua");
requireToken(pluginInfo, `PS-Sezhao ${version}`, "Lightroom information panel version is stale");
const nativeMenuIndex = lrInfo.indexOf("file = 'ApplyNative.lua'");
const tiffMenuIndex = lrInfo.indexOf("file = 'ProcessSelected.lua'");
if (nativeMenuIndex < 0 || tiffMenuIndex <= nativeMenuIndex) {
  throw new Error("Lightroom native mode must remain the first menu entry");
}
requireToken(lrInfo, "file = 'RestoreNative.lua'", "Lightroom native restore entry is missing");
const lrProcess = read("lightroom-classic/PS-Sezhao.lrplugin/ProcessSelected.lua");
requireToken(lrProcess, "LrFunctionContext.postAsyncTaskWithContext", "Lightroom export must be asynchronous");
requireToken(lrProcess, "LR_export_bitDepth = 16", "Lightroom high-precision export must remain 16-bit");

const requirements = read("standalone/requirements.txt");
requireToken(requirements, "rawpy>=0.27,<0.28", "rawpy dependency is missing or unpinned");
requireToken(requirements, "tkinterdnd2>=0.6.2,<0.7", "safe TkDND runtime dependency is missing");
const dragDropPatch = read("standalone/ps_sezhao/app_v055_import_drop_patch.py");
for (const token of ["DnDWrapper", "_ps_sezhao_dnd_available", "_ps_sezhao_dnd_error"]) {
  requireToken(dragDropPatch, token, `Drag-drop fallback is incomplete: ${token}`);
}

const javascriptFiles = fs.readdirSync(plugin)
  .filter((name) => name.endsWith(".js"))
  .map((name) => path.join(plugin, name));
for (const scriptPath of javascriptFiles) {
  const source = fs.readFileSync(scriptPath, "utf8");
  if (/\btimeOut\s*:/.test(source)) {
    throw new Error(`${path.basename(scriptPath)} uses unsupported executeAsModal.timeOut`);
  }
  const result = spawnSync(process.execPath, ["--check", scriptPath], { encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(`${path.basename(scriptPath)} syntax check failed:\n${result.stderr || result.stdout}`);
  }
}

const buildScript = read("scripts/build-release.sh");
for (const token of [
  "PS-Sezhao-Photoshop-v${VERSION}.ccx",
  "PS-Sezhao-Photoshop-Developer-v${VERSION}.zip",
  "PS-Sezhao-LightroomClassic-Source-v${VERSION}.zip",
  "unzip -Z1",
]) {
  requireToken(buildScript, token, `Release build is missing: ${token}`);
}
const workflow = read(".github/workflows/release.yml");
if ((workflow.match(/--collect-all rawpy/g) || []).length < 2) {
  throw new Error("Both desktop packages must collect rawpy/LibRaw binaries");
}
if ((workflow.match(/--collect-all tkinterdnd2/g) || []).length < 2) {
  throw new Error("Both desktop packages must collect the TkDND runtime");
}
requireToken(workflow, "--gui-smoke-test --require-dnd", "Packaged GUI smoke testing is missing");
requireToken(workflow, "--prerelease", "Prerelease publication handling is missing");
requireToken(workflow, "--latest=false", "Prerelease must not replace the latest stable release");

const architectureDocument = read("docs/architecture-refactor-plan.md");
const archiveDocument = read("docs/project-archive-migration.md");
for (const document of [architectureDocument, archiveDocument]) {
  if (document.includes("NexFilm")) throw new Error("Internal optimization documents contain an external project name");
}

if (prerelease && !version.includes("beta")) {
  throw new Error("The current prerelease channel must be explicitly identified as beta");
}
console.log(`Validated unified PS-Sezhao ${version} (${prerelease ? "prerelease" : "stable"})`);
