"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");
const assert = require("node:assert/strict");

const engine = require("../plugin/engine.js");
require("../plugin/runtime-engine-v053.js").apply(engine);
require("../plugin/runtime-engine-style-v060.js").apply(engine);

function controls(extra) {
  return Object.assign({
    exposure: 0,
    contrast: 1,
    gamma: 1,
    saturation: 1,
    temperature: 0,
    tint: 0,
    styleStrength: 1,
    scannerProfile: "neutral_lab",
    scannerStrength: 1,
    redGain: 1,
    greenGain: 1,
    blueGain: 1,
    blackPoint: 0,
    whitePoint: 0,
    shadows: 0,
    highlights: 0,
    baseAdjust: [0, 0, 0]
  }, extra || {});
}

test("v0.6.0 exposes scanner and film libraries independently", function () {
  assert.equal(engine.SCANNER_PROFILE_ORDER.length, 6);
  assert.equal(engine.FILM_PROFILE_ORDER.length, 16);
  assert.match(engine.SCANNER_PROFILES.hasselblad_flextight_x5.label, /Hasselblad Flextight X5/);
  assert.match(engine.FILM_PROFILES.kodak_portra_400.label, /Kodak Portra 400/);

  const analysis = { base: [0.92, 0.64, 0.38], black: [0, 0, 0], white: [1.25, 1.20, 1.15] };
  const input = new Uint8Array([107, 71, 41]);
  const neutral = engine.processBuffer(input, 1, 1, 3, 8, analysis, controls(), "generic", true);
  const scanner = engine.processBuffer(
    input,
    1,
    1,
    3,
    8,
    analysis,
    controls({ scannerProfile: "hasselblad_flextight_x5" }),
    "generic",
    true
  );
  const film = engine.processBuffer(input, 1, 1, 3, 8, analysis, controls(), "kodak_portra_400", true);
  assert.notDeepEqual(Array.from(neutral), Array.from(scanner));
  assert.notDeepEqual(Array.from(neutral), Array.from(film));
  assert.notDeepEqual(Array.from(scanner), Array.from(film));
});

test("legacy film profile names migrate to popular canonical names", function () {
  assert.equal(engine.canonicalFilmProfile("portra"), "kodak_portra_400");
  assert.equal(engine.canonicalFilmProfile("gold"), "kodak_gold_200");
  assert.equal(engine.canonicalFilmProfile("fuji"), "fujifilm_superia_400");
  assert.equal(engine.canonicalFilmProfile("ecn2"), "kodak_vision3_250d");
});

test("Photoshop style runtime files are syntax-valid and wired into the panel", function () {
  const root = path.resolve(__dirname, "..");
  for (const file of ["runtime-engine-style-v060.js", "runtime-style-v060.js"]) {
    const filePath = path.join(root, "plugin", file);
    const result = spawnSync(process.execPath, ["--check", filePath], { encoding: "utf8" });
    assert.equal(result.status, 0, result.stderr || result.stdout);
  }
  const entry = fs.readFileSync(path.join(root, "plugin/runtime-v022.js"), "utf8");
  const html = fs.readFileSync(path.join(root, "plugin/index.html"), "utf8");
  assert.match(entry, /runtime-engine-style-v060/);
  assert.match(entry, /runtime-style-v060/);
  assert.match(html, /id="scannerProfile"/);
  assert.match(html, /Hasselblad Flextight X5/);
  assert.match(html, /Kodak Portra 400/);
  assert.match(html, /非官方风格参考/);
});
