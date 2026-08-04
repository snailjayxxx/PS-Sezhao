return {
    LrSdkVersion = 15.0,
    LrSdkMinimumVersion = 15.4,
    LrToolkitIdentifier = 'com.snailjoss.pssezhao.lightroom',
    LrPluginName = 'PS-Sezhao 胶片去色罩',
    VERSION = { major = 0, minor = 3, revision = 3, build = 0 },

    LrLibraryMenuItems = {
        {
            title = 'PS-Sezhao：转正所选负片',
            file = 'ProcessSelected.lua',
        },
    },

    LrPluginInfoProvider = 'PluginInfoProvider.lua',
}
