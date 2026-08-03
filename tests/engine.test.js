"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const engine = require("../plugin/engine.js");

function syntheticNegative(width, height, base) {
  const data = new Uint8Array(width * height * 3);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const index = (y * width + x) * 3;
      const border = x < 8 || y < 8 || x >= width - 8 || y >= height - 8;
      if (border) {
        data[index] = base[0];
        data[index + 1] = base[1];
        data[index + 2] = base[2];
      } else {
        const fx = (x - 8) / Math.max(1, width - 16);
        const fy = (y - 8) / Math.max(1, height - 16);
        data[index] = Math.round(base[0] * (0.25 + 0.65 * fx));
        data[index + 1] = Math.round(base[1] * (0.20 + 0.70 * fy));
        data[index + 2] = Math.round(base[2] * (0.18 + 0.72 * (1 - fx)));
      }
    }
  }
  return data;
}

function defaultControls(extra) {
  return Object.assign({
    exposure: 0,
    contrast: 1,
    gamma: 1,
    saturation: 1,
    temperature: 0,
    tint: 0,
    styleStrength: 1,
    redGain: 1,
    greenGain: 1,
    blueGain: 1,
    blackPoint: 0,
    whitePoint: 0,
    shadows: 0,
    highlights: 0,
    baseAdjust: [0, 0, 0]
  }, extra || {});
}

test("border estimator finds an orange film base", function () {
  const data = syntheticNegative(100, 80, [230, 150, 85]);
  const result = engine.estimateMaskFromBorder(data, 100, 80, 3, { maxValue: 255, borderFraction: 0.1 });
  assert.ok(Math.abs(result.base[0] * 255 - 230) < 3);
  assert.ok(Math.abs(result.base[1] * 255 - 150) < 3);
  assert.ok(Math.abs(result.base[2] * 255 - 85) < 3);
  assert.ok(result.confidence > 0.65);
});

test("density analysis returns ordered black and white points", function () {
  const data = syntheticNegative(120, 90, [232, 154, 88]);
  const mask = engine.estimateMaskFromBorder(data, 120, 90, 3, { maxValue: 255, borderFraction: 0.1 });
  const analysis = engine.analysisFromThumbnail(data, 120, 90, 3, mask, { maxValue: 255, borderFraction: 0.1 });
  analysis.white.forEach(function (value, index) {
    assert.ok(value > analysis.black[index]);
  });
});

test("processing preserves type, length and alpha", function () {
  const input = new Uint16Array([
    50000, 30000, 16000, 65535,
    12000, 9000, 7000, 32768
  ]);
  const analysis = {
    base: [50000 / 65535, 30000 / 65535, 16000 / 65535],
    black: [0, 0, 0],
    white: [1.5, 1.2, 0.9]
  };
  const output = engine.processBuffer(input, 2, 1, 4, 16, analysis, defaultControls(), "generic", true);
  assert.ok(output instanceof Uint16Array);
  assert.equal(output.length, input.length);
  assert.equal(output[3], 65535);
  assert.equal(output[7], 32768);
});

test("profile lookup falls back to generic", function () {
  const analysis = { base: [0.9, 0.6, 0.35], black: [0, 0, 0], white: [1, 1, 1] };
  const controls = defaultControls();
  const a = engine.transformRGB([0.3, 0.2, 0.1], analysis, controls, engine.PROFILES.generic);
  const b = engine.processBuffer(new Uint8Array([77, 51, 26]), 1, 1, 3, 8, analysis, controls, "missing", true);
  assert.equal(b.length, 3);
  assert.ok(a.every(Number.isFinite));
});

test("32-bit processing keeps continuous float values", function () {
  const input = new Float32Array([0.45, 0.30, 0.15]);
  const analysis = { base: [0.9, 0.6, 0.3], black: [0, 0, 0], white: [1.2, 1.2, 1.2] };
  const output = engine.processBuffer(input, 1, 1, 3, 32, analysis, defaultControls(), "generic", true);
  assert.ok(output instanceof Float32Array);
  assert.ok(output.some(function (value) { return value > 0 && value < 1; }));
});

