"use strict";

function finiteOr(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function makeArrayLike(source, length) {
  if (source instanceof Uint8Array) return new Uint8Array(length);
  if (source instanceof Uint16Array) return new Uint16Array(length);
  return new Float32Array(length);
}

function normalizedRGB(data, index, maxValue) {
  return [
    Number(data[index]) / maxValue,
    Number(data[index + 1]) / maxValue,
    Number(data[index + 2]) / maxValue
  ];
}

function apply(engine) {
  if (engine._v053WideBaseApplied) return engine;
  const EPSILON = 1 / 65535;

  function safeControls(controls) {
    controls = controls || {};
    const legacyWarmth = finiteOr(controls.warmth, 0);
    const temperature = controls.temperature == null ? legacyWarmth : finiteOr(controls.temperature, 0);
    const baseAdjust = Array.isArray(controls.baseAdjust) ? controls.baseAdjust : [
      finiteOr(controls.baseAdjustR, 0),
      finiteOr(controls.baseAdjustG, 0),
      finiteOr(controls.baseAdjustB, 0)
    ];
    return {
      exposure: engine.clamp(finiteOr(controls.exposure, 0), -6, 6),
      contrast: engine.clamp(finiteOr(controls.contrast, 1), 0.1, 4),
      gamma: engine.clamp(finiteOr(controls.gamma, 1), 0.1, 4),
      saturation: engine.clamp(finiteOr(controls.saturation, 1), 0, 5),
      temperature: engine.clamp(temperature, -3, 3),
      tint: engine.clamp(finiteOr(controls.tint, 0), -2.5, 2.5),
      styleStrength: engine.clamp(finiteOr(controls.styleStrength, 1), 0, 2.5),
      redGain: engine.clamp(finiteOr(controls.redGain, 1), 0.1, 4),
      greenGain: engine.clamp(finiteOr(controls.greenGain, 1), 0.1, 4),
      blueGain: engine.clamp(finiteOr(controls.blueGain, 1), 0.1, 4),
      blackPoint: engine.clamp(finiteOr(controls.blackPoint, 0), -1, 1),
      whitePoint: engine.clamp(finiteOr(controls.whitePoint, 0), -1, 1),
      shadows: engine.clamp(finiteOr(controls.shadows, 0), -1, 1),
      highlights: engine.clamp(finiteOr(controls.highlights, 0), -1, 1),
      baseAdjust: baseAdjust.map(function (value) {
        return engine.clamp(finiteOr(value, 0), -1, 1);
      })
    };
  }

  function effectiveBase(analysis, controls) {
    return analysis.base.map(function (value, index) {
      return engine.clamp(value + controls.baseAdjust[index], EPSILON, 1.5);
    });
  }

  function density(value, base) {
    return Math.max(0, Math.log(Math.max(base, EPSILON) / Math.max(value, EPSILON)));
  }

  function applyMatrix(rgb, matrix) {
    return [
      rgb[0] * matrix[0][0] + rgb[1] * matrix[0][1] + rgb[2] * matrix[0][2],
      rgb[0] * matrix[1][0] + rgb[1] * matrix[1][1] + rgb[2] * matrix[1][2],
      rgb[0] * matrix[2][0] + rgb[1] * matrix[2][1] + rgb[2] * matrix[2][2]
    ];
  }

  function blendMatrix(matrix, amount) {
    return matrix.map(function (row, r) {
      return row.map(function (value, c) {
        const identity = r === c ? 1 : 0;
        return identity + (value - identity) * amount;
      });
    });
  }

  function applyTemperatureTint(rgb, temperature, tint) {
    return [
      rgb[0] * Math.exp(0.30 * temperature + 0.10 * tint),
      rgb[1] * Math.exp(0.03 * temperature - 0.22 * tint),
      rgb[2] * Math.exp(-0.34 * temperature + 0.10 * tint)
    ];
  }

  function applyOutputTone(value, controls) {
    const blackShift = controls.blackPoint * 0.18;
    const whiteShift = controls.whitePoint * 0.18;
    const denominator = Math.max(0.10, 1 + whiteShift - blackShift);
    let out = (value - blackShift) / denominator;
    out += controls.shadows * Math.pow(1 - engine.clamp(out, 0, 1), 2) * 0.28;
    out += controls.highlights * Math.pow(engine.clamp(out, 0, 1), 2) * 0.28;
    return out;
  }

  function transformRGB(rgb, analysis, rawControls, profile) {
    const controls = safeControls(rawControls);
    profile = profile || engine.PROFILES.generic;
    const base = effectiveBase(analysis, controls);
    const normalized = [0, 0, 0];

    for (let channel = 0; channel < 3; channel++) {
      const value = density(rgb[channel], base[channel]);
      const range = Math.max(analysis.white[channel] - analysis.black[channel], 0.0001);
      const linear = engine.clamp((value - analysis.black[channel]) / range, 0, 1);
      const profileGamma = 1 + (profile.gamma[channel] - 1) * controls.styleStrength;
      normalized[channel] = Math.pow(linear, 1 / Math.max(0.1, profileGamma));
    }

    let out = applyMatrix(normalized, blendMatrix(profile.matrix, controls.styleStrength));
    const contrast = (1 + (profile.contrast - 1) * controls.styleStrength) * controls.contrast;
    const saturation = (1 + (profile.saturation - 1) * controls.styleStrength) * controls.saturation;
    const temperature = (profile.temperature || profile.warmth || 0) * controls.styleStrength + controls.temperature;
    const tint = (profile.tint || 0) * controls.styleStrength + controls.tint;
    const exposureScale = Math.pow(2, controls.exposure);

    for (let channel = 0; channel < 3; channel++) {
      out[channel] = (out[channel] - 0.5) * contrast + 0.5;
      out[channel] = applyOutputTone(out[channel], controls);
      out[channel] = engine.clamp(out[channel] * exposureScale, 0, 1);
      out[channel] = Math.pow(out[channel], 1 / controls.gamma);
    }

    const luma = 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2];
    out = out.map(function (value) { return luma + (value - luma) * saturation; });
    out = applyTemperatureTint(out, temperature, tint);
    out[0] *= controls.redGain;
    out[1] *= controls.greenGain;
    out[2] *= controls.blueGain;
    return out.map(function (value) { return engine.clamp(value, 0, 1); });
  }

  function processBuffer(data, width, height, components, componentSize, analysis, controls, profileName, fullRange) {
    const maxValue = engine.maxForComponent(componentSize, fullRange !== false);
    const output = makeArrayLike(data, data.length);
    const profile = engine.PROFILES[profileName] || engine.PROFILES.generic;
    const prepared = safeControls(controls);
    const pixelCount = width * height;
    for (let pixel = 0; pixel < pixelCount; pixel++) {
      const index = pixel * components;
      const transformed = transformRGB(normalizedRGB(data, index, maxValue), analysis, prepared, profile);
      if (componentSize === 32) {
        output[index] = transformed[0];
        output[index + 1] = transformed[1];
        output[index + 2] = transformed[2];
      } else {
        output[index] = Math.round(transformed[0] * maxValue);
        output[index + 1] = Math.round(transformed[1] * maxValue);
        output[index + 2] = Math.round(transformed[2] * maxValue);
      }
      for (let channel = 3; channel < components; channel++) output[index + channel] = data[index + channel];
    }
    return output;
  }

  function estimateNeutralGains(data, selection, width, height, components, selectionComponents, analysis, controls, profileName, options) {
    options = options || {};
    const maxValue = options.maxValue || 255;
    const selectionMax = options.selectionMax || 255;
    const current = safeControls(controls);
    const profile = engine.PROFILES[profileName] || engine.PROFILES.generic;
    const samples = [[], [], []];
    const stride = Math.max(1, Math.floor(Math.sqrt(width * height / 80000)));
    for (let y = 0; y < height; y += stride) {
      for (let x = 0; x < width; x += stride) {
        const pixel = y * width + x;
        if (Number(selection[pixel * selectionComponents]) / selectionMax < 0.5) continue;
        const index = pixel * components;
        const transformed = transformRGB(normalizedRGB(data, index, maxValue), analysis, current, profile);
        for (let channel = 0; channel < 3; channel++) samples[channel].push(transformed[channel]);
      }
    }
    if (samples[0].length < 12) throw new Error("中性点选区太小。请框选白色、灰色或其他应当中性的区域。");
    const average = samples.map(engine.median);
    const target = engine.clamp(0.2126 * average[0] + 0.7152 * average[1] + 0.0722 * average[2], 0.05, 0.95);
    return {
      redGain: engine.clamp(current.redGain * target / Math.max(average[0], 0.01), 0.25, 3),
      greenGain: engine.clamp(current.greenGain * target / Math.max(average[1], 0.01), 0.25, 3),
      blueGain: engine.clamp(current.blueGain * target / Math.max(average[2], 0.01), 0.25, 3),
      sampleCount: samples[0].length,
      sampledRGB: average,
      target: target
    };
  }

  engine.safeControls = safeControls;
  engine.effectiveBase = effectiveBase;
  engine.transformRGB = transformRGB;
  engine.processBuffer = processBuffer;
  engine.estimateNeutralGains = estimateNeutralGains;
  engine._v053WideBaseApplied = true;
  return engine;
}

module.exports = { apply };
