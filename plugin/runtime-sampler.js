"use strict";

const { action } = require("photoshop");
const c = require("./runtime-common.js");
const panelPreview = require("./runtime-panel-preview.js");
const {
  app, imaging, core, engine, state, byId, setStatus, reportError,
  currentControls, refreshOutputs, schedulePreview, displayRGB,
  ensureActiveCandidate, storedSource, rememberSource, readThumbnail,
  cacheMatches
} = c;

const PICK_TIMEOUT_MS = 60000;
const POLL_INTERVAL_MS = 120;

function numberValue(value) {
  if (typeof value === "number") return value;
  if (value && typeof value.value === "number") return value.value;
  return Number(value);
}

function sampleSize() {
  const value = Number(byId("sampleSize") && byId("sampleSize").value);
  return [1, 3, 5, 11, 21].indexOf(value) >= 0 ? value : 11;
}

function samplerSnapshot(doc) {
  const result = [];
  if (!doc || !doc.colorSamplers) return result;
  for (let i = 0; i < doc.colorSamplers.length; i++) {
    const sampler = doc.colorSamplers[i];
    const pos = sampler.position || {};
    result.push({
      index: i,
      x: Math.round(numberValue(pos.x)),
      y: Math.round(numberValue(pos.y))
    });
  }
  return result;
}

function signature(item) {
  return item.index + ":" + item.x + ":" + item.y;
}

function findNewSampler(doc, baseline) {
  const before = new Set((baseline || []).map(signature));
  const now = samplerSnapshot(doc);
  for (let i = now.length - 1; i >= 0; i--) {
    if (!before.has(signature(now[i]))) {
      return { sampler: doc.colorSamplers[now[i].index], position: now[i] };
    }
  }
  if (now.length > (baseline || []).length && now.length) {
    const last = now[now.length - 1];
    return { sampler: doc.colorSamplers[last.index], position: last };
  }
  return null;
}

async function selectTool(toolRef) {
  if (!toolRef) return;
  await core.executeAsModal(async function () {
    await action.batchPlay([{
      _obj: "select",
      _target: [{ _ref: toolRef }],
      _options: { dialogOptions: "dontDisplay" }
    }], { synchronousExecution: false });
  }, { commandName: "切换吸管工具" });
}

function setPickerButtons(mode) {
  const base = byId("pickBase");
  const neutral = byId("pickNeutral");
  const cancel = byId("cancelPicker");
  if (base) base.className = mode === "base" ? "primary picker-on" : "primary";
  if (neutral) neutral.className = mode === "neutral" ? "primary picker-on" : "";
  if (cancel) cancel.disabled = !mode;
}

function clearPoll() {
  if (state.pickerTimer) clearTimeout(state.pickerTimer);
  state.pickerTimer = null;
}

async function restoreTool() {
  const previous = state.pickerPreviousTool;
  state.pickerPreviousTool = null;
  if (typeof previous !== "string" || !previous || previous === "colorSamplerTool") return;
  try { await selectTool(previous); } catch (_) { /* leave current tool unchanged */ }
}

function finishPicker(message, kind) {
  clearPoll();
  state.pickerMode = null;
  state.pickerBaseline = null;
  setPickerButtons(null);
  panelPreview.setPickerActive(false);
  if (message) setStatus(message, kind || "ok");
  restoreTool();
}

function cancelPicker() {
  if (!state.pickerMode) return;
  finishPicker("已取消吸管取样。", "");
}

async function readPatch(source, position, size) {
  const dimensions = c.documentDimensions(source.doc);
  const half = Math.floor(size / 2);
  const left = Math.max(0, Math.min(dimensions.width - 1, Math.round(position.x) - half));
  const top = Math.max(0, Math.min(dimensions.height - 1, Math.round(position.y) - half));
  const right = Math.max(left + 1, Math.min(dimensions.width, left + size));
  const bottom = Math.max(top + 1, Math.min(dimensions.height, top + size));
  const result = await imaging.getPixels({
    documentID: source.doc.id,
    layerID: source.layer.id,
    sourceBounds: { left: left, top: top, right: right, bottom: bottom },
    colorSpace: "RGB",
    componentSize: -1,
    applyAlpha: false
  });
  try {
    const componentSize = result.imageData.componentSize;
    const fullRange = componentSize === 16;
    const data = await result.imageData.getData({ chunky: true, fullRange: fullRange });
    return {
      data: data,
      width: result.imageData.width,
      height: result.imageData.height,
      components: result.imageData.components,
      componentSize: componentSize,
      fullRange: fullRange,
      maxValue: engine.maxForComponent(componentSize, fullRange)
    };
  } finally {
    result.imageData.dispose();
  }
}

