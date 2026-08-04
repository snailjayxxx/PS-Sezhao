import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const root = path.resolve(process.cwd());
const plugin = path.join(root, "plugin");
const manifestPath = path.join(plugin, "manifest.json");
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
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
  "scripts/package-photoshop.ps1"
];

for (const file of requiredPluginFiles) {
  const filePath = path.join(plugin, file);
  if (!fs.existsSync(filePath)) throw new Error(`Missing Photoshop plugin file: ${file}`);
  if (fs.statSync(filePath).size === 0) throw new Error(`Empty Photoshop plugin file: ${file}`);
}
for (const file of requiredProjectFiles) {
  const filePath = path.join(root, file);
  if (!fs.existsSync(filePath)) throw new Error(`Missing unified project file: ${file}`);
  if (fs.statSync(filePath).size === 0) throw new Error(`Empty unified project file: ${file}`);
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
const lrInfo = fs.readFileSync(path.join(root, "lightroom-classic/PS-Sezhao.lrplugin/Info.lua"), "utf8");
const lrVersionPattern = new RegExp(`major\\s*=\\s*${major},\\s*minor\\s*=\\s*${minor},\\s*revision\\s*=\\s*${revision}`);
if (!lrVersionPattern.test(lrInfo)) throw new Error("Lightroom plugin version is stale");
const standaloneInit = fs.readFileSync(path.join(root, "standalone/ps_sezhao/__init__.py"), "utf8");
if (!standaloneInit.includes(`__version__ = "${version}"`)) throw new Error("Standalone version is stale");

for (const script of runtimeScripts) {
  const scriptPath = path.join(plugin, script);
  const source = fs.readFileSync(scriptPath, "utf8");
  if (/\btimeOut\s*:/.test(source)) {
    throw new Error(`${script} uses executeAsModal.timeOut, which requires Photoshop 25.10 and breaks early Photoshop 2024 releases`);
  }
  const result = spawnSync(process.execPath, ["--check", scriptPath], { encoding: "utf8" });
  if (result.status !== 0) throw new Error(`${script} syntax check failed:\n${result.stderr || result.stdout}`);
}

const packageScript = fs.readFileSync(path.join(root, "scripts/package-photoshop.ps1"), "utf8");
if (!/plugin\s+package/.test(packageScript)) throw new Error("Photoshop package script must call the Adobe UXP plugin package command");
if (!packageScript.includes("UXP_CLI_JS")) throw new Error("Photoshop package script must support the official Adobe source-built CLI entry point");
const workflow = fs.readFileSync(path.join(root, ".github/workflows/release.yml"), "utf8");
if (!workflow.includes("github.com/adobe-uxp/devtools-cli")) throw new Error("Release workflow must build the UXP CLI from Adobe's official repository");
if (!workflow.includes("yarn install --frozen-lockfile")) throw new Error("Release workflow must use Adobe's documented Yarn installation path");
const buildScript = fs.readFileSync(path.join(root, "scripts/build-release.sh"), "utf8");
if (!buildScript.includes("PS-Sezhao-Photoshop-Developer")) throw new Error("Developer-load package is missing from build script");

console.log(`Validated unified PS-Sezhao ${version} for Photoshop 2024+`);
