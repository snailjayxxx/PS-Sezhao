import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const root = path.resolve(process.cwd());
const plugin = path.join(root, "plugin");

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
  throw new Error(`Unsupported VERSION: ${version}`);
}
const coreVersion = version.split("-", 1)[0];
const prerelease = version.includes("-");
const [major, minor, revision] = coreVersion.split(".").map(Number);
const betaBuildMatch = version.match(/-beta\.(\d+)$/);
const expectedLrBuild = betaBuildMatch ? Number(betaBuildMatch[1]) : 0;

const packageJson = JSON.parse(read("package.json"));
const manifest = JSON.parse(read("plugin/manifest.json"));
if (packageJson.version !== version) throw new Error("package.json version is stale");
if (manifest.version !== coreVersion) throw new Error("Photoshop manifest must use the numeric core version");
if (manifest.manifestVersion !== 5 || manifest.host?.app !== "PS") throw new Error("Photoshop manifest is invalid");
if (manifest.host?.minVersion !== "25.0.0") throw new Error("Photoshop minimum version is invalid");
if (!manifest.entrypoints?.some((item) => item.type === "panel" && item.id === "sezhaoPanel")) {
  throw new Error("Photoshop panel entrypoint is missing");
}

const activeRuntimeFiles = [
  "engine.js",
  "runtime-common.js",
  "runtime-engine-v053.js",
  "runtime-engine-style-v060.js",
  "runtime-style-v060.js",
  "runtime-history-v054.js",
  "runtime-panel-preview.js",
  "runtime-sampler.js",
  "runtime-preview.js",
  "runtime-final.js",
  "runtime-controls-v050.js",
  "runtime-v022.js",
];
const requiredFiles = [
  "plugin/manifest.json",
  "plugin/index.html",
  "plugin/styles.css",
  ...activeRuntimeFiles.map((name) => `plugin/${name}`),
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
  "standalone/ps_sezhao/app_v071_text_layout_patch.py",
  "standalone/ps_sezhao/app_v072_workspace_lut_layout_patch.py",
  "standalone/ps_sezhao/app_v072_responsive_group_patch.py",
  "standalone/ps_sezhao/app_v073_style_status_patch.py",
  "standalone/ps_sezhao/engine_lut_v072_patch.py",
  "standalone/ps_sezhao/core/lut.py",
  "standalone/ps_sezhao/services/lifecycle_facade.py",
  "standalone/ps_sezhao/services/proxy_service.py",
  "standalone/ps_sezhao/services/output_service.py",
  "standalone/ps_sezhao/services/project_session.py",
  "standalone/ps_sezhao/services/roll_project_pipeline.py",
  "standalone/ps_sezhao/services/startup_close_policy.py",
  "standalone/ps_sezhao/storage/paths.py",
  "standalone/ps_sezhao/storage/project_archive.py",
  "standalone/ps_sezhao/validation/real_roll.py",
  "standalone/tests/test_text_layout_v071.py",
  "standalone/tests/test_lut_paths_v072.py",
  "standalone/tests/test_ui_layout_v072.py",
  "standalone/tests/test_startup_close_policy_v073.py",
  "standalone/installer/INSTALL.zh-CN.html",
  "standalone/installer/PS-Sezhao.iss",
  "scripts/validate-real-roll.py",
  "scripts/build-release.sh",
  "scripts/build-macos-release.sh",
  "hook-tkinterdnd2.py",
  "docs/architecture-refactor-plan.md",
  "docs/project-archive-migration.md",
];
requiredFiles.forEach(requireFile);

const runtimeEntry = read("plugin/runtime-v022.js");
const runtimeFinal = read("plugin/runtime-final.js");
requireToken(runtimeEntry, `const VERSION = "${version}"`, "Photoshop panel version is stale");
requireToken(runtimeFinal, `const VERSION = "${version}"`, "Photoshop output version is stale");
for (const token of [
  'require("./runtime-engine-style-v060.js")',
  'require("./runtime-style-v060.js")',
  'require("./runtime-history-v054.js")',
  'require("./runtime-controls-v050.js")',
  "initializeNumericControls()",
  "history.initialize()",
]) requireToken(runtimeEntry, token, `Photoshop integration is missing: ${token}`);

