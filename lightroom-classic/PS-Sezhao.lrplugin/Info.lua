return {
    LrSdkVersion = 15.0,
    LrSdkMinimumVersion = 15.4,
    LrToolkitIdentifier = 'com.snailjoss.pssezhao.lightroom',
    LrPluginName = 'PS-Sezhao 胶片去色罩',
    VERSION = { major = 0, minor = 7, revision = 0, build = 4 },

    LrLibraryMenuItems = {
        {
            title = 'PS-Sezhao：原生直接转正所选照片（默认）',
            file = 'ApplyNative.lua',
        },
        {
            title = 'PS-Sezhao：高精度 16 位 TIFF',
            file = 'ProcessSelected.lua',
        },
        {
            title = 'PS-Sezhao：恢复原生转正前状态',
            file = 'RestoreNative.lua',
        },
    },

    LrPluginInfoProvider = 'PluginInfoProvider.lua',
}
