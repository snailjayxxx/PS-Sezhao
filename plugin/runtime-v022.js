"use strict";

const { entrypoints } = require("uxp");
const c = require("./runtime-common.js");
require("./runtime-engine-v053.js").apply(c.engine);
require("./runtime-engine-style-v060.js").apply(c.engine);
const styleLibrary = require("./runtime-style-v060.js");
styleLibrary.applyCommon(c);
const history = require("./runtime-history-v054.js");
history.applyCommon(c);
const preview = require("./runtime-preview.js");
const finalOps = require("./runtime-final.js");
const panelPreview = require("./runtime-panel-preview.js");
const sampler = require("./runtime-sampler.js");
const numericControls = require("./runtime-controls-v050.js");
const {
  state, byId, ADJUSTMENT_IDS, REQUIRED_UI_IDS, DEFAULT_CONTROLS,
  applyControls, refreshOutputs, updateReadiness, setStatus,
  schedulePreview, resetControls
} = c;

const VERSION = "0.7.0-beta.3";
const V022_UI_IDS = [
  "pickBase", "pickNeutral", "cancelPicker", "sampleSize",
  "panelPreviewStage", "panelPreviewImage", "panelPreviewPlaceholder",
  "panelPreviewMessage", "panelPreviewZoom", "panelPreviewExpand",
  "undoEdit", "redoEdit", "resetNeutralGains"
];

function bindClick(id, handler) { byId(id).addEventListener("click", handler); }
function onAdjustmentInput() {
  refreshOutputs();
  styleLibrary.refreshDescription(c);
  schedulePreview();
  history.record("control", false);
}
function onAdjustmentChange() {
  refreshOutputs();
  styleLibrary.refreshDescription(c);
  schedulePreview(0);
  history.record("control", true);
}
function updateVersionLabels() {
  const eyebrow = document.querySelector(".eyebrow");
  const badge = document.querySelector(".badge");
  if (eyebrow) eyebrow.textContent = "PS-SEZHAO · " + VERSION;
  if (badge) badge.textContent = "BETA";
}
function configureDirectBaseRanges() {
  ["baseAdjustR", "baseAdjustG", "baseAdjustB"].forEach(function (id) {
    const range = byId(id);
    if (!range) return;
    range.min = "0";
    range.max = "255";
    range.step = "1";
  });
}
function initializeUI() {
  if (state.initialized) return true;
  const missing = REQUIRED_UI_IDS.concat(V022_UI_IDS).filter(function (id) { return !byId(id); });
  if (missing.length) return false;
  state.initialized = true;

  ADJUSTMENT_IDS.forEach(function (id) {
    byId(id).addEventListener("input", onAdjustmentInput);
    byId(id).addEventListener("change", onAdjustmentChange);
  });
  ["profile", "scannerProfile"].forEach(function (id) {
    byId(id).addEventListener("change", function () {
      styleLibrary.refreshDescription(c);
      onAdjustmentChange();
    });
  });
  byId("previewEdge").addEventListener("change", function () {
    state.previewCache = null;
    state.previewGeometryKey = null;
    schedulePreview(0);
  });
  byId("autoPreview").addEventListener("change", function () {
    if (byId("autoPreview").checked) {
      setStatus("自动预览已开启，正在同步画布和大图预览。", "ok");
      schedulePreview(0);
    } else {
      setStatus("自动预览已关闭，可点击“立即刷新预览”。");
    }
  });
  byId("borderFraction").addEventListener("input", refreshOutputs);

  bindClick("analyzeAuto", function () { preview.analyze(false); });
  bindClick("analyzeSelection", function () { preview.analyze(true); });
  bindClick("neutralizeSelection", preview.neutralizeSelection);
  bindClick("refreshPreview", function () { preview.renderPreview(true); });
  bindClick("togglePreview", preview.togglePreview);
  bindClick("removePreview", function () { preview.removePreview(true); });
  bindClick("convert", finalOps.convert);
  bindClick("reset", function () {
    resetControls();
    history.record("reset", true);
  });
  bindClick("saveRoll", finalOps.saveRoll);
  bindClick("loadRoll", finalOps.loadRoll);

  updateVersionLabels();
  configureDirectBaseRanges();
  numericControls.initializeNumericControls();
  panelPreview.initialize();
  sampler.initialize();
  styleLibrary.initializeUI(c);
  applyControls(DEFAULT_CONTROLS);
  refreshOutputs();
  history.initialize();
  updateReadiness();
  setStatus("Beta 版准备就绪。扫描仪风格与胶卷风格可独立选择和调整强度。", "");
  return true;
}
function scheduleInitialize() {
  if (initializeUI()) {
    if (state.initTimer) clearTimeout(state.initTimer);
    state.initTimer = null;
    return;
  }
  if (!state.initTimer) {
    state.initTimer = setTimeout(function () {
      state.initTimer = null;
      scheduleInitialize();
    }, 50);
  }
}

entrypoints.setup({
  panels: {
    sezhaoPanel: {
      show: function () { scheduleInitialize(); }
    }
  }
});

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", scheduleInitialize);
} else {
  scheduleInitialize();
}