for (const name of activeRuntimeFiles) {
  const scriptPath = path.join(plugin, name);
  const source = fs.readFileSync(scriptPath, "utf8");
  if (/\btimeOut\s*:/.test(source)) throw new Error(`${name} uses unsupported executeAsModal.timeOut`);
  const result = spawnSync(process.execPath, ["--check", scriptPath], { encoding: "utf8" });
  if (result.status !== 0) throw new Error(`${name} syntax check failed:\n${result.stderr || result.stdout}`);
}

const standaloneInit = read("standalone/ps_sezhao/__init__.py");
requireToken(standaloneInit, `__version__ = "${version}"`, "Standalone version is stale");
const standaloneMain = read("standalone/main.py");
requireToken(standaloneMain, "run_application", "Standalone launcher must use the unified entrypoint");
for (const forbidden of ["apply_patch", "apply_raw_patch", "app_v050_patch"]) {
  if (standaloneMain.includes(forbidden)) throw new Error(`Standalone launcher still wires a patch: ${forbidden}`);
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
]) requireToken(bootstrap, `IntegrationStep("${stage}"`, `Missing integration stage: ${stage}`);
for (const method of [
  "__init__",
  "_build_ui",
  "_store_current_state",
  "load_index",
  "_save_project_session_now",
  "_restore_project_session",
  "_handle_export_event",
]) requireToken(lifecycle, `"${method}"`, `Lifecycle facade is missing: ${method}`);
for (const installer of [
  "apply_v055_import_drop_patch",
  "apply_v061_resizable_layout_patch",
  "apply_v071_text_layout_patch",
  "apply_v072_workspace_lut_layout_patch",
  "apply_v072_responsive_group_patch",
  "apply_v073_style_status_patch",
  "apply_user_lut_engine_patch",
  "apply_proxy_pipeline",
  "apply_output_pipeline",
  "apply_complete_output_pipeline",
  "apply_project_session",
  "apply_roll_project_pipeline",
  "apply_startup_close_policy",
  "apply_project_archive_pipeline",
  "install_drag_drop_root",
]) requireToken(groups, installer, `Grouped integration is missing: ${installer}`);

const styleStatus = read("standalone/ps_sezhao/app_v073_style_status_patch.py");
for (const token of [
  "_v073_open_style_popup",
  "style_library_frame",
  "pane_width",
  "rotation_status",
  "crop_status",
  "geometry_status",
]) requireToken(styleStatus, token, `Beta 4 style/status UI is incomplete: ${token}`);

const startupClose = read("standalone/ps_sezhao/services/startup_close_policy.py");
for (const token of [
  "askyesnocancel",
  "clear_workspace",
  "set_active_project(None)",
  "_save_temporary_roll_for_close",
  "WM_DELETE_WINDOW",
]) requireToken(startupClose, token, `Startup/close policy is incomplete: ${token}`);

const lutCore = read("standalone/ps_sezhao/core/lut.py");
for (const token of ["LUT_1D_SIZE", "LUT_3D_SIZE", "DOMAIN_MIN", "DOMAIN_MAX", "_apply_3d", "apply_cube_lut"]) {
  requireToken(lutCore, token, `Cube LUT core is incomplete: ${token}`);
}
const lutEngine = read("standalone/ps_sezhao/engine_lut_v072_patch.py");
for (const token of ['payload["user_lut"]', "resolve_user_lut", "apply_cube_lut", "processing.process_image = process_image"]) {
  requireToken(lutEngine, token, `User LUT engine integration is incomplete: ${token}`);
}

const storagePaths = read("standalone/ps_sezhao/storage/paths.py");
for (const token of [
  'PROJECT_DIRECTORY_NAME = "project"',
  'LUT_DIRECTORY_NAME = "lut"',
  'PORTABLE_MARKER = ".ps-sezhao-portable"',
  "_uses_macos_application_support_layout",
  "Application Support",
  "legacy_project_database_path",
]) requireToken(storagePaths, token, `Project storage is incomplete: ${token}`);