function medianRGB(patch) {
  const channels = [[], [], []];
  const pixels = patch.width * patch.height;
  for (let p = 0; p < pixels; p++) {
    const index = p * patch.components;
    if (patch.components > 3 && Number(patch.data[index + 3]) / patch.maxValue < 0.2) continue;
    channels[0].push(Number(patch.data[index]) / patch.maxValue);
    channels[1].push(Number(patch.data[index + 1]) / patch.maxValue);
    channels[2].push(Number(patch.data[index + 2]) / patch.maxValue);
  }
  if (!channels[0].length) throw new Error("点击位置没有可读取的像素，请重新点击图像内部。");
  return channels.map(engine.median);
}

async function applyBaseSample(source, patch, position) {
  const base = medianRGB(patch);
  const edge = Number(byId("previewEdge").value) || 1800;
  let thumbnail = state.previewCache;
  if (!cacheMatches(source, edge)) thumbnail = await readThumbnail(source, edge);
  const tone = engine.analyzeToneRange(
    thumbnail.data,
    thumbnail.width,
    thumbnail.height,
    thumbnail.components,
    base,
    {
      maxValue: engine.maxForComponent(thumbnail.componentSize, thumbnail.fullRange),
      borderFraction: Number(byId("borderFraction").value) / 100
    }
  );
  state.analysis = {
    base: base,
    black: tone.black,
    white: tone.white,
    confidence: 1,
    method: "eyedropper",
    maskSampleCount: patch.width * patch.height,
    toneSampleCount: tone.sampleCount,
    samplePosition: { x: position.x, y: position.y }
  };
  state.previewCache = thumbnail;
  rememberSource(source);
  ["baseAdjustR", "baseAdjustG", "baseAdjustB"].forEach(function (id) {
    if (byId(id)) byId(id).value = "0";
  });
  byId("baseValue").textContent = displayRGB(base);
  byId("confidenceValue").textContent = "100%（吸管）";
  byId("sourceValue").textContent = source.layer.name;
  refreshOutputs();
  schedulePreview(0);
}

function neutralGainFromMedian(patch, controls) {
  const raw = medianRGB(patch);
  const profile = engine.PROFILES[controls.profile] || engine.PROFILES.generic;
  const transformed = engine.transformRGB(raw, state.analysis, controls, profile);
  const target = engine.clamp(
    0.2126 * transformed[0] + 0.7152 * transformed[1] + 0.0722 * transformed[2],
    0.05,
    0.95
  );
  return {
    redGain: engine.clamp(controls.redGain * target / Math.max(transformed[0], 0.01), 0.25, 3),
    greenGain: engine.clamp(controls.greenGain * target / Math.max(transformed[1], 0.01), 0.25, 3),
    blueGain: engine.clamp(controls.blueGain * target / Math.max(transformed[2], 0.01), 0.25, 3)
  };
}

function applyNeutralSample(patch) {
  const pixelCount = patch.width * patch.height;
  const controls = currentControls();
  let gain;
  if (pixelCount >= 12) {
    const selection = new Uint8Array(pixelCount);
    selection.fill(255);
    gain = engine.estimateNeutralGains(
      patch.data,
      selection,
      patch.width,
      patch.height,
      patch.components,
      1,
      state.analysis,
      controls,
      controls.profile,
      { maxValue: patch.maxValue, selectionMax: 255 }
    );
  } else {
    gain = neutralGainFromMedian(patch, controls);
  }
  byId("redGain").value = String(Math.round(gain.redGain * 100));
  byId("greenGain").value = String(Math.round(gain.greenGain * 100));
  byId("blueGain").value = String(Math.round(gain.blueGain * 100));
  refreshOutputs();
  schedulePreview(0);
}

