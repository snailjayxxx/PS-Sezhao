"use strict";

const IDENTITY_MATRIX = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];

const SCANNER_PROFILE_ORDER = [
  "neutral_lab",
  "hasselblad_flextight_x5",
  "noritsu_hs1800",
  "frontier_sp3000_soft",
  "frontier_sp3000_vivid",
  "archive_flatbed"
];

const SCANNER_PROFILES = {
  neutral_lab: {
    label: "中性实验室 · 干净扫描",
    description: "中性反差和色彩，适合先完成准确转正后再手动调色。",
    gamma: [1.000, 1.000, 1.000], matrix: IDENTITY_MATRIX,
    saturation: 1.00, contrast: 1.00, temperature: 0.00, tint: 0.00
  },
  hasselblad_flextight_x5: {
    label: "Hasselblad Flextight X5 · 高端扫描风格参考",
    description: "偏中性、细腻、微反差清楚，高光保持克制。",
    gamma: [1.010, 1.000, 0.995],
    matrix: [[1.012, -0.006, -0.006], [-0.004, 1.010, -0.006], [-0.004, -0.006, 1.010]],
    saturation: 0.98, contrast: 1.03, temperature: 0.01, tint: 0.005
  },
  noritsu_hs1800: {
    label: "Noritsu HS-1800 · 日系冲扫风格参考",
    description: "肤色略暖、层次柔顺，适合人像和日常照片。",
    gamma: [1.015, 1.000, 0.985],
    matrix: [[1.028, -0.012, -0.016], [-0.008, 1.018, -0.010], [-0.010, -0.012, 1.022]],
    saturation: 1.04, contrast: 1.02, temperature: 0.05, tint: 0.015
  },
  frontier_sp3000_soft: {
    label: "Fujifilm Frontier SP-3000 · 柔和风格参考",
    description: "反差柔和、青绿清爽，适合清淡日系观感。",
    gamma: [0.995, 1.010, 1.015],
    matrix: [[1.010, -0.008, -0.002], [-0.012, 1.030, -0.018], [-0.006, -0.014, 1.020]],
    saturation: 1.02, contrast: 0.96, temperature: -0.025, tint: -0.015
  },
  frontier_sp3000_vivid: {
    label: "Fujifilm Frontier SP-3000 · 浓郁风格参考",
    description: "更鲜明的色彩和反差，适合街拍、旅行和阳光场景。",
    gamma: [1.010, 1.000, 1.000],
    matrix: [[1.030, -0.018, -0.012], [-0.016, 1.050, -0.034], [-0.010, -0.020, 1.030]],
    saturation: 1.10, contrast: 1.08, temperature: 0.00, tint: -0.01
  },
  archive_flatbed: {
    label: "Archive Flatbed · 档案平板扫描",
    description: "低反差、低饱和、保留宽容度，适合作为后期档案底稿。",
    gamma: [1.000, 1.000, 1.000], matrix: IDENTITY_MATRIX,
    saturation: 0.96, contrast: 0.92, temperature: 0.00, tint: 0.00
  }
};

const FILM_PROFILE_ORDER = [
  "generic",
  "kodak_portra_160",
  "kodak_portra_400",
  "kodak_portra_800",
  "kodak_gold_200",
  "kodak_ektar_100",
  "kodak_ultramax_400",
  "fujifilm_pro_400h",
  "fujifilm_superia_400",
  "fujifilm_c200",
  "cinestill_50d",
  "cinestill_800t",
  "kodak_vision3_250d",
  "kodak_vision3_500t",
  "ilford_hp5_plus_400",
  "kodak_trix_400"
];

