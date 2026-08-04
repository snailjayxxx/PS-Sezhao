"use strict";

const { app, imaging, core, constants } = require("photoshop");
const engine = require("./engine.js");

const VERSION = "0.2.1";
const TARGET_TILE_BYTES = 24 * 1024 * 1024;
const ROLL_KEY = "ps-sezhao-roll-v2";
const PREVIEW_LAYER_NAME = "PS-Sezhao · 实时预览（临时）";
const FINAL_LAYER_PREFIX = "正片 · ";
const PREVIEW_DEBOUNCE_MS = 70;

const ADJUSTMENT_IDS = [
  "styleStrength", "exposure", "contrast", "gamma", "saturation",
  "temperature", "tint", "redGain", "greenGain", "blueGain",
  "blackPoint", "whitePoint", "shadows", "highlights",
  "baseAdjustR", "baseAdjustG", "baseAdjustB"
];
const OUTPUT_IDS = ADJUSTMENT_IDS.map(function (id) { return id + "Value"; });
const ACTION_IDS = [
  "analyzeAuto", "analyzeSelection", "neutralizeSelection", "refreshPreview",
  "togglePreview", "removePreview", "convert", "reset", "saveRoll", "loadRoll"
];
const REQUIRED_UI_IDS = ADJUSTMENT_IDS.concat(OUTPUT_IDS, ACTION_IDS, [
  "borderFraction", "borderValue", "profile", "autoPreview", "previewEdge",
  "baseValue", "confidenceValue", "sourceValue", "status", "progress", "readinessValue"
]);
const DEFAULT_CONTROLS = Object.freeze({
  profile: "generic", styleStrength: 1, exposure: 0, contrast: 1, gamma: 1,
  saturation: 1, temperature: 0, tint: 0, redGain: 1, greenGain: 1,
  blueGain: 1, blackPoint: 0, whitePoint: 0, shadows: 0, highlights: 0,
  baseAdjust: [0, 0, 0]
});

const state = {
  analysis: null,
  sourceDocumentId: null,
  sourceLayerId: null,
  sourceLayerName: null,
  previewLayerId: null,
  previewVisible: true,
  previewCache: null,
  previewGeometryKey: null,
  previewTimer: null,
  previewRendering: false,
  previewQueued: false,
  previewRunner: null,
  operation: null,
  initialized: false,
  initTimer: null
};

function byId(id) { return document.getElementById(id); }
function numberValue(value) {
  if (typeof value === "number") return value;
  if (value && typeof value.value === "number") return value.value;
  return Number(value);
}
function messageFromError(error) {
  if (!error) return "发生未知错误。";
  const message = error.message ? String(error.message) : String(error);
  return error.number ? message + "（错误代码 " + error.number + "）" : message;
}
function setStatus(message, kind) {
  const status = byId("status");
  if (!status) return;
  status.textContent = message;
  status.title = message;
  status.className = "status" + (kind ? " " + kind : "");
}
async function reportError(error, showDialog) {
  const message = messageFromError(error);
  console.error(error);
  setProgress(0);
  setStatus(message, "error");
  if (showDialog) {
    try { await app.showAlert(message); } catch (_) { /* status remains visible */ }
  }
}
function setProgress(value) {
  const progress = byId("progress");
  if (progress) progress.style.width = Math.round(engine.clamp(value, 0, 1) * 100) + "%";
}
function updateReadiness() {
  const el = byId("readinessValue");
  if (!el) return;
  if (state.operation === "analyze") {
    el.textContent = "正在分析胶片基底";
    el.className = "readiness busy";
  } else if (state.operation === "render") {
    el.textContent = "正在生成完整分辨率正片";
    el.className = "readiness busy";
  } else if (state.previewRendering) {
    el.textContent = "正在同步滑块预览";
    el.className = "readiness busy";
  } else if (state.analysis) {
    el.textContent = "拖动滑块即可查看画布结果";
    el.className = "readiness ready";
  } else {
    el.textContent = "请先分析胶片基底";
    el.className = "readiness";
  }
}
function setOperation(operation) {
  state.operation = operation;
  const locked = operation === "analyze" || operation === "render";
  ACTION_IDS.forEach(function (id) {
    const el = byId(id);
    if (el) el.disabled = locked;
  });
  ADJUSTMENT_IDS.forEach(function (id) {
    const el = byId(id);
    if (el) el.disabled = operation === "render";
  });
  if (byId("profile")) byId("profile").disabled = operation === "render";
  const convert = byId("convert");
  if (convert) convert.textContent = operation === "render" ? "正在生成最终正片…" : "生成最终正片图层";
  updateReadiness();
}
function documentDimensions(doc) {
  return {
    width: Math.max(1, Math.round(numberValue(doc.width))),
    height: Math.max(1, Math.round(numberValue(doc.height)))
  };
}
function targetSizeFor(width, height, edge) {
  return width >= height ? { width: edge } : { height: edge };
}
function displayRGB(base) {
  return base.map(function (value) { return Math.round(value * 255); }).join(" / ");
}
function cleanColorProfile(profile) {
  if (!profile) return "";
  return String(profile).replace(/\s*\(Linear RGB Profile\)\s*$/i, "").trim();
}
function resolveColorProfile(thumbnail, doc) {
  return cleanColorProfile(thumbnail.colorProfile) || cleanColorProfile(doc.colorProfileName) || "sRGB IEC61966-2.1";
}
function cloneTypedArray(source) {
  if (source instanceof Uint8Array) return new Uint8Array(source);
  if (source instanceof Uint16Array) return new Uint16Array(source);
  return new Float32Array(source);
}

