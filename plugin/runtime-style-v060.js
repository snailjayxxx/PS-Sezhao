"use strict";

function appendUnique(values, additions) {
  const result = values.slice();
  additions.forEach(function (value) {
    if (result.indexOf(value) < 0) result.push(value);
  });
  return result;
}

function applyCommon(c) {
  if (c._v060StyleCommonApplied) return c;

  const baseCurrentControls = c.currentControls;
  const baseApplyControls = c.applyControls;
  const baseRefreshOutputs = c.refreshOutputs;
  const baseSetOperation = c.setOperation;
  const baseResetControls = c.resetControls;

  c.ADJUSTMENT_IDS = appendUnique(c.ADJUSTMENT_IDS, ["scannerStrength"]);
  c.REQUIRED_UI_IDS = appendUnique(c.REQUIRED_UI_IDS, [
    "scannerProfile",
    "scannerStrength",
    "scannerStrengthValue",
    "styleDescription"
  ]);
  c.DEFAULT_CONTROLS = Object.freeze(Object.assign({}, c.DEFAULT_CONTROLS, {
    profile: "generic",
    scannerProfile: "neutral_lab",
    scannerStrength: 1,
    styleStrength: 1
  }));

  c.currentControls = function currentControls() {
    const values = baseCurrentControls();
    values.profile = c.engine.canonicalFilmProfile(values.profile);
    values.scannerProfile = c.engine.canonicalScannerProfile(c.byId("scannerProfile").value);
    values.scannerStrength = Number(c.byId("scannerStrength").value) / 100;
    return values;
  };

  c.applyControls = function applyControls(values) {
    const normalized = Object.assign({}, c.DEFAULT_CONTROLS, values || {});
    normalized.profile = c.engine.canonicalFilmProfile(normalized.profile);
    normalized.scannerProfile = c.engine.canonicalScannerProfile(normalized.scannerProfile);
    baseApplyControls(normalized);
    if (c.byId("scannerProfile")) c.byId("scannerProfile").value = normalized.scannerProfile;
    if (c.byId("scannerStrength")) {
      const strength = Number.isFinite(Number(normalized.scannerStrength)) ? Number(normalized.scannerStrength) : 1;
      c.byId("scannerStrength").value = String(Math.round(c.engine.clamp(strength, 0, 2.5) * 100));
    }
    c.refreshOutputs();
    refreshDescription(c);
  };

  c.refreshOutputs = function refreshOutputs() {
    baseRefreshOutputs();
    const output = c.byId("scannerStrengthValue");
    const range = c.byId("scannerStrength");
    if (output && range) output.textContent = range.value + "%";
  };

  c.setOperation = function setOperation(operation) {
    baseSetOperation(operation);
    const locked = operation === "render";
    ["scannerProfile", "scannerStrength"].forEach(function (id) {
      const element = c.byId(id);
      if (element) element.disabled = locked;
    });
  };

  c.resetControls = function resetControls() {
    baseResetControls();
    if (c.byId("scannerProfile")) c.byId("scannerProfile").value = "neutral_lab";
    if (c.byId("scannerStrength")) c.byId("scannerStrength").value = "100";
    c.refreshOutputs();
    refreshDescription(c);
    if (c.state.analysis) c.schedulePreview(0);
  };

  c._v060StyleCommonApplied = true;
  return c;
}

function refreshDescription(c) {
  if (!c || !c.byId) return;
  const element = c.byId("styleDescription");
  if (!element) return;
  const scannerKey = c.engine.canonicalScannerProfile(c.byId("scannerProfile").value);
  const filmKey = c.engine.canonicalFilmProfile(c.byId("profile").value);
  const scanner = c.engine.SCANNER_PROFILES[scannerKey];
  const film = c.engine.FILM_PROFILES[filmKey];
  element.textContent = "扫描：" + scanner.description + "\n胶卷：" + film.description;
}

function initializeUI(c) {
  refreshDescription(c);
}

module.exports = { applyCommon, initializeUI, refreshDescription };
