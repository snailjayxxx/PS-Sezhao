local M = {}

M.SNAPSHOT_PREFIX = 'PS-Sezhao 原生转正前'

local IDENTITY_CURVE = {
    0, 0,
    64, 64,
    128, 128,
    192, 192,
    255, 255,
}

local INVERT_CURVE = {
    0, 255,
    32, 223,
    64, 191,
    96, 159,
    128, 127,
    160, 95,
    192, 63,
    224, 31,
    255, 0,
}

local PROFILES = {
    neutral = {
        title = '通用 C-41（中性）',
        exposure = 0,
        contrast = 0,
        highlights = -20,
        shadows = 20,
        whites = 0,
        blacks = 0,
        temperature = 0,
        tint = 0,
        vibrance = 5,
        saturation = 0,
        red = { 0, 0, 64, 64, 128, 128, 192, 192, 255, 255 },
        green = { 0, 0, 64, 64, 128, 128, 192, 192, 255, 255 },
        blue = { 0, 0, 64, 64, 128, 128, 192, 192, 255, 255 },
    },
    portra = {
        title = 'Kodak Portra 起始风格',
        exposure = 0.15,
        contrast = -6,
        highlights = -28,
        shadows = 24,
        whites = 5,
        blacks = -4,
        temperature = 12,
        tint = 6,
        vibrance = 10,
        saturation = -5,
        red = { 0, 3, 64, 67, 128, 132, 192, 198, 255, 255 },
        green = { 0, 0, 64, 64, 128, 128, 192, 191, 255, 252 },
        blue = { 0, 0, 64, 59, 128, 122, 192, 187, 255, 250 },
    },
    gold = {
        title = 'Kodak Gold 起始风格',
        exposure = 0.1,
        contrast = 8,
        highlights = -18,
        shadows = 12,
        whites = 8,
        blacks = -8,
        temperature = 18,
        tint = 3,
        vibrance = 12,
        saturation = 8,
        red = { 0, 4, 64, 70, 128, 136, 192, 203, 255, 255 },
        green = { 0, 0, 64, 65, 128, 129, 192, 192, 255, 252 },
        blue = { 0, 0, 64, 57, 128, 118, 192, 181, 255, 245 },
    },
    fuji = {
        title = 'Fujifilm C-41 起始风格',
        exposure = 0.05,
        contrast = 4,
        highlights = -22,
        shadows = 18,
        whites = 3,
        blacks = -6,
        temperature = -5,
        tint = -2,
        vibrance = 10,
        saturation = 2,
        red = { 0, 0, 64, 62, 128, 126, 192, 191, 255, 252 },
        green = { 0, 3, 64, 68, 128, 132, 192, 198, 255, 255 },
        blue = { 0, 2, 64, 66, 128, 132, 192, 196, 255, 255 },
    },
    ecn2 = {
        title = 'ECN-2 低反差起始风格',
        exposure = 0.2,
        contrast = -16,
        highlights = -35,
        shadows = 32,
        whites = -5,
        blacks = 4,
        temperature = 4,
        tint = 2,
        vibrance = 4,
        saturation = -10,
        red = { 0, 2, 64, 66, 128, 130, 192, 194, 255, 253 },
        green = { 0, 1, 64, 65, 128, 129, 192, 193, 255, 252 },
        blue = { 0, 0, 64, 62, 128, 126, 192, 189, 255, 248 },
    },
}

local function clamp(value, minimum, maximum)
    value = tonumber(value) or 0
    if value < minimum then return minimum end
    if value > maximum then return maximum end
    return value
end

local function copyCurve(curve)
    local result = {}
    for index, value in ipairs(curve) do result[index] = value end
    return result
end