function currentControls() {
  return {
    profile: byId("profile").value,
    styleStrength: Number(byId("styleStrength").value) / 100,
    exposure: Number(byId("exposure").value) / 100,
    contrast: Number(byId("contrast").value) / 100,
    gamma: Number(byId("gamma").value) / 100,
    saturation: Number(byId("saturation").value) / 100,
    temperature: Number(byId("temperature").value) / 100,
    tint: Number(byId("tint").value) / 100,
    redGain: Number(byId("redGain").value) / 100,
    greenGain: Number(byId("greenGain").value) / 100,
    blueGain: Number(byId("blueGain").value) / 100,
    blackPoint: Number(byId("blackPoint").value) / 100,
    whitePoint: Number(byId("whitePoint").value) / 100,
    shadows: Number(byId("shadows").value) / 100,
    highlights: Number(byId("highlights").value) / 100,
    baseAdjust: [
      Number(byId("baseAdjustR").value) / 255,
      Number(byId("baseAdjustG").value) / 255,
      Number(byId("baseAdjustB").value) / 255
    ]
  };
}
function setRangeValue(id, value, scale) {
  if (Number.isFinite(value)) byId(id).value = String(Math.round(value * scale));
}
function applyControls(values) {
  values = values || DEFAULT_CONTROLS;
  if (values.profile && engine.PROFILES[values.profile]) byId("profile").value = values.profile;
  [
    ["styleStrength", values.styleStrength], ["exposure", values.exposure],
    ["contrast", values.contrast], ["gamma", values.gamma],
    ["saturation", values.saturation], ["temperature", values.temperature == null ? values.warmth : values.temperature],
    ["tint", values.tint], ["redGain", values.redGain], ["greenGain", values.greenGain],
    ["blueGain", values.blueGain], ["blackPoint", values.blackPoint],
    ["whitePoint", values.whitePoint], ["shadows", values.shadows], ["highlights", values.highlights]
  ].forEach(function (item) { setRangeValue(item[0], item[1], 100); });
  const base = Array.isArray(values.baseAdjust) ? values.baseAdjust : [0, 0, 0];
  setRangeValue("baseAdjustR", base[0], 255);
  setRangeValue("baseAdjustG", base[1], 255);
  setRangeValue("baseAdjustB", base[2], 255);
  refreshOutputs();
}
function signed(value) {
  const n = Math.round(value);
  return n > 0 ? "+" + n : String(n);
}
function adjustedBaseDisplay(index) {
  if (!state.analysis) return "—";
  const base = engine.effectiveBase(state.analysis, engine.safeControls(currentControls()));
  return String(Math.round(base[index] * 255));
}
function refreshOutputs() {
  if (!state.initialized) return;
  byId("borderValue").textContent = byId("borderFraction").value + "%";
  byId("styleStrengthValue").textContent = byId("styleStrength").value + "%";
  byId("exposureValue").textContent = (Number(byId("exposure").value) / 100).toFixed(2) + " EV";
  ["contrast", "gamma", "saturation", "redGain", "greenGain", "blueGain"].forEach(function (id) {
    byId(id + "Value").textContent = (Number(byId(id).value) / 100).toFixed(2);
  });
  ["temperature", "tint", "blackPoint", "whitePoint", "shadows", "highlights"].forEach(function (id) {
    byId(id + "Value").textContent = signed(byId(id).value);
  });
  byId("baseAdjustRValue").textContent = adjustedBaseDisplay(0);
  byId("baseAdjustGValue").textContent = adjustedBaseDisplay(1);
  byId("baseAdjustBValue").textContent = adjustedBaseDisplay(2);
}
function schedulePreview(delay) {
  if (!state.analysis || !byId("autoPreview").checked || !state.previewRunner) return;
  if (state.previewTimer) clearTimeout(state.previewTimer);
  state.previewTimer = setTimeout(function () {
    state.previewTimer = null;
    state.previewRunner(false);
  }, delay == null ? PREVIEW_DEBOUNCE_MS : delay);
}
function resetControls() {
  applyControls(DEFAULT_CONTROLS);
  setStatus(state.analysis ? "调整已恢复默认，正在同步预览。" : "调整已恢复默认。", state.analysis ? "ok" : "");
  setProgress(0);
  if (state.analysis) schedulePreview(0);
}