test("temperature has a strong warm and cool range", function () {
  const analysis = { base: [0.95, 0.75, 0.5], black: [0, 0, 0], white: [1.5, 1.5, 1.5] };
  const rgb = [0.35, 0.28, 0.18];
  const cool = engine.transformRGB(rgb, analysis, defaultControls({ temperature: -2 }), engine.PROFILES.generic);
  const warm = engine.transformRGB(rgb, analysis, defaultControls({ temperature: 2 }), engine.PROFILES.generic);
  assert.ok(warm[0] > cool[0], "warming should increase red output");
  assert.ok(warm[2] < cool[2], "warming should reduce blue output");
  assert.ok((warm[0] - warm[2]) - (cool[0] - cool[2]) > 0.25, "temperature range should be visibly strong");
});

test("tint and RGB gains provide independent channel control", function () {
  const analysis = { base: [0.9, 0.65, 0.4], black: [0, 0, 0], white: [1.2, 1.2, 1.2] };
  const rgb = [0.45, 0.30, 0.18];
  const neutral = engine.transformRGB(rgb, analysis, defaultControls(), engine.PROFILES.generic);
  const adjusted = engine.transformRGB(rgb, analysis, defaultControls({ tint: 1, redGain: 1.3, blueGain: 0.7 }), engine.PROFILES.generic);
  assert.ok(adjusted[0] > neutral[0]);
  assert.ok(adjusted[1] < neutral[1]);
  assert.ok(adjusted[2] < neutral[2]);
});

test("base offsets modify the conversion without mutating analysis", function () {
  const analysis = { base: [0.9, 0.6, 0.35], black: [0, 0, 0], white: [1.2, 1.2, 1.2] };
  const before = analysis.base.slice();
  const a = engine.transformRGB([0.4, 0.25, 0.12], analysis, defaultControls(), engine.PROFILES.generic);
  const b = engine.transformRGB([0.4, 0.25, 0.12], analysis, defaultControls({ baseAdjust: [0.08, 0, -0.04] }), engine.PROFILES.generic);
  assert.deepEqual(analysis.base, before);
  assert.notDeepEqual(a.map(v => v.toFixed(5)), b.map(v => v.toFixed(5)));
});

test("style strength zero neutralizes the profile look", function () {
  const analysis = { base: [0.9, 0.6, 0.35], black: [0, 0, 0], white: [1.2, 1.2, 1.2] };
  const rgb = [0.4, 0.24, 0.13];
  const generic = engine.transformRGB(rgb, analysis, defaultControls({ styleStrength: 0 }), engine.PROFILES.generic);
  const portraZero = engine.transformRGB(rgb, analysis, defaultControls({ styleStrength: 0 }), engine.PROFILES.portra);
  generic.forEach(function (value, index) {
    assert.ok(Math.abs(value - portraZero[index]) < 1e-9);
  });
});

test("neutral selection estimates gains that reduce channel imbalance", function () {
  const width = 20, height = 20;
  const data = new Uint8Array(width * height * 3);
  const selection = new Uint8Array(width * height);
  for (let i = 0; i < width * height; i++) {
    data[i * 3] = 120;
    data[i * 3 + 1] = 90;
    data[i * 3 + 2] = 55;
    selection[i] = 255;
  }
  const analysis = { base: [0.95, 0.72, 0.45], black: [0, 0, 0], white: [1.2, 1.2, 1.2] };
  const result = engine.estimateNeutralGains(data, selection, width, height, 3, 1, analysis, defaultControls(), "generic", { maxValue: 255, selectionMax: 255 });
  assert.ok(result.sampleCount >= 12);
  assert.ok(result.redGain >= 0.25 && result.redGain <= 3);
  assert.ok(result.greenGain >= 0.25 && result.greenGain <= 3);
  assert.ok(result.blueGain >= 0.25 && result.blueGain <= 3);
  const corrected = result.sampledRGB.map(function (value, index) {
    return value * [result.redGain, result.greenGain, result.blueGain][index];
  });
  assert.ok(Math.max(...corrected) - Math.min(...corrected) < 0.08);
});
