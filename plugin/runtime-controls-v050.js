"use strict";

const CONTROL_SPECS = {
  borderFraction: { factor: 1, step: 1, decimals: 0 },
  styleStrength: { factor: 1, step: 1, decimals: 0 },
  exposure: { factor: 100, step: 0.05, decimals: 2 },
  contrast: { factor: 100, step: 0.01, decimals: 2 },
  gamma: { factor: 100, step: 0.01, decimals: 2 },
  saturation: { factor: 100, step: 0.01, decimals: 2 },
  temperature: { factor: 1, step: 1, decimals: 0 },
  tint: { factor: 1, step: 1, decimals: 0 },
  redGain: { factor: 100, step: 0.01, decimals: 2 },
  greenGain: { factor: 100, step: 0.01, decimals: 2 },
  blueGain: { factor: 100, step: 0.01, decimals: 2 },
  blackPoint: { factor: 1, step: 1, decimals: 0 },
  whitePoint: { factor: 1, step: 1, decimals: 0 },
  shadows: { factor: 1, step: 1, decimals: 0 },
  highlights: { factor: 1, step: 1, decimals: 0 },
  baseAdjustR: { factor: 1, step: 1, decimals: 0 },
  baseAdjustG: { factor: 1, step: 1, decimals: 0 },
  baseAdjustB: { factor: 1, step: 1, decimals: 0 }
};

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function specFor(range) {
  const configured = CONTROL_SPECS[range.id];
  if (configured) return configured;
  const rawStep = Number(range.step || 1);
  return {
    factor: 1,
    step: Number.isFinite(rawStep) && rawStep > 0 ? rawStep : 1,
    decimals: rawStep < 1 ? 2 : 0
  };
}

function rawToDisplay(range, spec) {
  return Number(range.value) / spec.factor;
}

function displayToRaw(value, spec) {
  return value * spec.factor;
}

function formatValue(value, decimals) {
  if (!Number.isFinite(value)) return "";
  return Number(value).toFixed(decimals);
}

function dispatchRange(range) {
  range.dispatchEvent(new Event("input", { bubbles: true }));
  range.dispatchEvent(new Event("change", { bubbles: true }));
}

function enhanceRange(range) {
  if (!range || range.dataset.numericEnhanced === "true") return;
  const spec = specFor(range);
  const minimum = Number(range.min || 0) / spec.factor;
  const maximum = Number(range.max || 100) / spec.factor;

  const wrapper = document.createElement("div");
  wrapper.className = "numeric-stepper";
  wrapper.setAttribute("data-for", range.id || "");

  const minus = document.createElement("button");
  minus.className = "numeric-step-button";
  minus.textContent = "−";
  minus.title = "按一步减少";

  const input = document.createElement("input");
  input.className = "numeric-value-input";
  input.type = "number";
  input.min = String(minimum);
  input.max = String(maximum);
  input.step = String(spec.step);
  input.value = formatValue(rawToDisplay(range, spec), spec.decimals);
  input.setAttribute("aria-label", (range.id || "参数") + " 数值");

  const plus = document.createElement("button");
  plus.className = "numeric-step-button";
  plus.textContent = "+";
  plus.title = "按一步增加";

  wrapper.appendChild(minus);
  wrapper.appendChild(input);
  wrapper.appendChild(plus);
  range.insertAdjacentElement("afterend", wrapper);
  range.dataset.numericEnhanced = "true";

  function syncFromRange() {
    input.value = formatValue(rawToDisplay(range, spec), spec.decimals);
  }

  function commitInput() {
    const parsed = Number(input.value);
    if (!Number.isFinite(parsed)) {
      syncFromRange();
      return;
    }
    const displayValue = clamp(parsed, minimum, maximum);
    const rawValue = clamp(
      displayToRaw(displayValue, spec),
      Number(range.min || 0),
      Number(range.max || 100)
    );
    range.value = String(rawValue);
    input.value = formatValue(displayValue, spec.decimals);
    dispatchRange(range);
  }

  function adjust(direction) {
    const current = rawToDisplay(range, spec);
    input.value = formatValue(clamp(current + spec.step * direction, minimum, maximum), spec.decimals);
    commitInput();
  }

  range.addEventListener("input", syncFromRange);
  range.addEventListener("change", syncFromRange);
  input.addEventListener("change", commitInput);
  input.addEventListener("blur", commitInput);
  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      commitInput();
      input.blur();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      adjust(1);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      adjust(-1);
    }
  });
  minus.addEventListener("click", function () { adjust(-1); });
  plus.addEventListener("click", function () { adjust(1); });
}

function initializeNumericControls() {
  const ranges = document.querySelectorAll('input[type="range"]');
  for (let index = 0; index < ranges.length; index += 1) {
    enhanceRange(ranges[index]);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeNumericControls);
} else {
  initializeNumericControls();
}

module.exports = {
  CONTROL_SPECS,
  clamp,
  specFor,
  rawToDisplay,
  displayToRaw,
  formatValue
};
