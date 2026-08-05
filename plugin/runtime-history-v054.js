"use strict";

let c = null;
let undoItems = [];
let redoItems = [];
let restoring = false;
let lastKind = "";
let lastTime = 0;
let lastAnalysisSignature = "";
const LIMIT = 60;

function clone(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}

function same(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

function analysisSignature() {
  if (!c || !c.state.analysis || !Array.isArray(c.state.analysis.base)) return "";
  return JSON.stringify({
    base: c.state.analysis.base,
    black: c.state.analysis.black,
    white: c.state.analysis.white,
    method: c.state.analysis.method,
    sourceDocumentId: c.state.sourceDocumentId,
    sourceLayerId: c.state.sourceLayerId
  });
}

function directBaseValue(index) {
  const id = ["baseAdjustR", "baseAdjustG", "baseAdjustB"][index];
  const input = c.byId(id);
  return input ? Number(input.value) / 255 : 0;
}

function ensureUi() {
  if (typeof document === "undefined") return;

  let undo = document.getElementById("undoEdit");
  let redo = document.getElementById("redoEdit");
  const actionMeta = document.querySelector(".action-meta");
  if (actionMeta && !undo) {
    undo = document.createElement("button");
    undo.id = "undoEdit";
    undo.className = "reset-button";
    undo.textContent = "↶ 撤销";
    actionMeta.insertBefore(undo, actionMeta.firstChild);
  }
  if (actionMeta && !redo) {
    redo = document.createElement("button");
    redo.id = "redoEdit";
    redo.className = "reset-button";
    redo.textContent = "↷ 重做";
    if (undo && undo.nextSibling) actionMeta.insertBefore(redo, undo.nextSibling);
    else actionMeta.insertBefore(redo, actionMeta.firstChild);
  }

  const colorCard = document.querySelector(".color-card");
  if (colorCard) {
    const heading = colorCard.querySelector("h2");
    if (heading) heading.textContent = "5. 中性灰校正与色彩";
    const microcopy = colorCard.querySelector(".microcopy");
    if (microcopy) {
      microcopy.textContent = "中性灰吸管修改的是下方红、绿、蓝输出增益；1.00 表示不校正，这三个数值可以继续手动修改。";
    }
    let resetNeutral = document.getElementById("resetNeutralGains");
    if (!resetNeutral) {
      resetNeutral = document.createElement("button");
      resetNeutral.id = "resetNeutralGains";
      resetNeutral.textContent = "中性灰增益恢复 1.00";
      const row = colorCard.querySelector(".button-row.single-action");
      if (row) row.appendChild(resetNeutral);
      else colorCard.appendChild(resetNeutral);
    }
  }

  const headings = document.querySelectorAll(".card h2");
  for (let index = 0; index < headings.length; index++) {
    const heading = headings[index];
    if (String(heading.textContent).indexOf("7. 胶片基底") === 0) {
      heading.textContent = "7. 胶片基底（直接 R/G/B）";
      const card = heading.parentElement;
      const copy = card && card.querySelector(".microcopy");
      if (copy) copy.textContent = "这里直接填写最终使用的 8 位 R/G/B 数值，不再显示识别值的加减偏移。点击“恢复调整默认值”会回到识别值。";
      break;
    }
  }
}

function applyCommon(common) {
  if (common._v054DirectBaseApplied) {
    c = common;
    ensureUi();
    return common;
  }
  c = common;
  const originalCurrentControls = common.currentControls;
  const originalApplyControls = common.applyControls;
  const originalRefreshOutputs = common.refreshOutputs;
  const originalSchedulePreview = common.schedulePreview;

  common.currentControls = function () {
    const controls = originalCurrentControls();
    const detected = common.state.analysis && Array.isArray(common.state.analysis.base)
      ? common.state.analysis.base
      : [0, 0, 0];
    controls.baseAdjust = [0, 1, 2].map(function (index) {
      return directBaseValue(index) - Number(detected[index] || 0);
    });
    return controls;
  };

  common.applyControls = function (values) {
    values = values || common.DEFAULT_CONTROLS;
    originalApplyControls(values);
    const detected = common.state.analysis && Array.isArray(common.state.analysis.base)
      ? common.state.analysis.base
      : [0, 0, 0];
    const offsets = Array.isArray(values.baseAdjust) ? values.baseAdjust : [0, 0, 0];
    ["baseAdjustR", "baseAdjustG", "baseAdjustB"].forEach(function (id, index) {
      const input = common.byId(id);
      if (!input) return;
      const direct = common.engine.clamp(Number(detected[index] || 0) + Number(offsets[index] || 0), 0, 1);
      input.value = String(Math.round(direct * 255));
    });
    lastAnalysisSignature = analysisSignature();
    common.refreshOutputs();
  };

  common.refreshOutputs = function () {
    originalRefreshOutputs();
    ["baseAdjustR", "baseAdjustG", "baseAdjustB"].forEach(function (id) {
      const output = common.byId(id + "Value");
      const input = common.byId(id);
      if (output && input) output.textContent = String(Math.round(Number(input.value)));
    });
  };

  common.schedulePreview = function (delay) {
    const signature = analysisSignature();
    if (signature && signature !== lastAnalysisSignature && !restoring) {
      setDirectBaseFromAnalysis();
      lastAnalysisSignature = signature;
    }
    originalSchedulePreview(delay);
    if (!restoring) setTimeout(function () { record("preview-state", false); }, 0);
  };

  common.resetControls = function () {
    common.applyControls(common.DEFAULT_CONTROLS);
    common.setStatus(common.state.analysis ? "调整已恢复默认，胶片基底恢复为识别值。" : "调整已恢复默认。", common.state.analysis ? "ok" : "");
    common.setProgress(0);
    if (common.state.analysis) common.schedulePreview(0);
  };

  common._v054DirectBaseApplied = true;
  ensureUi();
  return common;
}

function snapshot() {
  return {
    analysis: clone(c.state.analysis),
    controls: clone(c.currentControls()),
    sourceDocumentId: c.state.sourceDocumentId,
    sourceLayerId: c.state.sourceLayerId,
    sourceLayerName: c.state.sourceLayerName
  };
}

function updateButtons() {
  const undo = c.byId("undoEdit");
  const redo = c.byId("redoEdit");
  if (undo) undo.disabled = undoItems.length <= 1;
  if (redo) redo.disabled = redoItems.length === 0;
}

function resetHistory() {
  undoItems = [snapshot()];
  redoItems = [];
  lastKind = "";
  lastTime = 0;
  updateButtons();
}

function record(kind, force) {
  if (restoring || !c) return;
  const next = snapshot();
  if (!undoItems.length) {
    undoItems.push(next);
    updateButtons();
    return;
  }
  if (same(undoItems[undoItems.length - 1], next)) return;

  // The first successful base analysis becomes the starting point. Undo should
  // not return to a stale preview with no analysis.
  if (undoItems.length === 1 && !undoItems[0].analysis && next.analysis) {
    undoItems = [next];
    redoItems = [];
    updateButtons();
    return;
  }

  const now = Date.now();
  const replaceLast = !force && kind === lastKind && now - lastTime < 350 && undoItems.length > 1;
  if (replaceLast) undoItems[undoItems.length - 1] = next;
  else undoItems.push(next);
  if (undoItems.length > LIMIT) undoItems = undoItems.slice(-LIMIT);
  redoItems = [];
  lastKind = kind || "edit";
  lastTime = now;
  updateButtons();
}

function restore(item, message) {
  if (!item) return;
  restoring = true;
  try {
    c.state.analysis = clone(item.analysis);
    c.state.sourceDocumentId = item.sourceDocumentId;
    c.state.sourceLayerId = item.sourceLayerId;
    c.state.sourceLayerName = item.sourceLayerName;
    c.applyControls(item.controls || c.DEFAULT_CONTROLS);
    if (c.state.analysis) {
      c.byId("baseValue").textContent = c.displayRGB(c.state.analysis.base);
      c.byId("confidenceValue").textContent = Math.round((c.state.analysis.confidence || 0) * 100) + "%（历史）";
      c.byId("sourceValue").textContent = c.state.sourceLayerName || "—";
      c.schedulePreview(0);
    }
    c.refreshOutputs();
    c.updateReadiness();
    c.setStatus(message, "ok");
  } finally {
    restoring = false;
  }
  updateButtons();
}

function undo() {
  if (undoItems.length <= 1) {
    c.setStatus("没有可撤销的操作。");
    return;
  }
  redoItems.push(undoItems.pop());
  restore(clone(undoItems[undoItems.length - 1]), "已撤销上一项插件调整。");
}

function redo() {
  if (!redoItems.length) {
    c.setStatus("没有可重做的操作。");
    return;
  }
  const item = redoItems.pop();
  undoItems.push(clone(item));
  restore(item, "已重做下一项插件调整。");
}

function setDirectBaseFromAnalysis() {
  if (!c || !c.state.analysis || !Array.isArray(c.state.analysis.base)) return;
  ["baseAdjustR", "baseAdjustG", "baseAdjustB"].forEach(function (id, index) {
    const input = c.byId(id);
    if (input) input.value = String(Math.round(c.engine.clamp(c.state.analysis.base[index], 0, 1) * 255));
  });
  c.refreshOutputs();
}

function resetNeutralGains() {
  ["redGain", "greenGain", "blueGain"].forEach(function (id) {
    const input = c.byId(id);
    if (input) input.value = "100";
  });
  c.refreshOutputs();
  c.schedulePreview(0);
  c.setStatus("中性灰 R/G/B 输出增益已恢复为 1.00。", "ok");
  record("neutral-reset", true);
}

function initialize() {
  ensureUi();
  const undoButton = c.byId("undoEdit");
  const redoButton = c.byId("redoEdit");
  const resetNeutral = c.byId("resetNeutralGains");
  if (undoButton) undoButton.addEventListener("click", undo);
  if (redoButton) redoButton.addEventListener("click", redo);
  if (resetNeutral) resetNeutral.addEventListener("click", resetNeutralGains);
  document.addEventListener("keydown", function (event) {
    const modifier = event.ctrlKey || event.metaKey;
    if (!modifier || String(event.key).toLowerCase() !== "z") return;
    event.preventDefault();
    if (event.shiftKey) redo();
    else undo();
  });
  document.addEventListener("keydown", function (event) {
    if (!(event.ctrlKey || event.metaKey) || String(event.key).toLowerCase() !== "y") return;
    event.preventDefault();
    redo();
  });
  resetHistory();
}

module.exports = {
  applyCommon,
  initialize,
  record,
  resetHistory,
  undo,
  redo,
  setDirectBaseFromAnalysis,
  resetNeutralGains
};