function allLayers(layers, result) {
  result = result || [];
  if (!layers) return result;
  for (let i = 0; i < layers.length; i++) {
    const layer = layers[i];
    result.push(layer);
    if (layer.layers && layer.layers.length) allLayers(layer.layers, result);
  }
  return result;
}
function findOpenDocument(id) {
  for (let i = 0; i < app.documents.length; i++) if (app.documents[i].id === id) return app.documents[i];
  return null;
}
function findLayer(doc, id) {
  const layers = allLayers(doc.layers);
  for (let i = 0; i < layers.length; i++) if (layers[i].id === id) return layers[i];
  return null;
}
function ensureActiveCandidate() {
  if (!app.documents.length) throw new Error("请先在 Photoshop 中打开一张胶片负片。");
  const doc = app.activeDocument;
  if (!doc.activeLayers || !doc.activeLayers.length) throw new Error("请先选择负片所在图层。");
  let layer = doc.activeLayers[0];
  const pluginLayer = layer.id === state.previewLayerId || String(layer.name).indexOf(PREVIEW_LAYER_NAME) === 0 || String(layer.name).indexOf(FINAL_LAYER_PREFIX) === 0;
  if (pluginLayer && state.sourceDocumentId === doc.id) {
    const stored = findLayer(doc, state.sourceLayerId);
    if (stored) layer = stored;
  }
  return { doc: doc, layer: layer };
}
function storedSource() {
  if (!state.analysis) throw new Error("请先分析胶片基底。");
  const doc = findOpenDocument(state.sourceDocumentId);
  if (!doc) throw new Error("原始负片文档已关闭，请重新分析。");
  const layer = findLayer(doc, state.sourceLayerId);
  if (!layer) throw new Error("原始负片图层已删除，请重新分析。");
  return { doc: doc, layer: layer };
}
function rememberSource(source) {
  state.sourceDocumentId = source.doc.id;
  state.sourceLayerId = source.layer.id;
  state.sourceLayerName = source.layer.name;
}
async function readThumbnail(source, edge) {
  const size = documentDimensions(source.doc);
  const requestedBounds = { left: 0, top: 0, right: size.width, bottom: size.height };
  const result = await imaging.getPixels({
    documentID: source.doc.id, layerID: source.layer.id, sourceBounds: requestedBounds,
    targetSize: targetSizeFor(size.width, size.height, edge), colorSpace: "RGB",
    componentSize: -1, applyAlpha: false
  });
  try {
    const componentSize = result.imageData.componentSize;
    const fullRange = componentSize === 16;
    const raw = await result.imageData.getData({ chunky: true, fullRange: fullRange });
    return {
      data: cloneTypedArray(raw), width: result.imageData.width, height: result.imageData.height,
      components: result.imageData.components, componentSize: componentSize, fullRange: fullRange,
      colorProfile: cleanColorProfile(result.imageData.colorProfile), requestedBounds: requestedBounds,
      edge: edge, documentId: source.doc.id, layerId: source.layer.id
    };
  } finally { result.imageData.dispose(); }
}
async function selectionForThumbnail(source, thumbnail) {
  const result = await imaging.getSelection({
    documentID: source.doc.id, sourceBounds: thumbnail.requestedBounds,
    targetSize: { width: thumbnail.width, height: thumbnail.height }
  });
  try {
    const size = result.imageData.componentSize;
    const fullRange = size === 16;
    const raw = await result.imageData.getData({ chunky: true, fullRange: fullRange });
    return {
      data: cloneTypedArray(raw), components: result.imageData.components,
      componentSize: size, maxValue: engine.maxForComponent(size, fullRange)
    };
  } finally { result.imageData.dispose(); }
}
async function deletePreviewInsideModal() {
  const doc = state.sourceDocumentId ? findOpenDocument(state.sourceDocumentId) : null;
  const layer = doc && state.previewLayerId ? findLayer(doc, state.previewLayerId) : null;
  if (layer) await layer.delete();
  state.previewLayerId = null;
  state.previewVisible = true;
  state.previewGeometryKey = null;
  if (byId("togglePreview")) byId("togglePreview").textContent = "隐藏预览";
}
async function ensurePreviewLayer(doc) {
  let layer = state.previewLayerId ? findLayer(doc, state.previewLayerId) : null;
  if (!layer) {
    layer = await doc.createLayer({ name: PREVIEW_LAYER_NAME });
    state.previewLayerId = layer.id;
    state.previewGeometryKey = null;
  }
  layer.name = PREVIEW_LAYER_NAME;
  layer.opacity = 100;
  layer.visible = true;
  state.previewVisible = true;
  byId("togglePreview").textContent = "隐藏预览";
  return layer;
}
async function writePreviewPixels(doc, outputImage, thumbnail) {
  const dimensions = documentDimensions(doc);
  const key = [doc.id, dimensions.width, dimensions.height, thumbnail.width, thumbnail.height].join(":");
  let layer = await ensurePreviewLayer(doc);
  if (state.previewGeometryKey && state.previewGeometryKey !== key) {
    await layer.delete();
    state.previewLayerId = null;
    state.previewGeometryKey = null;
    layer = await ensurePreviewLayer(doc);
  }
  await imaging.putPixels({
    documentID: doc.id, layerID: layer.id, imageData: outputImage, replace: true,
    targetBounds: { left: 0, top: 0 }, commandName: "更新胶片实时预览像素"
  });
  if (state.previewGeometryKey !== key) {
    await layer.scale(dimensions.width / thumbnail.width * 100, dimensions.height / thumbnail.height * 100, constants.AnchorPosition.TOPLEFT);
    state.previewGeometryKey = key;
  }
  return layer;
}
function cacheMatches(source, edge) {
  const c = state.previewCache;
  return c && c.documentId === source.doc.id && c.layerId === source.layer.id && c.edge === edge;
}
function tileHeightFor(width, components, componentSize) {
  const bytes = componentSize === 8 ? 1 : componentSize === 16 ? 2 : 4;
  return Math.max(32, Math.min(1024, Math.floor(TARGET_TILE_BYTES / Math.max(1, width * components * bytes * 2))));
}

module.exports = {
  app, imaging, core, constants, engine,
  VERSION, ROLL_KEY, PREVIEW_LAYER_NAME, FINAL_LAYER_PREFIX,
  ADJUSTMENT_IDS, ACTION_IDS, REQUIRED_UI_IDS, DEFAULT_CONTROLS, state,
  byId, setStatus, reportError, setProgress, updateReadiness, setOperation,
  documentDimensions, displayRGB, cleanColorProfile, resolveColorProfile,
  currentControls, applyControls, refreshOutputs, schedulePreview, resetControls,
  findLayer, ensureActiveCandidate, storedSource, rememberSource,
  readThumbnail, selectionForThumbnail, deletePreviewInsideModal,
  ensurePreviewLayer, writePreviewPixels, cacheMatches, tileHeightFor
};
