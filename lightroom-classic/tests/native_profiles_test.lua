local profilePath = arg[1]
assert(profilePath, 'NativeProfiles.lua path is required')

local profiles = dofile(profilePath)

local current = {
    Exposure2012 = 0.25,
    Contrast2012 = 5,
    Highlights2012 = -10,
    Shadows2012 = 5,
    Whites2012 = 0,
    Blacks2012 = 0,
    Vibrance = 2,
    Saturation = 0,
    Temperature = 0,
    Tint = 0,
}

local settings = profiles.buildSettings(current, {
    profile = 'portra',
    styleStrength = 100,
    exposure = 0.1,
    temperature = 5,
    tint = 2,
})

assert(settings.EnableToneCurve == true)
assert(settings.ToneCurveName2012 == 'Custom')
assert(type(settings.ExtendedToneCurvePV2012) == 'table')
assert(settings.ExtendedToneCurvePV2012[1] == 0)
assert(settings.ExtendedToneCurvePV2012[2] == 255)
assert(settings.ExtendedToneCurvePV2012[#settings.ExtendedToneCurvePV2012 - 1] == 255)
assert(settings.ExtendedToneCurvePV2012[#settings.ExtendedToneCurvePV2012] == 0)
assert(type(settings.ExtendedToneCurvePV2012Red) == 'table')
assert(type(settings.ExtendedToneCurvePV2012Green) == 'table')
assert(type(settings.ExtendedToneCurvePV2012Blue) == 'table')
assert(settings.WhiteBalance == 'Custom')
assert(settings.Exposure2012 > current.Exposure2012)
assert(profiles.isNativeApplied(settings))

local zeroStyle = profiles.buildSettings({}, {
    profile = 'gold',
    styleStrength = 0,
})
assert(zeroStyle.ExtendedToneCurvePV2012Red[4] == 64)
assert(zeroStyle.ExtendedToneCurvePV2012Green[4] == 64)
assert(zeroStyle.ExtendedToneCurvePV2012Blue[4] == 64)

local items = profiles.profileItems()
assert(#items == 5)

print('Lightroom native profile tests passed')
