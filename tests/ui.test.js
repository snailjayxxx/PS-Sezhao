"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "plugin/index.html"), "utf8");
const css = fs.readFileSync(path.join(root, "plugin/styles.css"), "utf8");
const main = fs.readFileSync(path.join(root, "plugin/main.js"), "utf8");

test("UXP panel uses a bounded scroll container", function () {
  assert.match(html, /class="panel-scroll"/);
  assert.match(css, /\.panel-scroll\s*\{[^}]*overflow-y:\s*auto/s);
  assert.match(css, /\.panel-shell\s*\{[^}]*height:\s*100%/s);
});

test("button rows use UXP-supported flex layout instead of CSS grid", function () {
  assert.doesNotMatch(css, /display:\s*grid/);
  assert.match(css, /\.button-grid\s*\{[^}]*display:\s*flex/s);
  assert.match(html, /id="analyzeAuto"/);
  assert.match(html, /id="analyzeSelection"/);
});

test("generation feedback remains outside the scrolling content", function () {
  const scrollEnd = html.indexOf("</div>\n\n    <section class=\"action-dock\"");
  assert.ok(scrollEnd > 0, "action dock should follow the scroll container");
  assert.match(html, /id="status"/);
  assert.match(html, /id="readinessValue"/);
});

test("UI initialization is retryable and prerequisite errors are visible", function () {
  assert.match(main, /function scheduleInitialize\(/);
  assert.match(main, /app\.showAlert\(message\)/);
  assert.match(main, /请先点击“自动分析边框”/);
});

test("Photoshop pixel analysis runs inside executeAsModal", function () {
  const analyzeStart = main.indexOf("async function analyze(useSelection)");
  const validateStart = main.indexOf("function validateAnalysisSource", analyzeStart);
  assert.ok(analyzeStart >= 0 && validateStart > analyzeStart, "analyze function should exist");
  const analyzeSource = main.slice(analyzeStart, validateStart);
  assert.match(analyzeSource, /core\.executeAsModal\(/);
  assert.match(analyzeSource, /preview\s*=\s*await getPreview\(source\)/);
  assert.match(analyzeSource, /await imaging\.getSelection\(/);
  assert.ok(
    analyzeSource.indexOf("core.executeAsModal(") < analyzeSource.indexOf("preview = await getPreview(source)"),
    "getPixels must be reached only after entering the modal scope"
  );
  assert.match(analyzeSource, /timeOut:\s*10/);
});

test("busy labels distinguish analysis from conversion", function () {
  assert.match(main, /setBusy\(true, "analyze"\)/);
  assert.match(main, /setBusy\(true, "convert"\)/);
  assert.match(main, /正在分析胶片基底/);
  assert.match(main, /正在生成正片/);
});
