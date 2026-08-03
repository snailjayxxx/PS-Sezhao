"use strict";

const { app, imaging, core } = require("photoshop");
const { entrypoints } = require("uxp");
const engine = require("./engine.js");

const VERSION = "0.1.2";
const MAX_PREVIEW_EDGE = 720;
const TARGET_TILE_BYTES = 24 * 1024 * 1024;
const ROLL_KEY = "ps-sezhao-roll-v1";
const CONTROL_IDS = ["borderFraction", "exposure", "contrast", "gamma", "saturation", "warmth"];
const ACTION_IDS = ["analyzeAuto", "analyzeSelection", "convert", "reset", "saveRoll", "loadRoll"];
const REQUIRED_UI_IDS = CONTROL_IDS.concat(ACTION_IDS, [
  "profile", "borderValue", "exposureValue", "contrastValue", "gammaValue",
  "saturationValue", "warmthValue", "baseValue", "confidenceValue", "sourceValue",
  "status", "progress", "readinessValue"
]);

const state = {
  analysis: null,
  sourceDocumentId: null,
  sourceLayerId: null,
  sourceLayerName: null,
  busy: false,
  busyAction: null,
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
    try { await app.showAlert(message); } catch (_) { /* Status text remains visible. */ }
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
  if (state.busy) {
    readiness.textContent = state.busyAction === "analyze"
      ? "正在分析胶片基底，请勿切换文档或图层"
      : "正在生成正片，请勿切换文档或图层";
    readiness.className = "readiness busy";
  } else if (state.analysis) {
    readiness.textContent = "已完成基底分析，可以生成正片";
    readiness.className = "readiness ready";
  } else {
    readiness.textContent = "请先完成第 1 步：分析胶片基底";
    readiness.className = "readiness";
  }
}

function setBusy(busy, action) {
  state.busy = busy;
  state.busyAction = busy ? action || null : null;
  ACTION_IDS.forEach(function (id) {
    const element = byId(id);
    if (element) element.disabled = busy;
  });
  const convertButton = byId("convert");
  if (convertButton) {
    convertButton.textContent = busy && state.busyAction === "convert"
      ? "正在生成，请稍候…"
      : "生成正片图层";
  }
  updateReadiness();
}

function documentDimensions(doc) {
  return {
    width: Math.max(1, Math.round(numberValue(doc.width))),
    height: Math.max(1, Math.round(numberValue(doc.height)))
  };
}

function previewTarget(width, height) {
  return width >= height ? { width: MAX_PREVIEW_EDGE } : { height: MAX_PREVIEW_EDGE };
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
    exposure: Number(byId("exposure").value) / 100,
    contrast: Number(byId("contrast").value) / 100,
    gamma: Number(byId("gamma").value) / 100,
    saturation: Number(byId("saturation").value) / 100,
    warmth: Number(byId("warmth").value) / 100
  };
}

function applyControls(values) {
  if (!values) return;
  if (values.profile && engine.PROFILES[values.profile]) byId("profile").value = values.profile;
  if (Number.isFinite(values.exposure)) byId("exposure").value = String(Math.round(values.exposure * 100));
  if (Number.isFinite(values.contrast)) byId("contrast").value = String(Math.round(values.contrast * 100));
  if (Number.isFinite(values.gamma)) byId("gamma").value = String(Math.round(values.gamma * 100));
  if (Number.isFinite(values.saturation)) byId("saturation").value = String(Math.round(values.saturation * 100));
  if (Number.isFinite(values.warmth)) byId("warmth").value = String(Math.round(values.warmth * 100));
  refreshOutputs();
}

function refreshOutputs() {
  if (!state.initialized) return;
  byId("borderValue").textContent = byId("borderFraction").value + "%";
  byId("exposureValue").textContent = (Number(byId("exposure").value) / 100).toFixed(2) + " EV";
  byId("contrastValue").textContent = (Number(byId("contrast").value) / 100).toFixed(2);
  byId("gammaValue").textContent = (Number(byId("gamma").value) / 100).toFixed(2);
  byId("saturationValue").textContent = (Number(byId("saturation").value) / 100).toFixed(2);
  byId("warmthValue").textContent = String(Number(byId("warmth").value));
}

