"use strict";

const { app, imaging, core, constants } = require("photoshop");
const { entrypoints } = require("uxp");
const engine = require("./engine.js");

const VERSION = "0.2.0";
const TARGET_TILE_BYTES = 24 * 1024 * 1024;
const ROLL_KEY = "ps-sezhao-roll-v2";
const PREVIEW_LAYER_NAME = "PS-Sezhao · 实时预览（临时）";
const FINAL_LAYER_PREFIX = "正片 · ";
const PREVIEW_DEBOUNCE_MS = 180;

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
  profile: "generic",
  styleStrength: 1,
  exposure: 0,
  contrast: 1,
  gamma: 1,
  saturation: 1,
  temperature: 0,
  tint: 0,
  redGain: 1,
  greenGain: 1,
  blueGain: 1,
  blackPoint: 0,
  whitePoint: 0,
  shadows: 0,
  highlights: 0,
  baseAdjust: [0, 0, 0]
});

const state = {
  analysis: null,
  sourceDocumentId: null,
  sourceLayerId: null,
  sourceLayerName: null,
  sourceDocumentRef: null,
  sourceLayerRef: null,
  previewLayerId: null,
  previewLayerRef: null,
  previewVisible: true,
  previewCache: null,
  previewTimer: null,
  previewRendering: false,
  previewQueued: false,
  previewUseScaleFallback: false,
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
    try { await app.showAlert(message); } catch (_) { /* Status remains visible. */ }
  }
}

function setProgress(value) {
  const progress = byId("progress");
  if (!progress) return;
  progress.style.width = Math.round(engine.clamp(value, 0, 1) * 100) + "%";
}

function updateReadiness() {
  const readiness = byId("readinessValue");
  if (!readiness) return;
  if (state.operation === "analyze") {
    readiness.textContent = "正在分析胶片基底";
    readiness.className = "readiness busy";
  } else if (state.operation === "render") {
    readiness.textContent = "正在生成完整分辨率正片";
    readiness.className = "readiness busy";
  } else if (state.previewRendering) {
    readiness.textContent = "正在更新实时预览";
    readiness.className = "readiness busy";
  } else if (state.analysis) {
    readiness.textContent = "基底分析完成，可实时调整或生成最终图层";
    readiness.className = "readiness ready";
  } else {
    readiness.textContent = "请先分析胶片基底";
    readiness.className = "readiness";
  }
}

