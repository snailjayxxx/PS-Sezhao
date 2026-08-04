"use strict";

const c = require("./runtime-common.js");
const { state, byId } = c;

function setMessage(message, kind) {
  const el = byId("panelPreviewMessage");
  if (!el) return;
  el.textContent = message;
  el.className = "panel-preview-message" + (kind ? " " + kind : "");
}

function applyZoom() {
  const img = byId("panelPreviewImage");
  const stage = byId("panelPreviewStage");
  const select = byId("panelPreviewZoom");
  if (!img || !stage || !select || !state.panelPreviewMeta) return;

  const mode = select.value;
  stage.className = "panel-preview-stage zoom-" + mode + (state.panelPreviewExpanded ? " expanded" : "") + (state.panelPreviewMeta ? " has-image" : "") + (state.pickerMode ? " picker-active" : "");
  if (mode === "fit") {
    img.style.width = "auto";
    img.style.height = "auto";
    img.style.maxWidth = "100%";
    img.style.maxHeight = "100%";
  } else {
    const scale = mode === "200" ? 2 : 1;
    img.style.maxWidth = "none";
    img.style.maxHeight = "none";
    img.style.width = Math.max(1, Math.round(state.panelPreviewMeta.width * scale)) + "px";
    img.style.height = Math.max(1, Math.round(state.panelPreviewMeta.height * scale)) + "px";
  }
}

function setImage(dataUrl, meta) {
  const img = byId("panelPreviewImage");
  const placeholder = byId("panelPreviewPlaceholder");
  const stage = byId("panelPreviewStage");
  if (!img || !stage) return;
  state.panelPreviewMeta = meta;
  img.src = dataUrl;
  img.style.display = "block";
  if (placeholder) placeholder.style.display = "none";
  stage.classList.add("has-image");
  applyZoom();
  setMessage("大图预览已同步。启动吸管后，可直接点击这里或 Photoshop 画布取样。", "ok");
}

function clear(message) {
  const img = byId("panelPreviewImage");
  const placeholder = byId("panelPreviewPlaceholder");
  const stage = byId("panelPreviewStage");
  state.panelPreviewMeta = null;
  if (img) {
    img.removeAttribute("src");
    img.style.display = "none";
  }
  if (placeholder) {
    placeholder.style.display = "flex";
    placeholder.textContent = message || "分析胶片后显示大图预览";
  }
  if (stage) stage.classList.remove("has-image");
  setMessage(message || "尚未生成预览。");
}

function setLoading(message) {
  setMessage(message || "正在生成大图预览…", "busy");
}

function setError(message) {
  setMessage(message || "大图预览生成失败。", "error");
}

function setPickerActive(active, mode) {
  const img = byId("panelPreviewImage");
  const stage = byId("panelPreviewStage");
  if (img) img.classList.toggle("picker-active", Boolean(active));
  if (stage) stage.classList.toggle("picker-active", Boolean(active));
  if (active) {
    setMessage(mode === "base"
      ? "色罩吸管已启动：点击大图预览中的未曝光橙色胶片，或直接点击 Photoshop 画布。"
      : "中性色吸管已启动：点击大图预览中的白色/灰色区域，或直接点击 Photoshop 画布。", "busy");
  } else if (state.panelPreviewMeta) {
    setMessage("大图预览已同步。可继续拖动滑块，或重新启动吸管。", "ok");
  }
}

function mapEventToDocument(event) {
  const img = byId("panelPreviewImage");
  const meta = state.panelPreviewMeta;
  if (!img || !meta) return null;

  let localX = Number(event.offsetX);
  let localY = Number(event.offsetY);
  if (!Number.isFinite(localX) || !Number.isFinite(localY)) {
    const rect = img.getBoundingClientRect();
    localX = Number(event.clientX) - rect.left;
    localY = Number(event.clientY) - rect.top;
  }
  const shownWidth = Math.max(1, Number(img.clientWidth) || meta.width);
  const shownHeight = Math.max(1, Number(img.clientHeight) || meta.height);
  const x = Math.max(0, Math.min(meta.documentWidth - 1, Math.round(localX / shownWidth * meta.documentWidth)));
  const y = Math.max(0, Math.min(meta.documentHeight - 1, Math.round(localY / shownHeight * meta.documentHeight)));
  return { x: x, y: y };
}

function initialize() {
  const zoom = byId("panelPreviewZoom");
  const expand = byId("panelPreviewExpand");
  if (zoom) zoom.addEventListener("change", applyZoom);
  if (expand) {
    expand.addEventListener("click", function () {
      state.panelPreviewExpanded = !state.panelPreviewExpanded;
      expand.textContent = state.panelPreviewExpanded ? "收起预览" : "放大预览区";
      applyZoom();
    });
  }
  clear("分析胶片后显示大图预览");
}

module.exports = {
  initialize,
  setImage,
  clear,
  setLoading,
  setError,
  setPickerActive,
  mapEventToDocument,
  applyZoom
};
