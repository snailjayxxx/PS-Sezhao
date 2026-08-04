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
  "standalone/ps_sezhao/app.py",
  "standalone/ps_sezhao/engine.py",
  "standalone/ps_sezhao/io_utils.py",
  "standalone/ps_sezhao/jobs.py",
  "standalone/ps_sezhao/processing.py"
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
if (manifest.host?.minVersion !== "27.8.0") throw new Error("Photoshop minVersion must target 27.8.0");
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

for (const script of runtimeScripts) {
  const result = spawnSync(process.execPath, ["--check", path.join(plugin, script)], { encoding: "utf8" });
  if (result.status !== 0) throw new Error(`${script} syntax check failed:\n${result.stderr || result.stdout}`);
}

console.log(`Validated unified PS-Sezhao ${version}`);