function setOperation(operation) {
  state.operation = operation;
  const locked = operation === "analyze" || operation === "render";
  ACTION_IDS.forEach(function (id) {
    const element = byId(id);
    if (element) element.disabled = locked;
  });
  ADJUSTMENT_IDS.forEach(function (id) {
    const element = byId(id);
    if (element) element.disabled = operation === "render";
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
  return String(profile).replace(/\s*\(Linear RGB Profile\)\s*$/i, "");
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
  setRangeValue("styleStrength", values.styleStrength, 100);
  setRangeValue("exposure", values.exposure, 100);
  setRangeValue("contrast", values.contrast, 100);
  setRangeValue("gamma", values.gamma, 100);
  setRangeValue("saturation", values.saturation, 100);
  setRangeValue("temperature", values.temperature == null ? values.warmth : values.temperature, 100);
  setRangeValue("tint", values.tint, 100);
  setRangeValue("redGain", values.redGain, 100);
  setRangeValue("greenGain", values.greenGain, 100);
  setRangeValue("blueGain", values.blueGain, 100);
  setRangeValue("blackPoint", values.blackPoint, 100);
  setRangeValue("whitePoint", values.whitePoint, 100);
  setRangeValue("shadows", values.shadows, 100);
  setRangeValue("highlights", values.highlights, 100);
  const baseAdjust = Array.isArray(values.baseAdjust) ? values.baseAdjust : [0, 0, 0];
  setRangeValue("baseAdjustR", baseAdjust[0], 255);
  setRangeValue("baseAdjustG", baseAdjust[1], 255);
  setRangeValue("baseAdjustB", baseAdjust[2], 255);
  refreshOutputs();
}

function signed(value) {
  const rounded = Math.round(value);
  return rounded > 0 ? "+" + rounded : String(rounded);
}

function adjustedBaseDisplay(index) {
  if (!state.analysis) return "—";
  const controls = currentControls();
  const base = engine.effectiveBase(state.analysis, engine.safeControls(controls));
  return String(Math.round(base[index] * 255));
}

function refreshOutputs() {
  if (!state.initialized) return;
  byId("borderValue").textContent = byId("borderFraction").value + "%";
  byId("styleStrengthValue").textContent = byId("styleStrength").value + "%";
  byId("exposureValue").textContent = (Number(byId("exposure").value) / 100).toFixed(2) + " EV";
  byId("contrastValue").textContent = (Number(byId("contrast").value) / 100).toFixed(2);
  byId("gammaValue").textContent = (Number(byId("gamma").value) / 100).toFixed(2);
  byId("saturationValue").textContent = (Number(byId("saturation").value) / 100).toFixed(2);
  byId("temperatureValue").textContent = signed(byId("temperature").value);
  byId("tintValue").textContent = signed(byId("tint").value);
  byId("redGainValue").textContent = (Number(byId("redGain").value) / 100).toFixed(2);
  byId("greenGainValue").textContent = (Number(byId("greenGain").value) / 100).toFixed(2);
  byId("blueGainValue").textContent = (Number(byId("blueGain").value) / 100).toFixed(2);
  byId("blackPointValue").textContent = signed(byId("blackPoint").value);
  byId("whitePointValue").textContent = signed(byId("whitePoint").value);
  byId("shadowsValue").textContent = signed(byId("shadows").value);
  byId("highlightsValue").textContent = signed(byId("highlights").value);
  byId("baseAdjustRValue").textContent = adjustedBaseDisplay(0);
  byId("baseAdjustGValue").textContent = adjustedBaseDisplay(1);
  byId("baseAdjustBValue").textContent = adjustedBaseDisplay(2);
}

function resetControls() {
  applyControls(DEFAULT_CONTROLS);
  setStatus(state.analysis ? "调整已恢复默认，正在刷新预览。" : "调整已恢复默认。", state.analysis ? "ok" : "");
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
  for (let i = 0; i < app.documents.length; i++) {
    if (app.documents[i].id === id) return app.documents[i];
  }
  return null;
}

function findLayer(doc, id) {
  const layers = allLayers(doc.layers);
  for (let i = 0; i < layers.length; i++) {
    if (layers[i].id === id) return layers[i];
  }
  return null;
}

function ensureActiveCandidate() {
  if (!app.documents.length) throw new Error("请先在 Photoshop 中打开一张胶片负片。");
  const doc = app.activeDocument;
  if (!doc.activeLayers || !doc.activeLayers.length) throw new Error("请先选择负片所在图层。");
  let layer = doc.activeLayers[0];
  const isPluginLayer = layer.id === state.previewLayerId || String(layer.name).indexOf(PREVIEW_LAYER_NAME) === 0 || String(layer.name).indexOf(FINAL_LAYER_PREFIX) === 0;
  if (isPluginLayer && state.sourceDocumentId === doc.id) {
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
  state.sourceDocumentRef = source.doc;
  state.sourceLayerRef = source.layer;
}

async function readThumbnail(source, edge) {
  const size = documentDimensions(source.doc);
  const requestedBounds = { left: 0, top: 0, right: size.width, bottom: size.height };
  const result = await imaging.getPixels({
    documentID: source.doc.id,
    layerID: source.layer.id,
    sourceBounds: requestedBounds,
    targetSize: targetSizeFor(size.width, size.height, edge),
    colorSpace: "RGB",
    componentSize: 8,
    applyAlpha: false
  });
  try {
    const raw = await result.imageData.getData({ chunky: true });
    return {
      data: new Uint8Array(raw),
      width: result.imageData.width,
      height: result.imageData.height,
      components: result.imageData.components,
      requestedBounds: requestedBounds,
      edge: edge,
      documentId: source.doc.id,
      layerId: source.layer.id
    };
  } finally {
    result.imageData.dispose();
  }
}

async function selectionForThumbnail(source, thumbnail) {
  const result = await imaging.getSelection({
    documentID: source.doc.id,
    sourceBounds: thumbnail.requestedBounds,
    targetSize: { width: thumbnail.width, height: thumbnail.height }
  });
  try {
    const raw = await result.imageData.getData({ chunky: true });
    return {
      data: new Uint8Array(raw),
      components: result.imageData.components
    };
  } finally {
    result.imageData.dispose();
  }
}

async function deletePreviewInsideModal() {
  const doc = state.sourceDocumentId ? findOpenDocument(state.sourceDocumentId) : null;
  const layer = doc && state.previewLayerId ? findLayer(doc, state.previewLayerId) : null;
  if (layer) await layer.delete();
  state.previewLayerId = null;
  state.previewLayerRef = null;
  state.previewVisible = true;
  const toggle = byId("togglePreview");
  if (toggle) toggle.textContent = "隐藏预览";
}

async function removePreview(showStatus) {
  if (!state.previewLayerId) {
    if (showStatus) setStatus("当前没有实时预览图层。");
    return;
  }
  try {
    await core.executeAsModal(async function () {
      await deletePreviewInsideModal();
    }, { commandName: "移除胶片实时预览", timeOut: 10 });
    if (showStatus) setStatus("实时预览图层已移除。", "ok");
  } catch (error) {
    await reportError(error, showStatus);
  }
}

async function analyze(useSelection) {
  if (state.operation || state.previewRendering) return;
  setOperation("analyze");
  setProgress(0.05);
  setStatus(useSelection ? "正在读取选区并分析胶片基底…" : "正在分析胶片边框…");

  try {
    const source = ensureActiveCandidate();
    const edge = Math.max(1000, Number(byId("previewEdge").value) || 1200);
    let resultBundle;

    await core.executeAsModal(async function (executionContext) {
      executionContext.reportProgress({ value: 0.12, commandName: "读取负片缩略图" });
      const thumbnail = await readThumbnail(source, edge);
      let mask;
      const borderFraction = Number(byId("borderFraction").value) / 100;
      if (useSelection) {
        const selection = await selectionForThumbnail(source, thumbnail);
        mask = engine.estimateMaskFromSelection(
          thumbnail.data, selection.data, thumbnail.width, thumbnail.height,
          thumbnail.components, selection.components,
          { maxValue: 255, selectionMax: 255 }
        );
      } else {
        mask = engine.estimateMaskFromBorder(
          thumbnail.data, thumbnail.width, thumbnail.height, thumbnail.components,
          { maxValue: 255, borderFraction: borderFraction }
        );
      }
      executionContext.reportProgress({ value: 0.70, commandName: "计算密度与色罩" });
      const analysis = engine.analysisFromThumbnail(
        thumbnail.data, thumbnail.width, thumbnail.height, thumbnail.components,
        mask, { maxValue: 255, borderFraction: borderFraction }
      );
      await deletePreviewInsideModal();
      resultBundle = { thumbnail: thumbnail, analysis: analysis };
      executionContext.reportProgress({ value: 1, commandName: "分析完成" });
    }, { commandName: useSelection ? "从选区分析胶片基底" : "自动分析胶片基底", timeOut: 10 });

    state.analysis = resultBundle.analysis;
    state.previewCache = resultBundle.thumbnail;
    rememberSource(source);
    byId("baseValue").textContent = displayRGB(state.analysis.base);
    byId("confidenceValue").textContent = Math.round(state.analysis.confidence * 100) + "%" + (useSelection ? "（选区）" : "（边框）");
    byId("sourceValue").textContent = source.layer.name;
    refreshOutputs();
    setProgress(1);
    setStatus("分析完成，正在生成实时预览。", "ok");
    setOperation(null);
    schedulePreview(0);
  } catch (error) {
    state.analysis = null;
    state.previewCache = null;
    setOperation(null);
    await reportError(error, true);
  }
}

function cacheMatches(source, edge) {
  return state.previewCache && state.previewCache.documentId === source.doc.id && state.previewCache.layerId === source.layer.id && state.previewCache.edge === edge;
}

function schedulePreview(delay) {
  if (!state.analysis || !byId("autoPreview").checked) return;
  if (state.previewTimer) clearTimeout(state.previewTimer);
  state.previewTimer = setTimeout(function () {
    state.previewTimer = null;
    renderPreview(false);
  }, delay == null ? PREVIEW_DEBOUNCE_MS : delay);
}

async function ensurePreviewLayer(doc) {
  let layer = state.previewLayerId ? findLayer(doc, state.previewLayerId) : null;
  if (!layer) {
    layer = await doc.createLayer({ name: PREVIEW_LAYER_NAME });
    state.previewLayerId = layer.id;
    state.previewLayerRef = layer;
  }
  layer.name = PREVIEW_LAYER_NAME;
  layer.opacity = 100;
  layer.visible = true;
  state.previewVisible = true;
  byId("togglePreview").textContent = "隐藏预览";
  return layer;
}

async function putScaledPreview(doc, layer, imageData, thumbnail) {
  const dimensions = documentDimensions(doc);
  if (!state.previewUseScaleFallback) {
    try {
      await imaging.putPixels({
        documentID: doc.id,
        layerID: layer.id,
        imageData: imageData,
        replace: true,
        targetBounds: { left: 0, top: 0, right: dimensions.width, bottom: dimensions.height },
        targetSize: { width: dimensions.width, height: dimensions.height },
        commandName: "更新胶片实时预览"
      });
      return layer;
    } catch (error) {
      console.warn("putPixels targetSize failed; using layer scale fallback", error);
      state.previewUseScaleFallback = true;
      await layer.delete();
      state.previewLayerId = null;
      state.previewLayerRef = null;
      layer = await ensurePreviewLayer(doc);
    }
  }

  if (layer) await layer.delete();
  state.previewLayerId = null;
  state.previewLayerRef = null;
  layer = await ensurePreviewLayer(doc);
  await imaging.putPixels({
    documentID: doc.id,
    layerID: layer.id,
    imageData: imageData,
    replace: true,
    targetBounds: { left: 0, top: 0 },
    commandName: "写入低分辨率预览"
  });
  const scaleX = dimensions.width / thumbnail.width * 100;
  const scaleY = dimensions.height / thumbnail.height * 100;
  await layer.scale(scaleX, scaleY, constants.AnchorPosition.TOPLEFT);
  return layer;
}

async function renderPreview(force) {
  if (!state.analysis) {
    if (force) await reportError(new Error("请先分析胶片基底。"), true);
    return;
  }
  if (state.operation === "analyze" || state.operation === "render") return;
  if (state.previewRendering) {
    state.previewQueued = true;
    return;
  }

  state.previewRendering = true;
  state.previewQueued = false;
  updateReadiness();
  setStatus("正在更新画布实时预览…");

  try {
    const source = storedSource();
    const edge = Number(byId("previewEdge").value) || 1200;
    const controls = currentControls();

    await core.executeAsModal(async function () {
      let thumbnail = state.previewCache;
      if (!cacheMatches(source, edge)) {
        thumbnail = await readThumbnail(source, edge);
        state.previewCache = thumbnail;
      }
      const processed = engine.processBuffer(
        thumbnail.data, thumbnail.width, thumbnail.height, thumbnail.components,
        8, state.analysis, controls, controls.profile, true
      );
      const outputImage = await imaging.createImageDataFromBuffer(processed, {
        width: thumbnail.width,
        height: thumbnail.height,
        components: thumbnail.components,
        chunky: true,
        colorSpace: "RGB",
        fullRange: true
      });
      try {
        let layer = await ensurePreviewLayer(source.doc);
        layer = await putScaledPreview(source.doc, layer, outputImage, thumbnail);
        state.previewLayerId = layer.id;
        state.previewLayerRef = layer;
        layer.visible = true;
      } finally {
        outputImage.dispose();
      }
      if (typeof app.updateUI === "function") await app.updateUI();
    }, { commandName: "更新胶片实时预览", interactive: true, timeOut: 10 });

    setProgress(1);
    setStatus("实时预览已更新。继续拖动参数即可刷新。", "ok");
  } catch (error) {
    await reportError(error, force);
  } finally {
    state.previewRendering = false;
    updateReadiness();
    if (state.previewQueued) {
      state.previewQueued = false;
      schedulePreview(60);
    }
  }
}

async function togglePreview() {
  if (!state.previewLayerId) {
    await renderPreview(true);
    return;
  }
  try {
    const source = storedSource();
    await core.executeAsModal(async function () {
      const layer = findLayer(source.doc, state.previewLayerId);
      if (!layer) throw new Error("实时预览图层已不存在，请重新刷新预览。");
      state.previewVisible = !layer.visible;
      layer.visible = state.previewVisible;
      byId("togglePreview").textContent = state.previewVisible ? "隐藏预览" : "显示预览";
      if (typeof app.updateUI === "function") await app.updateUI();
    }, { commandName: state.previewVisible ? "隐藏胶片预览" : "显示胶片预览", interactive: true, timeOut: 10 });
    setStatus(state.previewVisible ? "已显示实时预览。" : "已隐藏实时预览，可查看原始负片。", "ok");
  } catch (error) {
    await reportError(error, true);
  }
}

async function neutralizeSelection() {
  if (!state.analysis) {
    await reportError(new Error("请先分析胶片基底，然后框选应当为白色或灰色的区域。"), true);
    return;
  }
  if (state.operation || state.previewRendering) return;
  setOperation("analyze");
  setStatus("正在从当前选区计算中性色校正…");

  try {
    const source = storedSource();
    const edge = Number(byId("previewEdge").value) || 1200;
    const controls = currentControls();
    let gainResult;

    await core.executeAsModal(async function () {
      let thumbnail = state.previewCache;
      if (!cacheMatches(source, edge)) {
        thumbnail = await readThumbnail(source, edge);
        state.previewCache = thumbnail;
      }
      const selection = await selectionForThumbnail(source, thumbnail);
      gainResult = engine.estimateNeutralGains(
        thumbnail.data, selection.data, thumbnail.width, thumbnail.height,
        thumbnail.components, selection.components, state.analysis, controls,
        controls.profile, { maxValue: 255, selectionMax: 255 }
      );
    }, { commandName: "从选区校正中性色", timeOut: 10 });

    byId("redGain").value = String(Math.round(gainResult.redGain * 100));
    byId("greenGain").value = String(Math.round(gainResult.greenGain * 100));
    byId("blueGain").value = String(Math.round(gainResult.blueGain * 100));
    refreshOutputs();
    setOperation(null);
    setStatus("中性色校正完成，正在刷新预览。", "ok");
    schedulePreview(0);
  } catch (error) {
    setOperation(null);
    await reportError(error, true);
  }
}

function tileHeightFor(width, components, componentSize) {
  const bytes = componentSize === 8 ? 1 : componentSize === 16 ? 2 : 4;
  return Math.max(32, Math.min(1024, Math.floor(TARGET_TILE_BYTES / Math.max(1, width * components * bytes * 2))));
}

async function convert() {
  if (state.operation || state.previewRendering) return;
  let source;
  try {
    source = storedSource();
  } catch (error) {
    await reportError(error, true);
    return;
  }

  setOperation("render");
  setProgress(0.01);
  setStatus("准备生成完整分辨率正片图层…");

  try {
    const controls = currentControls();
    const dimensions = documentDimensions(source.doc);
    const sourceDocId = source.doc.id;
    const sourceLayerId = source.layer.id;
    const sourceName = source.layer.name;

    await core.executeAsModal(async function (executionContext) {
      const previewLayer = state.previewLayerId ? findLayer(source.doc, state.previewLayerId) : null;
      if (previewLayer) previewLayer.visible = false;
      const outputLayer = await source.doc.createLayer({ name: FINAL_LAYER_PREFIX + sourceName + " · PS-Sezhao " + VERSION });
      let top = 0;
      let suggestedTileHeight = 256;

      while (top < dimensions.height) {
        if (executionContext.isCancelled) throw new Error("用户已取消生成正片。");
        const bottom = Math.min(dimensions.height, top + suggestedTileHeight);
        const pixelResult = await imaging.getPixels({
          documentID: sourceDocId,
          layerID: sourceLayerId,
          sourceBounds: { left: 0, top: top, right: dimensions.width, bottom: bottom },
          colorSpace: "RGB",
          componentSize: -1,
          applyAlpha: false
        });
        const sourceImage = pixelResult.imageData;
        if (!sourceImage || sourceImage.width < 1 || sourceImage.height < 1) {
          if (sourceImage) sourceImage.dispose();
          top = bottom;
          continue;
        }

        let outputImage;
        try {
          const componentSize = sourceImage.componentSize;
          suggestedTileHeight = tileHeightFor(dimensions.width, sourceImage.components, componentSize);
          const fullRange = componentSize === 16;
          const sourceData = await sourceImage.getData({ chunky: true, fullRange: fullRange });
          const processed = engine.processBuffer(
            sourceData, sourceImage.width, sourceImage.height, sourceImage.components,
            componentSize, state.analysis, controls, controls.profile, fullRange
          );
          outputImage = await imaging.createImageDataFromBuffer(processed, {
            width: sourceImage.width,
            height: sourceImage.height,
            components: sourceImage.components,
            chunky: true,
            colorSpace: "RGB",
            colorProfile: cleanColorProfile(sourceImage.colorProfile),
            fullRange: fullRange
          });
          await imaging.putPixels({
            documentID: sourceDocId,
            layerID: outputLayer.id,
            imageData: outputImage,
            replace: false,
            targetBounds: { left: pixelResult.sourceBounds.left, top: pixelResult.sourceBounds.top },
            commandName: "写入胶片转正像素"
          });
        } finally {
          if (outputImage) outputImage.dispose();
          sourceImage.dispose();
        }

        top = bottom;
        const progress = top / dimensions.height;
        setProgress(progress);
        executionContext.reportProgress({ value: progress, commandName: "正在生成完整分辨率正片" });
      }
      await deletePreviewInsideModal();
    }, { commandName: "生成最终胶片正片", timeOut: 10 });

    setProgress(1);
    setStatus("最终正片图层已生成，原始负片图层未修改。", "ok");
  } catch (error) {
    await reportError(error, true);
  } finally {
    setOperation(null);
  }
}

function saveRoll() {
  try {
    if (!state.analysis) throw new Error("请先完成胶片基底分析，再保存本卷参数。");
    const payload = { version: 2, analysis: state.analysis, controls: currentControls() };
    localStorage.setItem(ROLL_KEY, JSON.stringify(payload));
    setStatus("本卷分析与全部校色参数已保存。", "ok");
  } catch (error) {
    reportError(error, false);
  }
}

async function loadRoll() {
  try {
    const raw = localStorage.getItem(ROLL_KEY);
    if (!raw) throw new Error("尚未保存本卷参数。");
    const payload = JSON.parse(raw);
    if (!payload || !payload.analysis) throw new Error("保存的本卷参数格式无效。");
    const source = ensureActiveCandidate();
    state.analysis = payload.analysis;
    state.previewCache = null;
    rememberSource(source);
    applyControls(payload.controls || DEFAULT_CONTROLS);
    byId("baseValue").textContent = displayRGB(state.analysis.base);
    byId("confidenceValue").textContent = Math.round(state.analysis.confidence * 100) + "%（本卷）";
    byId("sourceValue").textContent = source.layer.name;
    updateReadiness();
    setStatus("本卷参数已应用，正在刷新预览。", "ok");
    schedulePreview(0);
  } catch (error) {
    await reportError(error, true);
  }
}

function onAdjustmentInput() {
  refreshOutputs();
  schedulePreview();
}

function bindClick(id, handler) {
  byId(id).addEventListener("click", handler);
}

function initializeUI() {
  if (state.initialized) return true;
  const missing = REQUIRED_UI_IDS.filter(function (id) { return !byId(id); });
  if (missing.length) return false;

  state.initialized = true;
  ADJUSTMENT_IDS.forEach(function (id) {
    byId(id).addEventListener("input", onAdjustmentInput);
  });
  byId("profile").addEventListener("change", onAdjustmentInput);
  byId("previewEdge").addEventListener("change", function () {
    state.previewCache = null;
    schedulePreview(0);
  });
  byId("autoPreview").addEventListener("change", function () {
    if (byId("autoPreview").checked) {
      setStatus("自动预览已开启，正在刷新。", "ok");
      schedulePreview(0);
    } else {
      setStatus("自动预览已关闭，可点击“立即刷新预览”。");
    }
  });
  byId("borderFraction").addEventListener("input", refreshOutputs);

  bindClick("analyzeAuto", function () { analyze(false); });
  bindClick("analyzeSelection", function () { analyze(true); });
  bindClick("neutralizeSelection", neutralizeSelection);
  bindClick("refreshPreview", function () { renderPreview(true); });
  bindClick("togglePreview", togglePreview);
  bindClick("removePreview", function () { removePreview(true); });
  bindClick("convert", convert);
  bindClick("reset", resetControls);
  bindClick("saveRoll", saveRoll);
  bindClick("loadRoll", loadRoll);

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
