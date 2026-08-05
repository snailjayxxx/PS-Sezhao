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

const VERSION = "0.7.0-beta.2";
const V022_UI_IDS = [
  "pickBase", "pickNeutral", "cancelPicker", "sampleSize",
  "panelPreviewStage", "panelPreviewImage", "panelPreviewPlaceholder",
  "panelPreviewMessage", "panelPreviewZoom", "panelPreviewExpand",
  "undoEdit", "redoEdit", "resetNeutralGains"
];

function bindClick(id, handler) { byId(id).addEventListener("click", handler); }
function bindRange(id) { byId(id).addEventListener("input", function () { refreshOutputs(); history.record("control", id); schedulePreview(false); }); }

function initializeNumericControls() {
  numericControls.initialize({
    byId,
    adjustmentIds: ADJUSTMENT_IDS,
    onCommit: function (id) {
      refreshOutputs();
      history.record("control", id);
      schedulePreview(false);
    }
  });
}

function initializePanel() {
  for (const id of [...REQUIRED_UI_IDS, ...V022_UI_IDS]) byId(id);
  bindClick("analyze", preview.analyze);
  bindClick("pickBase", function () { sampler.startPicker("base"); });
  bindClick("pickNeutral", function () { sampler.startPicker("neutral"); });
  bindClick("cancelPicker", sampler.cancelPicker);
  bindClick("render", finalOps.convert);
  bindClick("reset", function () {
    resetControls(DEFAULT_CONTROLS);
    history.record("reset", "reset", true);
    schedulePreview(false);
  });
  bindClick("undoEdit", history.undo);
  bindClick("redoEdit", history.redo);
  bindClick("resetNeutralGains", history.resetNeutralGains);
  byId("sampleSize").addEventListener("change", function () { sampler.updateSampleSize(); });
  byId("panelPreviewStage").addEventListener("click", sampler.handlePanelPreviewClick);
  byId("panelPreviewZoom").addEventListener("input", panelPreview.updateZoomFromControl);
  bindClick("panelPreviewExpand", panelPreview.toggleExpanded);
  for (const id of ADJUSTMENT_IDS) bindRange(id);
  initializeNumericControls();
  history.initialize();
  panelPreview.initialize();
  sampler.initialize();
  updateReadiness();
  setStatus("请选择一个负片图层，然后点击分析。", "info");
}

entrypoints.setup({
  panels: {
    sezhaoPanel: {
      create() {
        initializePanel();
        return byId("panelRoot");
      },
      show() { updateReadiness(); },
      hide() { sampler.cancelPicker(); }
    }
  }
});

module.exports = { initializePanel, VERSION };