local function blendCurve(base, styled, amount)
    local result = {}
    for index = 1, math.min(#base, #styled) do
        if index % 2 == 1 then
            result[index] = base[index]
        else
            result[index] = math.floor(base[index] + (styled[index] - base[index]) * amount + 0.5)
        end
    end
    return result
end

local function addCurrent(current, key, offset, minimum, maximum)
    return clamp((tonumber(current[key]) or 0) + (tonumber(offset) or 0), minimum, maximum)
end

local function adjustedTemperature(currentValue, shift)
    local current = tonumber(currentValue) or 0
    shift = tonumber(shift) or 0

    -- TIFF/JPEG 通常使用 -100..100 的相对温度；RAW 通常返回 Kelvin。
    if math.abs(current) <= 200 then
        return clamp(current + shift, -100, 100)
    end
    return clamp(current + shift * 50, 2000, 50000)
end

function M.profileItems()
    return {
        { title = PROFILES.neutral.title, value = 'neutral' },
        { title = PROFILES.portra.title, value = 'portra' },
        { title = PROFILES.gold.title, value = 'gold' },
        { title = PROFILES.fuji.title, value = 'fuji' },
        { title = PROFILES.ecn2.title, value = 'ecn2' },
    }
end

function M.isNativeApplied(settings)
    settings = settings or {}
    local curve = settings.ExtendedToneCurvePV2012 or settings.ToneCurvePV2012
    if type(curve) ~= 'table' or #curve < 4 then return false end
    return tonumber(curve[1]) == 0
        and (tonumber(curve[2]) or 0) >= 245
        and (tonumber(curve[#curve - 1]) or 0) >= 245
        and (tonumber(curve[#curve]) or 255) <= 10
end

function M.buildSettings(current, options)
    current = current or {}
    options = options or {}
    local profile = PROFILES[options.profile] or PROFILES.neutral
    local strength = clamp(options.styleStrength or 100, 0, 200) / 100

    local redCurve = blendCurve(IDENTITY_CURVE, profile.red, strength)
    local greenCurve = blendCurve(IDENTITY_CURVE, profile.green, strength)
    local blueCurve = blendCurve(IDENTITY_CURVE, profile.blue, strength)

    local settings = {
        EnableToneCurve = true,
        ToneCurveName2012 = 'Custom',
        ToneCurvePV2012 = copyCurve(INVERT_CURVE),
        ExtendedToneCurvePV2012 = copyCurve(INVERT_CURVE),
        ToneCurvePV2012Red = copyCurve(redCurve),
        ToneCurvePV2012Green = copyCurve(greenCurve),
        ToneCurvePV2012Blue = copyCurve(blueCurve),
        ExtendedToneCurvePV2012Red = copyCurve(redCurve),
        ExtendedToneCurvePV2012Green = copyCurve(greenCurve),
        ExtendedToneCurvePV2012Blue = copyCurve(blueCurve),

        Exposure2012 = addCurrent(current, 'Exposure2012', profile.exposure + (tonumber(options.exposure) or 0), -5, 5),
        Contrast2012 = addCurrent(current, 'Contrast2012', profile.contrast + (tonumber(options.contrast) or 0), -100, 100),
        Highlights2012 = addCurrent(current, 'Highlights2012', profile.highlights + (tonumber(options.highlights) or 0), -100, 100),
        Shadows2012 = addCurrent(current, 'Shadows2012', profile.shadows + (tonumber(options.shadows) or 0), -100, 100),
        Whites2012 = addCurrent(current, 'Whites2012', profile.whites + (tonumber(options.whites) or 0), -100, 100),
        Blacks2012 = addCurrent(current, 'Blacks2012', profile.blacks + (tonumber(options.blacks) or 0), -100, 100),
        Vibrance = addCurrent(current, 'Vibrance', profile.vibrance + (tonumber(options.vibrance) or 0), -100, 100),
        Saturation = addCurrent(current, 'Saturation', profile.saturation + (tonumber(options.saturation) or 0), -100, 100),
        Tint = clamp((tonumber(current.Tint) or 0) + profile.tint + (tonumber(options.tint) or 0), -150, 150),
        Temperature = adjustedTemperature(
            current.Temperature,
            profile.temperature + (tonumber(options.temperature) or 0)
        ),
        WhiteBalance = 'Custom',
    }

    return settings
end

return M
