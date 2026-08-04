"use strict";

const { entrypoints } = require("uxp");
const c = require("./runtime-common.js");
const preview = require("./runtime-preview.js");
const finalOps = require("./runtime-final.js");
const {
  state, byId, ADJUSTMENT_IDS, REQUIRED_UI_IDS, DEFAULT_CONTROLS,
  applyControls, refreshOutputs, updateReadiness, setStatus,
  schedulePreview, resetControls
} = c;

function bindClick(id, handler) { byId(id).addEventListener("click", handler); }
function onAdjustmentInput() {
  refreshOutputs();
  schedulePreview();
}
function onAdjustmentChange() {
  refreshOutputs();
  schedulePreview(0);
}
function initializeUI() {
  if (state.initialized) return true;
  const missing = REQUIRED_UI_IDS.filter(function (id) { return !byId(id); });
  if (missing.length) return false;
  state.initialized = true;

  ADJUSTMENT_IDS.forEach(function (id) {
    byId(id).addEventListener("input", onAdjustmentInput);
    byId(id).addEventListener("change", onAdjustmentChange);
  });
  byId("profile").addEventListener("change", onAdjustmentChange);
  byId("previewEdge").addEventListener("change", function () {
    state.previewCache = null;
    state.previewGeometryKey = null;
    schedulePreview(0);
  });
  byId("autoPreview").addEventListener("change", function () {
    if (byId("autoPreview").checked) {
      setStatus("自动预览已开启，正在同步。", "ok");
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
  bindClick("reset", resetControls);
  bindClick("saveRoll", finalOps.saveRoll);
  bindClick("loadRoll", finalOps.loadRoll);

  applyControls(DEFAULT_CONTROLS);
  refreshOutputs();
  updateReadiness();
  setStatus("准备就绪。请先分析胶片基底。");
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