async function captureAt(position, mode, sampler) {
  clearPoll();
  try {
    const source = mode === "neutral" ? storedSource() : (state.analysis ? storedSource() : ensureActiveCandidate());
    let patch;
    await core.executeAsModal(async function () {
      patch = await readPatch(source, position, sampleSize());
      if (mode === "base") await applyBaseSample(source, patch, position);
      else applyNeutralSample(patch);
      if (sampler && typeof sampler.remove === "function") sampler.remove();
    }, { commandName: mode === "base" ? "吸管采样胶片基底" : "吸管采样中性色" });

    finishPicker(
      mode === "base"
        ? "胶片基底已按点击位置更新，正在刷新预览。"
        : "中性色已按点击位置校正，正在刷新预览。",
      "ok"
    );
  } catch (error) {
    finishPicker();
    await reportError(error, true);
  }
}

function pollCanvasSampler() {
  if (!state.pickerMode) return;
  const doc = app.activeDocument;
  if (!doc || doc.id !== state.pickerDocumentId) {
    finishPicker("取样文档已切换，吸管已取消。", "");
    return;
  }
  const found = findNewSampler(doc, state.pickerBaseline);
  if (found) {
    captureAt(found.position, state.pickerMode, found.sampler);
    return;
  }
  if (Date.now() - state.pickerStartedAt > PICK_TIMEOUT_MS) {
    finishPicker("吸管等待超时，已取消。", "");
    return;
  }
  state.pickerTimer = setTimeout(pollCanvasSampler, POLL_INTERVAL_MS);
}

async function startPicker(mode) {
  if (mode === "neutral" && !state.analysis) {
    await reportError(new Error("请先分析胶片基底，再使用中性色吸管。"), true);
    return;
  }
  if (state.operation || state.previewRendering) return;
  if (state.pickerMode) cancelPicker();

  try {
    const source = mode === "neutral" ? storedSource() : (state.analysis ? storedSource() : ensureActiveCandidate());
    state.pickerMode = mode;
    state.pickerDocumentId = source.doc.id;
    state.pickerBaseline = samplerSnapshot(source.doc);
    state.pickerStartedAt = Date.now();
    state.pickerPreviousTool = app.currentTool;
    setPickerButtons(mode);
    panelPreview.setPickerActive(true, mode);
    setStatus(mode === "base"
      ? "色罩吸管已启动：直接点击 Photoshop 画布中的未曝光橙色胶片；也可点击上方大图预览。"
      : "中性色吸管已启动：直接点击 Photoshop 画布中的白色或灰色区域；也可点击上方大图预览。", "ok");

    try {
      await selectTool("colorSamplerTool");
    } catch (toolError) {
      console.warn("Unable to select colorSamplerTool", toolError);
      setStatus("Photoshop 未能自动切换取样工具。仍可直接点击插件内大图预览完成取样。", "error");
    }
    pollCanvasSampler();
  } catch (error) {
    finishPicker();
    await reportError(error, true);
  }
}

function handlePanelPreviewClick(event) {
  if (!state.pickerMode) return;
  const point = panelPreview.mapEventToDocument(event);
  if (!point) {
    reportError(new Error("大图预览尚未准备完成。"), false);
    return;
  }
  captureAt(point, state.pickerMode, null);
}

function initialize() {
  const base = byId("pickBase");
  const neutral = byId("pickNeutral");
  const cancel = byId("cancelPicker");
  const image = byId("panelPreviewImage");
  if (base) base.addEventListener("click", function () { startPicker("base"); });
  if (neutral) neutral.addEventListener("click", function () { startPicker("neutral"); });
  if (cancel) {
    cancel.disabled = true;
    cancel.addEventListener("click", cancelPicker);
  }
  if (image) image.addEventListener("click", handlePanelPreviewClick);
}

module.exports = {
  initialize,
  startPicker,
  cancelPicker,
  handlePanelPreviewClick,
  captureAt
};