const FILM_PROFILES = {
  generic: {
    label: "无胶卷风格 · 中性转正",
    description: "不附加胶卷色彩，只执行基础去色罩和转正。",
    gamma: [1.000, 1.000, 1.000], matrix: IDENTITY_MATRIX,
    saturation: 1.00, contrast: 1.00, temperature: 0.00, tint: 0.00
  },
  kodak_portra_160: {
    label: "Kodak Portra 160 · 细腻低饱和",
    description: "柔和反差、细腻肤色和较低饱和度。",
    gamma: [1.020, 1.000, 0.985],
    matrix: [[1.018, -0.006, -0.012], [-0.008, 1.016, -0.008], [-0.006, -0.012, 1.018]],
    saturation: 0.88, contrast: 0.94, temperature: 0.06, tint: 0.02
  },
  kodak_portra_400: {
    label: "Kodak Portra 400 · 柔和人像",
    description: "暖润肤色、柔和高光和均衡的日常人像观感。",
    gamma: [1.030, 1.000, 0.980],
    matrix: [[1.025, -0.010, -0.015], [-0.010, 1.020, -0.010], [-0.010, -0.015, 1.025]],
    saturation: 0.94, contrast: 0.96, temperature: 0.10, tint: 0.025
  },
  kodak_portra_800: {
    label: "Kodak Portra 800 · 暖调高感",
    description: "更暖、更浓的肤色与夜景氛围，保留柔和反差。",
    gamma: [1.040, 1.000, 0.970],
    matrix: [[1.035, -0.012, -0.023], [-0.010, 1.022, -0.012], [-0.014, -0.016, 1.030]],
    saturation: 0.98, contrast: 0.98, temperature: 0.15, tint: 0.03
  },
  kodak_gold_200: {
    label: "Kodak Gold 200 · 暖色复古",
    description: "金黄色调、较高饱和和鲜明的家庭照片观感。",
    gamma: [1.050, 1.000, 0.960],
    matrix: [[1.055, -0.020, -0.035], [-0.005, 1.015, -0.010], [-0.020, -0.010, 1.030]],
    saturation: 1.10, contrast: 1.06, temperature: 0.18, tint: 0.01
  },
  kodak_ektar_100: {
    label: "Kodak Ektar 100 · 高饱和风光",
    description: "红蓝更鲜明、反差较强，适合风光、建筑和产品。",
    gamma: [1.020, 1.000, 0.990],
    matrix: [[1.075, -0.030, -0.045], [-0.015, 1.035, -0.020], [-0.025, -0.020, 1.045]],
    saturation: 1.18, contrast: 1.10, temperature: 0.03, tint: 0.01
  },
  kodak_ultramax_400: {
    label: "Kodak Ultramax 400 · 通用日常",
    description: "暖调、明快、较强饱和，适合旅行和日常快照。",
    gamma: [1.035, 1.000, 0.975],
    matrix: [[1.050, -0.018, -0.032], [-0.010, 1.025, -0.015], [-0.016, -0.014, 1.030]],
    saturation: 1.12, contrast: 1.07, temperature: 0.10, tint: 0.005
  },
  fujifilm_pro_400h: {
    label: "Fujifilm Pro 400H · 清淡粉绿",
    description: "低饱和、柔和反差和清淡粉绿的人像观感。",
    gamma: [0.995, 1.015, 1.010],
    matrix: [[1.010, -0.006, -0.004], [-0.012, 1.035, -0.023], [-0.004, -0.015, 1.019]],
    saturation: 0.92, contrast: 0.94, temperature: -0.02, tint: 0.02
  },
  fujifilm_superia_400: {
    label: "Fujifilm Superia X-TRA 400 · 清爽日常",
    description: "青绿更明显，饱和和反差适中，适合街拍和生活记录。",
    gamma: [0.990, 1.020, 1.010],
    matrix: [[1.015, -0.010, -0.005], [-0.015, 1.045, -0.030], [-0.010, -0.020, 1.030]],
    saturation: 1.06, contrast: 1.02, temperature: -0.04, tint: -0.015
  },
  fujifilm_c200: {
    label: "Fujifilm C200 · 轻复古日常",
    description: "稍柔的反差、清爽蓝绿和轻微暖色复古感。",
    gamma: [1.000, 1.015, 1.005],
    matrix: [[1.018, -0.010, -0.008], [-0.012, 1.038, -0.026], [-0.008, -0.018, 1.026]],
    saturation: 1.03, contrast: 0.98, temperature: 0.02, tint: -0.01
  },
  cinestill_50d: {
    label: "CineStill 50D · 日光电影感",
    description: "日光平衡、细腻、低至中等反差的电影感色彩。",
    gamma: [1.010, 1.000, 0.990],
    matrix: [[1.030, -0.012, -0.018], [-0.010, 1.025, -0.015], [-0.010, -0.018, 1.028]],
    saturation: 1.05, contrast: 0.98, temperature: 0.03, tint: 0.01
  },
  cinestill_800t: {
    label: "CineStill 800T · 钨丝霓虹",
    description: "明显冷调和蓝色夜景倾向，适合霓虹与城市夜拍。",
    gamma: [0.980, 1.000, 1.030],
    matrix: [[1.020, -0.010, -0.010], [-0.015, 1.025, -0.010], [-0.020, -0.020, 1.040]],
    saturation: 1.08, contrast: 1.02, temperature: -0.22, tint: 0.03
  },
  kodak_vision3_250d: {
    label: "Kodak Vision3 250D · 电影日光",
    description: "低反差、柔和高光和自然日光电影色彩。",
    gamma: [1.000, 1.000, 1.000],
    matrix: [[1.020, -0.010, -0.010], [-0.010, 1.025, -0.015], [-0.010, -0.010, 1.020]],
    saturation: 0.92, contrast: 0.88, temperature: 0.04, tint: 0.01
  },
  kodak_vision3_500t: {
    label: "Kodak Vision3 500T · 电影夜景",
    description: "更低反差、冷调阴影和柔和的钨丝夜景观感。",
    gamma: [0.990, 1.000, 1.020],
    matrix: [[1.015, -0.008, -0.007], [-0.010, 1.020, -0.010], [-0.015, -0.012, 1.027]],
    saturation: 0.90, contrast: 0.86, temperature: -0.12, tint: 0.02
  },
  ilford_hp5_plus_400: {
    label: "Ilford HP5 Plus 400 · 经典黑白",
    description: "柔和到中等反差的经典黑白，适合人像和纪实。",
    gamma: [1.030, 1.030, 1.030], matrix: IDENTITY_MATRIX,
    saturation: 0.00, contrast: 1.10, temperature: 0.00, tint: 0.00, monochrome: true
  },
  kodak_trix_400: {
    label: "Kodak Tri-X 400 · 纪实黑白",
    description: "更强反差和更有力量的纪实黑白观感。",
    gamma: [1.060, 1.060, 1.060], matrix: IDENTITY_MATRIX,
    saturation: 0.00, contrast: 1.18, temperature: 0.00, tint: 0.00, monochrome: true
  }
};

