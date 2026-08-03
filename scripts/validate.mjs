import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd());
const plugin = path.join(root, "plugin");
const manifestPath = path.join(plugin, "manifest.json");
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const requiredFiles = ["manifest.json", "index.html", "styles.css", "main.js", "engine.js"];

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
if (version !== manifest.version) throw new Error(`VERSION (${version}) does not match manifest (${manifest.version})`);
console.log(`Validated PS-Sezhao ${version}`);
