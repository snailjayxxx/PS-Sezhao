"use strict";

const c = require("./runtime-common.js");
const {
  app, imaging, core, engine, state, byId, setStatus, reportError, setProgress,
  updateReadiness, setOperation, displayRGB, currentControls, refreshOutputs,
  schedulePreview, ensureActiveCandidate, storedSource, rememberSource,
  readThumbnail, selectionForThumbnail, deletePreviewInsideModal,
  writePreviewPixels, cacheMatches, findLayer
} = c;

async function analyze(useSelection) {
  if (state.operation || state.previewRendering) return;
  setOperation("analyze");
  setProgress(0.05);
  setStatus(useSelection ? "正在读取选区并分析胶片基底…" : "正在分析胶片边框…");
  try {
    const source = ensureActiveCandidate();
    const edge = Math.max(800, Number(byId("previewEdge").value) || 1200);
    let bundle;
    await core.executeAsModal(async function (executionContext) {
      executionContext.reportProgress({ value: 0.12, commandName: "读取负片缩略图" });
      const thumbnail = await readThumbnail(source, edge);
      const maxValue = engine.maxForComponent(thumbnail.componentSize, thumbnail.fullRange);
      const borderFraction = Number(byId("borderFraction").value) / 100;
      let mask;
      if (useSelection) {
        const selection = await selectionForThumbnail(source, thumbnail);
        mask = engine.estimateMaskFromSelection(
          thumbnail.data, selection.data, thumbnail.width, thumbnail.height,
          thumbnail.components, selection.components,
          { maxValue: maxValue, selectionMax: selection.maxValue }
        );
      } else {
        mask = engine.estimateMaskFromBorder(
          thumbnail.data, thumbnail.width, thumbnail.height, thumbnail.components,
          { maxValue: maxValue, borderFraction: borderFraction }
        );
      }
      executionContext.reportProgress({ value: 0.7, commandName: "计算密度与色罩" });
      const analysis = engine.analysisFromThumbnail(
        thumbnail.data, thumbnail.width, thumbnail.height, thumbnail.components,
        mask, { maxValue: maxValue, borderFraction: borderFraction }
      );
      await deletePreviewInsideModal();
      bundle = { thumbnail: thumbnail, analysis: analysis };
    }, { commandName: useSelection ? "从选区分析胶片基底" : "自动分析胶片基底", timeOut: 10 });

    state.analysis = bundle.analysis;
    state.previewCache = bundle.thumbnail;
    rememberSource(source);
    byId("baseValue").textContent = displayRGB(state.analysis.base);
    byId("confidenceValue").textContent = Math.round(state.analysis.confidence * 100) + "%" + (useSelection ? "（选区）" : "（边框）");
    byId("sourceValue").textContent = source.layer.name;
    refreshOutputs();
    setProgress(1);
    setOperation(null);
    setStatus("分析完成，正在建立可拖动实时预览。", "ok");
    schedulePreview(0);
  } catch (error) {
    state.analysis = null;
    state.previewCache = null;
    setOperation(null);
    await reportError(error, true);
  }
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
        thumbnail.componentSize, state.analysis, controls, controls.profile, thumbnail.fullRange
      );
      const outputImage = await imaging.createImageDataFromBuffer(processed, {
        width: thumbnail.width,
        height: thumbnail.height,
        components: thumbnail.components,
        chunky: true,
        colorSpace: "RGB",
        colorProfile: c.resolveColorProfile(thumbnail, source.doc),
        fullRange: thumbnail.fullRange
      });
      try {
        const layer = await writePreviewPixels(source.doc, outputImage, thumbnail);
        state.previewLayerId = layer.id;
        layer.visible = true;
      } finally {
        outputImage.dispose();
      }
      if (typeof app.updateUI === "function") await app.updateUI();
    }, { commandName: "同步胶片滑块预览", interactive: true, timeOut: 10 });
    setProgress(1);
    setStatus("预览已同步；继续拖动滑块可直接查看结果。", "ok");
  } catch (error) {
    await reportError(error, force);
  } finally {
    state.previewRendering = false;
    updateReadiness();
    if (state.previewQueued) {
      state.previewQueued = false;
      schedulePreview(0);
    }
  }
}

async function togglePreview() {
  if (!state.previewLayerId) return renderPreview(true);
  try {
    const source = storedSource();
    await core.executeAsModal(async function () {
      const layer = findLayer(source.doc, state.previewLayerId);
      if (!layer) throw new Error("实时预览图层已不存在，请重新刷新预览。");
      state.previewVisible = !layer.visible;
      layer.visible = state.previewVisible;
      byId("togglePreview").textContent = state.previewVisible ? "隐藏预览" : "显示预览";
      if (typeof app.updateUI === "function") await app.updateUI();
    }, { commandName: "切换胶片实时预览", interactive: true, timeOut: 10 });
    setStatus(state.previewVisible ? "已显示实时预览。" : "已隐藏实时预览，可查看原始负片。", "ok");
  } catch (error) { await reportError(error, true); }
}

async function removePreview(showStatus) {
  if (!state.previewLayerId) {
    if (showStatus) setStatus("当前没有实时预览图层。");
    return;
  }
  try {
    await core.executeAsModal(deletePreviewInsideModal, { commandName: "移除胶片实时预览", timeOut: 10 });
    if (showStatus) setStatus("实时预览图层已移除。", "ok");
  } catch (error) { await reportError(error, showStatus); }
}

async function neutralizeSelection() {
  if (!state.analysis) return reportError(new Error("请先分析胶片基底，然后框选应当为白色或灰色的区域。"), true);
  if (state.operation || state.previewRendering) return;
  setOperation("analyze");
  setStatus("正在从当前选区计算中性色校正…");
  try {
    const source = storedSource();
    const edge = Number(byId("previewEdge").value) || 1200;
    const controls = currentControls();
    let gain;
    await core.executeAsModal(async function () {
      let thumbnail = state.previewCache;
      if (!cacheMatches(source, edge)) {
        thumbnail = await readThumbnail(source, edge);
        state.previewCache = thumbnail;
      }
      const selection = await selectionForThumbnail(source, thumbnail);
      gain = engine.estimateNeutralGains(
        thumbnail.data, selection.data, thumbnail.width, thumbnail.height,
        thumbnail.components, selection.components, state.analysis, controls,
        controls.profile, {
          maxValue: engine.maxForComponent(thumbnail.componentSize, thumbnail.fullRange),
          selectionMax: selection.maxValue
        }
      );
    }, { commandName: "从选区校正中性色", timeOut: 10 });
    byId("redGain").value = String(Math.round(gain.redGain * 100));
    byId("greenGain").value = String(Math.round(gain.greenGain * 100));
    byId("blueGain").value = String(Math.round(gain.blueGain * 100));
    refreshOutputs();
    setOperation(null);
    setStatus("中性色校正完成，正在同步预览。", "ok");
    schedulePreview(0);
  } catch (error) {
    setOperation(null);
    await reportError(error, true);
  }
}

state.previewRunner = renderPreview;
module.exports = { analyze, renderPreview, togglePreview, removePreview, neutralizeSelection };
