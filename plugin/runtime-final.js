"use strict";

const c = require("./runtime-common.js");
const {
  imaging, core, engine, state, byId, setStatus, reportError, setProgress,
  setOperation, documentDimensions, cleanColorProfile, currentControls,
  applyControls, updateReadiness, displayRGB, schedulePreview,
  ensureActiveCandidate, storedSource, rememberSource, findLayer,
  deletePreviewInsideModal, tileHeightFor, ROLL_KEY, FINAL_LAYER_PREFIX,
  DEFAULT_CONTROLS
} = c;
const VERSION = "0.5.7";

async function convert() {
  if (state.operation || state.previewRendering) return;
  let source;
  try { source = storedSource(); }
  catch (error) { await reportError(error, true); return; }

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
      const preview = state.previewLayerId ? findLayer(source.doc, state.previewLayerId) : null;
      if (preview) preview.visible = false;
      const output = await source.doc.createLayer({ name: FINAL_LAYER_PREFIX + sourceName + " · PS-Sezhao " + VERSION });
      let top = 0;
      let tileHeight = 256;
      while (top < dimensions.height) {
        if (executionContext.isCancelled) throw new Error("用户已取消生成正片。");
        const bottom = Math.min(dimensions.height, top + tileHeight);
        const result = await imaging.getPixels({
          documentID: sourceDocId,
          layerID: sourceLayerId,
          sourceBounds: { left: 0, top: top, right: dimensions.width, bottom: bottom },
          colorSpace: "RGB",
          componentSize: -1,
          applyAlpha: false
        });
        const sourceImage = result.imageData;
        if (!sourceImage || sourceImage.width < 1 || sourceImage.height < 1) {
          if (sourceImage) sourceImage.dispose();
          top = bottom;
          continue;
        }
        let outputImage;
        try {
          const componentSize = sourceImage.componentSize;
          const fullRange = componentSize === 16;
          tileHeight = tileHeightFor(dimensions.width, sourceImage.components, componentSize);
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
            colorProfile: cleanColorProfile(sourceImage.colorProfile) || cleanColorProfile(source.doc.colorProfileName) || "sRGB IEC61966-2.1",
            fullRange: fullRange
          });
          await imaging.putPixels({
            documentID: sourceDocId,
            layerID: output.id,
            imageData: outputImage,
            replace: false,
            targetBounds: { left: result.sourceBounds.left, top: result.sourceBounds.top },
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
    }, { commandName: "生成最终胶片正片" });

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
    localStorage.setItem(ROLL_KEY, JSON.stringify({
      version: 2,
      analysis: state.analysis,
      controls: currentControls()
    }));
    setStatus("本卷分析与全部校色参数已保存。", "ok");
  } catch (error) { reportError(error, false); }
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
    state.previewGeometryKey = null;
    rememberSource(source);
    applyControls(payload.controls || DEFAULT_CONTROLS);
    byId("baseValue").textContent = displayRGB(state.analysis.base);
    byId("confidenceValue").textContent = Math.round(state.analysis.confidence * 100) + "%（本卷）";
    byId("sourceValue").textContent = source.layer.name;
    updateReadiness();
    setStatus("本卷参数已应用，正在同步画布和大图预览。", "ok");
    schedulePreview(0);
  } catch (error) { await reportError(error, true); }
}

module.exports = { convert, saveRoll, loadRoll };