function resetControls() {
  applyControls({ profile: "generic", exposure: 0, contrast: 1, gamma: 1, saturation: 1, warmth: 0 });
  byId("borderFraction").value = "7";
  refreshOutputs();
  state.analysis = null;
  state.sourceDocumentId = null;
  state.sourceLayerId = null;
  state.sourceLayerName = null;
  byId("baseValue").textContent = "尚未分析";
  byId("confidenceValue").textContent = "—";
  byId("sourceValue").textContent = "—";
  setStatus("已恢复默认。请重新分析胶片基底。");
  setProgress(0);
  updateReadiness();
}

function ensureSource() {
  if (!app.documents.length) throw new Error("请先在 Photoshop 中打开一张胶片负片。");
  const doc = app.activeDocument;
  if (!doc.activeLayers || !doc.activeLayers.length) throw new Error("请先选择负片所在图层。");
  const layer = doc.activeLayers[0];
  return { doc: doc, layer: layer };
}

async function getPreview(source) {
  const size = documentDimensions(source.doc);
  const requestedBounds = { left: 0, top: 0, right: size.width, bottom: size.height };
  const result = await imaging.getPixels({
    documentID: source.doc.id,
    layerID: source.layer.id,
    sourceBounds: requestedBounds,
    targetSize: previewTarget(size.width, size.height),
    colorSpace: "RGB",
    componentSize: 8,
    applyAlpha: false
  });
  const data = await result.imageData.getData({ chunky: true });
  return {
    result: result,
    data: data,
    width: result.imageData.width,
    height: result.imageData.height,
    components: result.imageData.components,
    requestedBounds: requestedBounds
  };
}

async function analyze(useSelection) {
  if (state.busy) return;
  setBusy(true, "analyze");
  setProgress(0.08);
  setStatus(useSelection ? "正在读取选区与负片像素…" : "正在分析胶片边框…");

  try {
    const borderFraction = Number(byId("borderFraction").value) / 100;
    const result = await core.executeAsModal(async function (executionContext) {
      const source = ensureSource();
      let preview;
      let selectionResult;

      try {
        try { executionContext.reportProgress({ value: 0.12, commandName: "读取负片像素" }); } catch (_) { /* Optional host UI. */ }
        preview = await getPreview(source);
        setProgress(0.35);

        let maskResult;
        if (useSelection) {
          try { executionContext.reportProgress({ value: 0.4, commandName: "读取当前选区" }); } catch (_) { /* Optional host UI. */ }
          selectionResult = await imaging.getSelection({
            documentID: source.doc.id,
            sourceBounds: preview.requestedBounds,
            targetSize: { width: preview.width, height: preview.height }
          });
          const selectionData = await selectionResult.imageData.getData({ chunky: true });
          maskResult = engine.estimateMaskFromSelection(
            preview.data,
            selectionData,
            preview.width,
            preview.height,
            preview.components,
            selectionResult.imageData.components,
            { maxValue: 255, selectionMax: 255 }
          );
        } else {
          maskResult = engine.estimateMaskFromBorder(
            preview.data,
            preview.width,
            preview.height,
            preview.components,
            { maxValue: 255, borderFraction: borderFraction }
          );
        }

        setProgress(0.65);
        try { executionContext.reportProgress({ value: 0.7, commandName: "计算胶片基底" }); } catch (_) { /* Optional host UI. */ }
        const analysis = engine.analysisFromThumbnail(
          preview.data,
          preview.width,
          preview.height,
          preview.components,
          maskResult,
          { maxValue: 255, borderFraction: borderFraction }
        );

        return {
          analysis: analysis,
          sourceDocumentId: source.doc.id,
          sourceLayerId: source.layer.id,
          sourceLayerName: source.layer.name
        };
      } finally {
        if (selectionResult && selectionResult.imageData) selectionResult.imageData.dispose();
        if (preview && preview.result && preview.result.imageData) preview.result.imageData.dispose();
      }
    }, {
      commandName: useSelection ? "从选区采样胶片基底" : "分析胶片基底",
      timeOut: 10
    });

    state.analysis = result.analysis;
    state.sourceDocumentId = result.sourceDocumentId;
    state.sourceLayerId = result.sourceLayerId;
    state.sourceLayerName = result.sourceLayerName;
    byId("baseValue").textContent = displayRGB(result.analysis.base);
    byId("confidenceValue").textContent = Math.round(result.analysis.confidence * 100) + "%" + (useSelection ? "（选区）" : "（边框）");
    byId("sourceValue").textContent = result.sourceLayerName;
    setProgress(1);
    setStatus("分析完成，可以生成正片图层。", "ok");
  } catch (error) {
    state.analysis = null;
    state.sourceDocumentId = null;
    state.sourceLayerId = null;
    state.sourceLayerName = null;
    await reportError(error, true);
  } finally {
    setBusy(false);
  }
}

