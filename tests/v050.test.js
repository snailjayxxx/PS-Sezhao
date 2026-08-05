"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const main = fs.readFileSync(path.join(root, "standalone/main.py"), "utf8");
const groups = fs.readFileSync(path.join(root, "standalone/ps_sezhao/integration_groups.py"), "utf8");
const patch = fs.readFileSync(path.join(root, "standalone/ps_sezhao/app_v050_patch.py"), "utf8");
const jobs = fs.readFileSync(path.join(root, "standalone/ps_sezhao/jobs.py"), "utf8");
const numeric = fs.readFileSync(path.join(root, "plugin/runtime-controls-v050.js"), "utf8");

test("standalone unified launcher installs the v0.5.0 compatibility layer", function () {
  assert.match(main, /from ps_sezhao\.bootstrap import run_application/);
  assert.doesNotMatch(main, /app_v050_patch/);
  assert.match(groups, /from \.app_v050_patch import apply_patch/);
  assert.match(groups, /apply_patch\(app_class\)/);
  assert.match(patch, /crop_dragged/);
  assert.match(patch, /self\.crop_norm = getattr\(self, "crop_before_drag"/);
});

test("Lightroom high precision job serializes and consumes per-photo settings", function () {
  assert.match(patch, /job_item\["analysis"\]/);
  assert.match(patch, /job_item\["controls"\]/);
  assert.match(patch, /job_item\["crop"\]/);
  assert.match(jobs, /item\.get\("analysis", default_analysis\)/);
  assert.match(jobs, /item\.get\("controls"\)/);
  assert.match(jobs, /item\.get\("crop", default_crop\)/);
});

test("Photoshop numeric input remains UXP-compatible and idempotent", function () {
  assert.match(numeric, /getAttribute\("data-numeric-enhanced"\)/);
  assert.match(numeric, /parentNode\.insertBefore/);
  assert.match(numeric, /setAttribute\("data-numeric-enhanced", "true"\)/);
  assert.match(numeric, /input\.type = "text"/);
  assert.match(numeric, /inputmode/);
});
