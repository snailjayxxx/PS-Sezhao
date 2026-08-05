"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const main = fs.readFileSync(path.join(root, "standalone/main.py"), "utf8");
const patch = fs.readFileSync(path.join(root, "standalone/ps_sezhao/app_v055_import_drop_patch.py"), "utf8");
const workflow = fs.readFileSync(path.join(root, ".github/workflows/release.yml"), "utf8");
const hook = fs.readFileSync(path.join(root, "standalone/hooks/hook-tkinterdnd2.py"), "utf8");
const requirements = fs.readFileSync(path.join(root, "standalone/requirements.txt"), "utf8");

test("v0.5.5 repairs the v0.5.4 history method aliases before importing files", function () {
  assert.match(main, /apply_v054_patch\(app_module\.SezhaoApp\)/);
  assert.match(main, /apply_v055_import_drop_patch\(app_module\.SezhaoApp\)/);
  assert.ok(main.indexOf("apply_v054_patch") < main.indexOf("apply_v055_import_drop_patch"));
  assert.match(patch, /\("history_for", "_history_for"\)/);
  assert.match(patch, /setattr\(app_class, public_name, getattr\(app_class, internal_name\)\)/);
});

test("desktop drag and drop accepts Explorer and Finder files or folders", function () {
  assert.match(main, /install_drag_drop_root\(app_module\)/);
  assert.match(patch, /TkinterDnD\.Tk/);
  assert.match(patch, /drop_target_register\(DND_FILES\)/);
  assert.match(patch, /dnd_bind\("<<Drop>>"/);
  assert.match(patch, /root\.tk\.splitlist/);
  assert.match(patch, /path\.rglob\("\*"\)/);
  assert.match(patch, /self\.open_paths\(unique\)/);
});

test("release packages include the native TkDnD runtime", function () {
  assert.match(requirements, /tkinterdnd2/);
  assert.match(hook, /collect_data_files\("tkinterdnd2"\)/);
  assert.equal((workflow.match(/--additional-hooks-dir standalone\/hooks/g) || []).length, 2);
  assert.match(workflow, /The macOS app does not contain TkDnD runtime files/);
  assert.match(workflow, /The Windows executable archive does not contain the native TkDnD runtime/);
});