const FILM_PROFILE_ALIASES = {
  portra: "kodak_portra_400",
  gold: "kodak_gold_200",
  fuji: "fujifilm_superia_400",
  ecn2: "kodak_vision3_250d"
};

function finiteOr(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function canonicalFilmProfile(value) {
  const raw = String(value || "generic");
  const mapped = FILM_PROFILE_ALIASES[raw] || raw;
  return FILM_PROFILES[mapped] ? mapped : "generic";
}

function canonicalScannerProfile(value) {
  const raw = String(value || "neutral_lab");
  return SCANNER_PROFILES[raw] ? raw : "neutral_lab";
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

function applyMatrix(rgb, matrix) {
  return [
    rgb[0] * matrix[0][0] + rgb[1] * matrix[0][1] + rgb[2] * matrix[0][2],
    rgb[0] * matrix[1][0] + rgb[1] * matrix[1][1] + rgb[2] * matrix[1][2],
    rgb[0] * matrix[2][0] + rgb[1] * matrix[2][1] + rgb[2] * matrix[2][2]
  ];
}

function blendMatrix(matrix, amount) {
  return matrix.map(function (row, rowIndex) {
    return row.map(function (value, columnIndex) {
      const identity = rowIndex === columnIndex ? 1 : 0;
      return identity + (value - identity) * amount;
    });
  });
}

function styleGamma(rgb, gamma, strength) {
  return rgb.map(function (value, index) {
    const effective = 1 + (gamma[index] - 1) * strength;
    return Math.pow(Math.max(0, Math.min(1, value)), 1 / Math.max(0.1, effective));
  });
}

function applyTemperatureTint(rgb, temperature, tint) {
  return [
    rgb[0] * Math.exp(0.30 * temperature + 0.10 * tint),
    rgb[1] * Math.exp(0.03 * temperature - 0.22 * tint),
    rgb[2] * Math.exp(-0.34 * temperature + 0.10 * tint)
  ];
}

function applyOutputTone(value, controls, clamp) {
  const blackShift = controls.blackPoint * 0.18;
  const whiteShift = controls.whitePoint * 0.18;
  const denominator = Math.max(0.10, 1 + whiteShift - blackShift);
  let out = (value - blackShift) / denominator;
  out += controls.shadows * Math.pow(1 - clamp(out, 0, 1), 2) * 0.28;
  out += controls.highlights * Math.pow(clamp(out, 0, 1), 2) * 0.28;
  return out;
}

function apply(engine) {
  if (engine._v060StyleLibraryApplied) return engine;
  const EPSILON = 1 / 65535;
  const profiles = Object.assign({}, FILM_PROFILES);
  Object.keys(FILM_PROFILE_ALIASES).forEach(function (alias) {
    profiles[alias] = FILM_PROFILES[FILM_PROFILE_ALIASES[alias]];
  });

  function safeControls(controls) {
    controls = controls || {};
    const baseAdjust = Array.isArray(controls.baseAdjust) ? controls.baseAdjust : [
      finiteOr(controls.baseAdjustR, 0),
      finiteOr(controls.baseAdjustG, 0),
      finiteOr(controls.baseAdjustB, 0)
    ];
    const legacyWarmth = finiteOr(controls.warmth, 0);
    return {
      exposure: engine.clamp(finiteOr(controls.exposure, 0), -6, 6),
      contrast: engine.clamp(finiteOr(controls.contrast, 1), 0.1, 4),
      gamma: engine.clamp(finiteOr(controls.gamma, 1), 0.1, 4),
      saturation: engine.clamp(finiteOr(controls.saturation, 1), 0, 5),
      temperature: engine.clamp(controls.temperature == null ? legacyWarmth : finiteOr(controls.temperature, 0), -3, 3),
      tint: engine.clamp(finiteOr(controls.tint, 0), -2.5, 2.5),
      styleStrength: engine.clamp(finiteOr(controls.styleStrength, 1), 0, 2.5),
      scannerProfile: canonicalScannerProfile(controls.scannerProfile),
      scannerStrength: engine.clamp(finiteOr(controls.scannerStrength, 1), 0, 2.5),
      redGain: engine.clamp(finiteOr(controls.redGain, 1), 0.1, 4),
      greenGain: engine.clamp(finiteOr(controls.greenGain, 1), 0.1, 4),
      blueGain: engine.clamp(finiteOr(controls.blueGain, 1), 0.1, 4),
      blackPoint: engine.clamp(finiteOr(controls.blackPoint, 0), -1, 1),
      whitePoint: engine.clamp(finiteOr(controls.whitePoint, 0), -1, 1),
      shadows: engine.clamp(finiteOr(controls.shadows, 0), -1, 1),
      highlights: engine.clamp(finiteOr(controls.highlights, 0), -1, 1),
      baseAdjust: baseAdjust.map(function (value) { return engine.clamp(finiteOr(value, 0), -1, 1); })
    };
  }

  function effectiveBase(analysis, controls) {
    return analysis.base.map(function (value, index) {
      return engine.clamp(value + controls.baseAdjust[index], EPSILON, 1.5);
    });
  }

  function transformRGB(rgb, analysis, rawControls, filmProfile) {
    const controls = safeControls(rawControls);
    const film = filmProfile || FILM_PROFILES.generic;
    const scanner = SCANNER_PROFILES[controls.scannerProfile] || SCANNER_PROFILES.neutral_lab;
    const base = effectiveBase(analysis, controls);
    let out = [0, 0, 0];

    for (let channel = 0; channel < 3; channel++) {
      const density = Math.max(0, Math.log(Math.max(base[channel], EPSILON) / Math.max(rgb[channel], EPSILON)));
      const range = Math.max(analysis.white[channel] - analysis.black[channel], 0.0001);
      out[channel] = engine.clamp((density - analysis.black[channel]) / range, 0, 1);
    }

    out = styleGamma(out, scanner.gamma, controls.scannerStrength);
    out = applyMatrix(out, blendMatrix(scanner.matrix, controls.scannerStrength));
    out = styleGamma(out, film.gamma, controls.styleStrength);
    out = applyMatrix(out, blendMatrix(film.matrix, controls.styleStrength));

    const contrast =
      (1 + (scanner.contrast - 1) * controls.scannerStrength) *
      (1 + (film.contrast - 1) * controls.styleStrength) *
      controls.contrast;
    const saturation =
      (1 + (scanner.saturation - 1) * controls.scannerStrength) *
      (1 + (film.saturation - 1) * controls.styleStrength) *
      controls.saturation;
    let styleTemperature = scanner.temperature * controls.scannerStrength + film.temperature * controls.styleStrength;
    let styleTint = scanner.tint * controls.scannerStrength + film.tint * controls.styleStrength;
    if (film.monochrome) {
      styleTemperature = 0;
      styleTint = 0;
    }
    const temperature = styleTemperature + controls.temperature;
    const tint = styleTint + controls.tint;
    const exposureScale = Math.pow(2, controls.exposure);

    for (let channel = 0; channel < 3; channel++) {
      out[channel] = (out[channel] - 0.5) * contrast + 0.5;
      out[channel] = applyOutputTone(out[channel], controls, engine.clamp);
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
    const film = FILM_PROFILES[canonicalFilmProfile(profileName)] || FILM_PROFILES.generic;
    const prepared = safeControls(controls);
    const pixelCount = width * height;
    for (let pixel = 0; pixel < pixelCount; pixel++) {
      const index = pixel * components;
      const transformed = transformRGB(normalizedRGB(data, index, maxValue), analysis, prepared, film);
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
    const film = FILM_PROFILES[canonicalFilmProfile(profileName)] || FILM_PROFILES.generic;
    const samples = [[], [], []];
    const stride = Math.max(1, Math.floor(Math.sqrt(width * height / 80000)));
    for (let y = 0; y < height; y += stride) {
      for (let x = 0; x < width; x += stride) {
        const pixel = y * width + x;
        if (Number(selection[pixel * selectionComponents]) / selectionMax < 0.5) continue;
        const index = pixel * components;
        const transformed = transformRGB(normalizedRGB(data, index, maxValue), analysis, current, film);
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

  engine.PROFILES = Object.freeze(profiles);
  engine.FILM_PROFILES = Object.freeze(FILM_PROFILES);
  engine.SCANNER_PROFILES = Object.freeze(SCANNER_PROFILES);
  engine.FILM_PROFILE_ORDER = Object.freeze(FILM_PROFILE_ORDER.slice());
  engine.SCANNER_PROFILE_ORDER = Object.freeze(SCANNER_PROFILE_ORDER.slice());
  engine.canonicalFilmProfile = canonicalFilmProfile;
  engine.canonicalScannerProfile = canonicalScannerProfile;
  engine.safeControls = safeControls;
  engine.effectiveBase = effectiveBase;
  engine.transformRGB = transformRGB;
  engine.processBuffer = processBuffer;
  engine.estimateNeutralGains = estimateNeutralGains;
  engine._v060StyleLibraryApplied = true;
  return engine;
}

module.exports = {
  apply,
  FILM_PROFILES,
  SCANNER_PROFILES,
  FILM_PROFILE_ORDER,
  SCANNER_PROFILE_ORDER,
  canonicalFilmProfile,
  canonicalScannerProfile
};
