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
