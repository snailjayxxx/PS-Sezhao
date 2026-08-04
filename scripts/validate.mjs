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
const requiredFiles = ["manifest.json", "index.html", "styles.css", ...runtimeScripts];

for (const file of requiredFiles) {
  const filePath = path.join(plugin, file);
  if (!fs.existsSync(filePath)) throw new Error(`Missing plugin file: ${file}`);
  if (fs.statSync(filePath).size === 0) throw new Error(`Empty plugin file: ${file}`);
}

if (manifest.manifestVersion !== 5) throw new Error("manifestVersion must be 5");
if (manifest.host?.app !== "PS") throw new Error("host.app must be PS");
if (!/^\d+\.\d+\.\d+$/.test(manifest.version)) throw new Error("manifest.version must be semver x.y.z");
if (!manifest.entrypoints?.some((item) => item.type === "panel" && item.id === "sezhaoPanel")) {
  throw new Error("sezhaoPanel entrypoint is missing");
}

const version = fs.readFileSync(path.join(root, "VERSION"), "utf8").trim();
const packageJson = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
if (version !== manifest.version) throw new Error(`VERSION (${version}) does not match manifest (${manifest.version})`);
if (version !== packageJson.version) throw new Error(`VERSION (${version}) does not match package.json (${packageJson.version})`);

const html = fs.readFileSync(path.join(plugin, "index.html"), "utf8");
if (!html.includes('src="runtime-v022.js"')) {
  throw new Error("index.html must load runtime-v022.js");
}

for (const script of runtimeScripts) {
  const result = spawnSync(process.execPath, ["--check", path.join(plugin, script)], { encoding: "utf8" });
  if (result.status !== 0) throw new Error(`${script} syntax check failed:\n${result.stderr || result.stdout}`);
}

console.log(`Validated PS-Sezhao ${version}`);
