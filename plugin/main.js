"use strict";

const { app, imaging, core } = require("photoshop");
const { entrypoints } = require("uxp");
const engine = require("./engine.js");

const VERSION = "0.1.0";
const MAX_PREVIEW_EDGE = 720;
const TARGET_TILE_BYTES = 24 * 1024 * 1024;
const ROLL_KEY = "ps-sezhao-roll-v1";

const state = {
  analysis: null,
  sourceDocumentId: null,
  sourceLayerId: null,
  sourceLayerName: null,
  busy: false,
  initialized: false
};

function byId(id) { return document.getElementById(id); }

function numberValue(value) {
  if (typeof value === "number") return value;
  if (value && typeof value.value === "number") return value.value;
  return Number(value);
}

function setStatus(message, kind) {
  const status = byId("status");
  status.textContent = message;
  status.className = "status" + (kind ? " " + kind : "");
}

function setProgress(value) {
  byId("progress").style.width = Math.round(engine.clamp(value, 0, 1) * 100) + "%";
}

function setBusy(busy) {
  state.busy = busy;
  ["analyzeAuto", "analyzeSelection", "convert", "reset", "saveRoll", "loadRoll"].forEach(function (id) {
    byId(id).disabled = busy;
  });
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
  setStatus("已恢复默认");
  setProgress(0);
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
  const result = await imaging.getPixels({
    documentID: source.doc.id,
    layerID: source.layer.id,
    sourceBounds: { left: 0, top: 0, right: size.width, bottom: size.height },
    targetSize: previewTarget(size.width, size.height),
    colorSpace: "RGB",
    componentSize: 8,
    applyAlpha: false
  });
  const data = await result.imageData.getData({ chunky: true });
  return { result: result, data: data, width: result.imageData.width, height: result.imageData.height, components: result.imageData.components };
}

async function analyze(useSelection) {
  if (state.busy) return;
  setBusy(true);
  setProgress(0.08);
  setStatus(useSelection ? "正在读取选区与负片像素…" : "正在分析胶片边框…");

  let preview;
  let selectionResult;
  try {
    const source = ensureSource();
    preview = await getPreview(source);
    setProgress(0.35);

    let maskResult;
    const borderFraction = Number(byId("borderFraction").value) / 100;
    if (useSelection) {
      selectionResult = await imaging.getSelection({
        documentID: source.doc.id,
        sourceBounds: preview.result.sourceBounds,
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
    const analysis = engine.analysisFromThumbnail(
      preview.data,
      preview.width,
      preview.height,
      preview.components,
      maskResult,
      { maxValue: 255, borderFraction: borderFraction }
    );

    state.analysis = analysis;
    state.sourceDocumentId = source.doc.id;
    state.sourceLayerId = source.layer.id;
    state.sourceLayerName = source.layer.name;
    byId("baseValue").textContent = displayRGB(analysis.base);
    byId("confidenceValue").textContent = Math.round(analysis.confidence * 100) + "%" + (useSelection ? "（选区）" : "（边框）");
    byId("sourceValue").textContent = source.layer.name;
    setProgress(1);
    setStatus("分析完成，可以生成正片图层。", "ok");
  } catch (error) {
    console.error(error);
    setProgress(0);
    setStatus(error && error.message ? error.message : String(error), "error");
  } finally {
    if (preview && preview.result && preview.result.imageData) preview.result.imageData.dispose();
    if (selectionResult && selectionResult.imageData) selectionResult.imageData.dispose();
    setBusy(false);
  }
}

function validateAnalysisSource(source) {
  if (!state.analysis) throw new Error("请先分析胶片基底。");
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
  setBusy(true);
  setProgress(0.02);
  setStatus("准备生成正片图层…");

  try {
    const source = ensureSource();
    validateAnalysisSource(source);
    const sourceDocId = source.doc.id;
    const sourceLayerId = source.layer.id;
    const sourceName = source.layer.name;
    const controls = currentControls();
    const dimensions = documentDimensions(source.doc);

    await core.executeAsModal(async function (executionContext) {
      const doc = app.activeDocument;
      const outputLayer = await doc.createLayer();
      outputLayer.name = "正片 · " + sourceName + " · PS-Sezhao " + VERSION;

      let top = 0;
      let suggestedTileHeight = 256;
      while (top < dimensions.height) {
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

        const outputImage = await imaging.createImageDataFromBuffer(processed, {
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

        outputImage.dispose();
        sourceImage.dispose();
        top = bottom;
        const progress = top / dimensions.height;
        setProgress(progress);
        try { executionContext.reportProgress({ value: progress }); } catch (_) { /* Older hosts may omit progress UI. */ }
      }
    }, { commandName: "胶片去色罩转正" });

    setProgress(1);
    setStatus("正片图层已生成，原负片图层未修改。", "ok");
  } catch (error) {
    console.error(error);
    setProgress(0);
    setStatus(error && error.message ? error.message : String(error), "error");
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
    setStatus(error.message || String(error), "error");
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
  } catch (error) {
    setStatus(error.message || String(error), "error");
  }
}

function initializeUI() {
  if (state.initialized) return;
  state.initialized = true;

  ["borderFraction", "exposure", "contrast", "gamma", "saturation", "warmth"].forEach(function (id) {
    byId(id).addEventListener("input", refreshOutputs);
  });
  byId("analyzeAuto").addEventListener("click", function () { analyze(false); });
  byId("analyzeSelection").addEventListener("click", function () { analyze(true); });
  byId("convert").addEventListener("click", convert);
  byId("reset").addEventListener("click", resetControls);
  byId("saveRoll").addEventListener("click", saveRoll);
  byId("loadRoll").addEventListener("click", loadRoll);
  refreshOutputs();
}

entrypoints.setup({
  panels: {
    sezhaoPanel: {
      show: function () { initializeUI(); }
    }
  }
});

document.addEventListener("DOMContentLoaded", initializeUI);