function validateAnalysisSource(source) {
  if (!state.analysis) throw new Error("请先点击“自动分析边框”，或用选区采样胶片基底，然后再生成正片。");
  if (source.doc.id !== state.sourceDocumentId || source.layer.id !== state.sourceLayerId) {
    throw new Error("当前文档或图层已改变，请重新分析胶片基底。");
  }
}

function tileHeightFor(width, components, componentSize) {
  const bytes = componentSize === 8 ? 1 : componentSize === 16 ? 2 : 4;
  return Math.max(32, Math.min(1024, Math.floor(TARGET_TILE_BYTES / Math.max(1, width * components * bytes * 2))));
}

async function convert() {
  if (state.busy) return;

  let source;
  try {
    source = ensureSource();
    validateAnalysisSource(source);
  } catch (error) {
    await reportError(error, true);
    return;
  }

  setBusy(true, "convert");
  setProgress(0.02);
  setStatus("准备生成正片图层…");

  try {
    const sourceDocId = source.doc.id;
    const sourceLayerId = source.layer.id;
    const sourceName = source.layer.name;
    const controls = currentControls();
    const dimensions = documentDimensions(source.doc);

    await core.executeAsModal(async function (executionContext) {
      const doc = app.activeDocument;
      const outputLayer = await doc.createLayer({ name: "正片 · " + sourceName + " · PS-Sezhao " + VERSION });

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
            sourceData,
            sourceImage.width,
            sourceImage.height,
            sourceImage.components,
            componentSize,
            state.analysis,
            controls,
            controls.profile,
            fullRange
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
        try { executionContext.reportProgress({ value: progress, commandName: "正在生成正片" }); } catch (_) { /* Older hosts may omit progress UI. */ }
      }
    }, { commandName: "胶片去色罩转正", timeOut: 10 });

    setProgress(1);
    setStatus("正片图层已生成，原负片图层未修改。", "ok");
  } catch (error) {
    await reportError(error, true);
  } finally {
    setBusy(false);
  }
}

function saveRoll() {
  try {
    if (!state.analysis) throw new Error("请先完成胶片基底分析，再保存本卷参数。");
    const payload = { version: 1, analysis: state.analysis, controls: currentControls() };
    localStorage.setItem(ROLL_KEY, JSON.stringify(payload));
    setStatus("本卷参数已保存到插件本地。", "ok");
  } catch (error) {
    reportError(error, false);
  }
}

function loadRoll() {
  try {
    const raw = localStorage.getItem(ROLL_KEY);
    if (!raw) throw new Error("尚未保存本卷参数。");
    const payload = JSON.parse(raw);
    if (!payload || payload.version !== 1 || !payload.analysis) throw new Error("保存的本卷参数格式无效。");
    const source = ensureSource();
    state.analysis = payload.analysis;
    state.sourceDocumentId = source.doc.id;
    state.sourceLayerId = source.layer.id;
    state.sourceLayerName = source.layer.name;
    applyControls(payload.controls);
    byId("baseValue").textContent = displayRGB(state.analysis.base);
    byId("confidenceValue").textContent = Math.round(state.analysis.confidence * 100) + "%（本卷）";
    byId("sourceValue").textContent = source.layer.name;
    setStatus("已将本卷参数应用到当前图层。", "ok");
    updateReadiness();
  } catch (error) {
    reportError(error, false);
  }
}

function bindClick(id, handler) {
  byId(id).addEventListener("click", handler);
}

function initializeUI() {
  if (state.initialized) return true;
  const missing = REQUIRED_UI_IDS.filter(function (id) { return !byId(id); });
  if (missing.length) return false;

  CONTROL_IDS.forEach(function (id) {
    byId(id).addEventListener("input", refreshOutputs);
  });
  bindClick("analyzeAuto", function () { analyze(false); });
  bindClick("analyzeSelection", function () { analyze(true); });
  bindClick("convert", convert);
  bindClick("reset", resetControls);
  bindClick("saveRoll", saveRoll);
  bindClick("loadRoll", loadRoll);

  state.initialized = true;
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
