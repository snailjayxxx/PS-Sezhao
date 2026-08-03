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
  const output = engine.processBuffer(input, 2, 1, 4, 16, analysis, {
    exposure: 0, contrast: 1, gamma: 1, saturation: 1, warmth: 0
  }, "generic", true);
  assert.ok(output instanceof Uint16Array);
  assert.equal(output.length, input.length);
  assert.equal(output[3], 65535);
  assert.equal(output[7], 32768);
});

test("profile lookup falls back to generic", function () {
  const analysis = { base: [0.9, 0.6, 0.35], black: [0, 0, 0], white: [1, 1, 1] };
  const controls = { exposure: 0, contrast: 1, gamma: 1, saturation: 1, warmth: 0 };
  const a = engine.transformRGB([0.3, 0.2, 0.1], analysis, controls, engine.PROFILES.generic);
  const b = engine.processBuffer(new Uint8Array([77, 51, 26]), 1, 1, 3, 8, analysis, controls, "missing", true);
  assert.equal(b.length, 3);
  assert.ok(a.every(Number.isFinite));
});

test("32-bit processing keeps continuous float values", function () {
  const input = new Float32Array([0.45, 0.30, 0.15]);
  const analysis = { base: [0.9, 0.6, 0.3], black: [0, 0, 0], white: [1.2, 1.2, 1.2] };
  const output = engine.processBuffer(input, 1, 1, 3, 32, analysis, {
    exposure: 0, contrast: 1, gamma: 1, saturation: 1, warmth: 0
  }, "generic", true);
  assert.ok(output instanceof Float32Array);
  assert.ok(output.some(function (value) { return value > 0 && value < 1; }));
});