const lrInfo = read("lightroom-classic/PS-Sezhao.lrplugin/Info.lua");
const lrVersionPattern = new RegExp(
  `major\\s*=\\s*${major},\\s*minor\\s*=\\s*${minor},\\s*revision\\s*=\\s*${revision},\\s*build\\s*=\\s*${expectedLrBuild}`,
);
if (!lrVersionPattern.test(lrInfo)) throw new Error("Lightroom version/build is stale");
requireToken(read("lightroom-classic/PS-Sezhao.lrplugin/PluginInfoProvider.lua"), `PS-Sezhao ${version}`, "Lightroom info version is stale");
const lrProcess = read("lightroom-classic/PS-Sezhao.lrplugin/ProcessSelected.lua");
requireToken(lrProcess, "LrFunctionContext.postAsyncTaskWithContext", "Lightroom export must be asynchronous");
requireToken(lrProcess, "LR_export_bitDepth = 16", "Lightroom high-precision export must remain 16-bit");

const requirements = read("standalone/requirements.txt");
requireToken(requirements, "rawpy>=0.27,<0.28", "rawpy dependency is missing");
requireToken(requirements, "tkinterdnd2>=0.6.2,<0.7", "TkDND dependency is missing");
const dragDropPatch = read("standalone/ps_sezhao/app_v055_import_drop_patch.py");
for (const token of ["DnDWrapper", "_ps_sezhao_dnd_available", "_ps_sezhao_dnd_error"]) {
  requireToken(dragDropPatch, token, `Drag-drop fallback is incomplete: ${token}`);
}

const buildScript = read("scripts/build-release.sh");
for (const token of [
  "PS-Sezhao-Photoshop-v${VERSION}.ccx",
  "PS-Sezhao-Photoshop-Developer-v${VERSION}.zip",
  "PS-Sezhao-LightroomClassic-Source-v${VERSION}.zip",
  "unzip -Z1",
]) requireToken(buildScript, token, `Release build is missing: ${token}`);

const macBuildScript = read("scripts/build-macos-release.sh");
for (const token of [
  "APPLE_CERTIFICATE_P12_BASE64",
  "codesign --force --deep --options runtime",
  "xcrun notarytool submit",
  "xcrun stapler staple",
  "ln -s /Applications",
  "The macOS build will remain unsigned",
]) requireToken(macBuildScript, token, `macOS release/signing flow is incomplete: ${token}`);

const workflow = read(".github/workflows/release.yml");
if ((workflow.match(/--collect-all rawpy/g) || []).length < 2) throw new Error("Both desktop packages must collect rawpy");
if ((workflow.match(/--collect-all tkinterdnd2/g) || []).length < 2) throw new Error("Both desktop packages must collect TkDND");
for (const token of [
  "--gui-smoke-test --require-dnd",
  "bash scripts/build-macos-release.sh",
  "APPLE_CERTIFICATE_P12_BASE64",
  "test -L dmg-stage/Applications",
  "test ! -e dmg-stage/安装到用户应用程序.command",
  "PS-Sezhao-Installer-Windows-x64-v$version.exe",
  "choco install innosetup",
  "PS-Sezhao.iss",
  "portable-stage/PS-Sezhao/project",
  "portable-stage/PS-Sezhao/lut",
  "Installed Windows GUI smoke test",
  "--prerelease",
  "--latest=false",
]) requireToken(workflow, token, `Release workflow is missing: ${token}`);

const installHtml = read("standalone/installer/INSTALL.zh-CN.html");
for (const token of [
  "Applications",
  "Library/Application Support/PS-Sezhao/workspace.sqlite3",
  "%LOCALAPPDATA%\\Programs\\PS-Sezhao\\",
  "是否保存本次胶卷项目",
  ".cube",
]) requireToken(installHtml, token, `Installation documentation is incomplete: ${token}`);

const innoSetup = read("standalone/installer/PS-Sezhao.iss");
for (const token of ["PrivilegesRequired=lowest", "{localappdata}\\Programs\\PS-Sezhao", "uninsneveruninstall", ".ps-sezhao-portable"]) {
  requireToken(innoSetup, token, `Windows installer is incomplete: ${token}`);
}

for (const document of [read("docs/architecture-refactor-plan.md"), read("docs/project-archive-migration.md")]) {
  if (document.includes("NexFilm")) throw new Error("Internal documents contain an external project name");
}
if (prerelease && !version.includes("beta")) throw new Error("Prerelease must be identified as beta");
console.log(`Validated unified PS-Sezhao ${version} (${prerelease ? "prerelease" : "stable"})`);
