/*
 * PS-Sezhao pure image engine.
 * This file intentionally has no Photoshop dependency so it can be unit-tested with Node.js.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.PSSezhaoEngine = factory();
  }
}(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const EPSILON = 1 / 65535;

  const PROFILES = Object.freeze({
    generic: {
      label: "通用 C-41",
      gamma: [1.00, 1.00, 1.00],
      matrix: [[1.00, 0.00, 0.00], [0.00, 1.00, 0.00], [0.00, 0.00, 1.00]],
      saturation: 1.00,
      contrast: 1.00,
      warmth: 0.00
    },
    portra: {
      label: "Kodak Portra 起始风格",
      gamma: [1.03, 1.00, 0.98],
      matrix: [[1.025, -0.010, -0.015], [-0.010, 1.020, -0.010], [-0.010, -0.015, 1.025]],
      saturation: 0.94,
      contrast: 0.96,
      warmth: 0.08
    },
    gold: {
      label: "Kodak Gold 起始风格",
      gamma: [1.05, 1.00, 0.96],
      matrix: [[1.055, -0.020, -0.035], [-0.005, 1.015, -0.010], [-0.020, -0.010, 1.030]],
      saturation: 1.08,
      contrast: 1.05,
      warmth: 0.16
    },
    fuji: {
      label: "Fujifilm C-41 起始风格",
      gamma: [0.99, 1.02, 1.01],
      matrix: [[1.015, -0.010, -0.005], [-0.015, 1.045, -0.030], [-0.010, -0.020, 1.030]],
      saturation: 1.04,
      contrast: 1.00,
      warmth: -0.04
    },
    ecn2: {
      label: "ECN-2 低反差起始风格",
      gamma: [1.00, 1.00, 1.00],
      matrix: [[1.020, -0.010, -0.010], [-0.010, 1.025, -0.015], [-0.010, -0.010, 1.020]],
      saturation: 0.92,
      contrast: 0.88,
      warmth: 0.02
    }
  });

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function median(values) {
    if (!values.length) return 0;
    const sorted = values.slice().sort(function (a, b) { return a - b; });
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  }

  function percentile(values, fraction) {
    if (!values.length) return 0;
    const sorted = values.slice().sort(function (a, b) { return a - b; });
    const position = clamp(fraction, 0, 1) * (sorted.length - 1);
    const lower = Math.floor(position);
    const upper = Math.ceil(position);
    if (lower === upper) return sorted[lower];
    const weight = position - lower;
    return sorted[lower] * (1 - weight) + sorted[upper] * weight;
  }

  function maxForComponent(componentSize, fullRange) {
    if (componentSize === 8) return 255;
    if (componentSize === 16) return fullRange ? 65535 : 32768;
    return 1;
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

  function estimateMaskFromBorder(data, width, height, components, options) {
    options = options || {};
    const maxValue = options.maxValue || 255;
    const borderFraction = clamp(options.borderFraction || 0.07, 0.02, 0.25);
    const borderX = Math.max(2, Math.round(width * borderFraction));
    const borderY = Math.max(2, Math.round(height * borderFraction));
    const totalPixels = width * height;
    const stride = Math.max(1, Math.floor(Math.sqrt(totalPixels / 120000)));
    const candidates = [];

    for (let y = 0; y < height; y += stride) {
      for (let x = 0; x < width; x += stride) {
        if (x >= borderX && x < width - borderX && y >= borderY && y < height - borderY) continue;
        const index = (y * width + x) * components;
        if (components > 3 && Number(data[index + 3]) / maxValue < 0.25) continue;
        const rgb = normalizedRGB(data, index, maxValue);
        const r = rgb[0], g = rgb[1], b = rgb[2];
        const luma = 0.2126 * r + 0.7152 * g + 0.0722 * b;
        if (luma < 0.10 || luma > 0.998) continue;
        const redDominance = (r - b) + 0.30 * (r - g);
        const chroma = Math.max(r, g, b) - Math.min(r, g, b);
        candidates.push({ r: r, g: g, b: b, score: redDominance + 0.15 * chroma, luma: luma });
      }
    }

    if (candidates.length < 24) {
      throw new Error("边框中没有足够的有效胶片基底像素。请保留橙色边框，或使用选区采样。");
    }

    candidates.sort(function (a, b) { return b.score - a.score; });
    const keepCount = Math.max(24, Math.floor(candidates.length * 0.55));
    const selected = candidates.slice(0, keepCount);
    const rValues = selected.map(function (p) { return p.r; });
    const gValues = selected.map(function (p) { return p.g; });
    const bValues = selected.map(function (p) { return p.b; });
    const base = [median(rValues), median(gValues), median(bValues)];

    const deviations = selected.map(function (p) {
      return (Math.abs(p.r - base[0]) + Math.abs(p.g - base[1]) + Math.abs(p.b - base[2])) / 3;
    });
    const mad = median(deviations);
    const orangeScore = clamp((base[0] - base[2]) * 1.8 + (base[0] - base[1]) * 0.5, 0, 1);
    const consistency = clamp(1 - mad * 8, 0, 1);
    const coverage = clamp(selected.length / 500, 0, 1);
    const confidence = clamp(0.15 + orangeScore * 0.40 + consistency * 0.35 + coverage * 0.10, 0, 1);

    return {
      base: base,
      confidence: confidence,
      sampleCount: selected.length,
      method: "border"
    };
  }

  function estimateMaskFromSelection(data, selection, width, height, components, selectionComponents, options) {
    options = options || {};
    const maxValue = options.maxValue || 255;
    const selectionMax = options.selectionMax || 255;
    const rValues = [], gValues = [], bValues = [];
    const totalPixels = width * height;
    const stride = Math.max(1, Math.floor(Math.sqrt(totalPixels / 150000)));

    for (let y = 0; y < height; y += stride) {
      for (let x = 0; x < width; x += stride) {
        const pixelIndex = y * width + x;
        const maskIndex = pixelIndex * selectionComponents;
        if (Number(selection[maskIndex]) / selectionMax < 0.5) continue;
        const index = pixelIndex * components;
        if (components > 3 && Number(data[index + 3]) / maxValue < 0.25) continue;
        const rgb = normalizedRGB(data, index, maxValue);
        rValues.push(rgb[0]);
        gValues.push(rgb[1]);
        bValues.push(rgb[2]);
      }
    }

    if (rValues.length < 12) {
      throw new Error("当前选区太小，或没有覆盖有效像素。请框选一块未曝光的橙色胶片边框。");
    }

    const base = [median(rValues), median(gValues), median(bValues)];
    const deviations = rValues.map(function (_, index) {
      return (Math.abs(rValues[index] - base[0]) + Math.abs(gValues[index] - base[1]) + Math.abs(bValues[index] - base[2])) / 3;
    });
    const consistency = clamp(1 - median(deviations) * 10, 0, 1);
    const coverage = clamp(rValues.length / 500, 0, 1);

    return {
      base: base,
      confidence: clamp(0.35 + consistency * 0.50 + coverage * 0.15, 0, 1),
      sampleCount: rValues.length,
      method: "selection"
    };
  }

  function density(value, base) {
    return Math.max(0, Math.log(Math.max(base, EPSILON) / Math.max(value, EPSILON)));
  }

  function analyzeToneRange(data, width, height, components, base, options) {
    options = options || {};
    const maxValue = options.maxValue || 255;
    const borderFraction = clamp(options.borderFraction || 0.07, 0, 0.25);
    const marginX = Math.floor(width * borderFraction);
    const marginY = Math.floor(height * borderFraction);
    const totalPixels = width * height;
    const stride = Math.max(1, Math.floor(Math.sqrt(totalPixels / 180000)));
    const channels = [[], [], []];

    for (let y = marginY; y < height - marginY; y += stride) {
      for (let x = marginX; x < width - marginX; x += stride) {
        const index = (y * width + x) * components;
        if (components > 3 && Number(data[index + 3]) / maxValue < 0.25) continue;
        for (let c = 0; c < 3; c++) {
          const value = Number(data[index + c]) / maxValue;
          channels[c].push(density(value, base[c]));
        }
      }
    }

    if (channels[0].length < 32) {
      throw new Error("画面有效像素不足，无法计算转正范围。");
    }

    const black = channels.map(function (values) { return percentile(values, 0.01); });
    const white = channels.map(function (values) { return percentile(values, 0.995); });
    for (let c = 0; c < 3; c++) {
      if (white[c] - black[c] < 0.02) white[c] = black[c] + 0.02;
    }

    return { black: black, white: white, sampleCount: channels[0].length };
  }

  function applyMatrix(rgb, matrix) {
    return [
      rgb[0] * matrix[0][0] + rgb[1] * matrix[0][1] + rgb[2] * matrix[0][2],
      rgb[0] * matrix[1][0] + rgb[1] * matrix[1][1] + rgb[2] * matrix[1][2],
      rgb[0] * matrix[2][0] + rgb[1] * matrix[2][1] + rgb[2] * matrix[2][2]
    ];
  }

  function transformRGB(rgb, analysis, controls, profile) {
    const base = analysis.base;
    const black = analysis.black;
    const white = analysis.white;
    const normalized = [0, 0, 0];

    for (let c = 0; c < 3; c++) {
      const d = density(rgb[c], base[c]);
      const range = Math.max(white[c] - black[c], 0.0001);
      const linear = clamp((d - black[c]) / range, 0, 1);
      normalized[c] = Math.pow(linear, 1 / profile.gamma[c]);
    }

    let out = applyMatrix(normalized, profile.matrix);
    const combinedContrast = profile.contrast * controls.contrast;
    const combinedSaturation = profile.saturation * controls.saturation;
    const combinedWarmth = profile.warmth + controls.warmth;
    const exposureScale = Math.pow(2, controls.exposure);

    for (let c = 0; c < 3; c++) {
      out[c] = (out[c] - 0.5) * combinedContrast + 0.5;
      out[c] = clamp(out[c] * exposureScale, 0, 1);
      out[c] = Math.pow(out[c], 1 / controls.gamma);
    }

    const luma = 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2];
    out = out.map(function (value) { return luma + (value - luma) * combinedSaturation; });
    out[0] += combinedWarmth * 0.055;
    out[1] += combinedWarmth * 0.010;
    out[2] -= combinedWarmth * 0.065;

    return [clamp(out[0], 0, 1), clamp(out[1], 0, 1), clamp(out[2], 0, 1)];
  }

  function processBuffer(data, width, height, components, componentSize, analysis, controls, profileName, fullRange) {
    const maxValue = maxForComponent(componentSize, fullRange !== false);
    const output = makeArrayLike(data, data.length);
    const profile = PROFILES[profileName] || PROFILES.generic;
    const safeControls = {
      exposure: Number(controls.exposure) || 0,
      contrast: clamp(Number(controls.contrast) || 1, 0.1, 3),
      gamma: clamp(Number(controls.gamma) || 1, 0.1, 3),
      saturation: clamp(Number(controls.saturation) || 1, 0, 4),
      warmth: clamp(Number(controls.warmth) || 0, -1, 1)
    };

    const pixelCount = width * height;
    for (let pixel = 0; pixel < pixelCount; pixel++) {
      const index = pixel * components;
      const rgb = normalizedRGB(data, index, maxValue);
      const transformed = transformRGB(rgb, analysis, safeControls, profile);
      if (componentSize === 32) {
        output[index] = transformed[0];
        output[index + 1] = transformed[1];
        output[index + 2] = transformed[2];
      } else {
        output[index] = Math.round(transformed[0] * maxValue);
        output[index + 1] = Math.round(transformed[1] * maxValue);
        output[index + 2] = Math.round(transformed[2] * maxValue);
      }
      for (let c = 3; c < components; c++) output[index + c] = data[index + c];
    }
    return output;
  }

  function analysisFromThumbnail(data, width, height, components, maskResult, options) {
    const tone = analyzeToneRange(data, width, height, components, maskResult.base, options);
    return {
      base: maskResult.base.slice(),
      black: tone.black,
      white: tone.white,
      confidence: maskResult.confidence,
      method: maskResult.method,
      maskSampleCount: maskResult.sampleCount,
      toneSampleCount: tone.sampleCount
    };
  }

  return {
    PROFILES: PROFILES,
    clamp: clamp,
    median: median,
    percentile: percentile,
    maxForComponent: maxForComponent,
    estimateMaskFromBorder: estimateMaskFromBorder,
    estimateMaskFromSelection: estimateMaskFromSelection,
    analyzeToneRange: analyzeToneRange,
    analysisFromThumbnail: analysisFromThumbnail,
    transformRGB: transformRGB,
    processBuffer: processBuffer
  };
}));
