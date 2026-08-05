local LrPathUtils = import 'LrPathUtils'
local LrFileUtils = import 'LrFileUtils'

local function enginePath()
    if WIN_ENV then
        return LrPathUtils.child(_PLUGIN.path, 'bin/windows-x64/PS-Sezhao.exe')
    end
    return LrPathUtils.child(_PLUGIN.path, 'bin/macos-arm64/PS-Sezhao.app/Contents/MacOS/PS-Sezhao')
end

return {
    sectionsForTopOfDialog = function(f, _propertyTable)
        local path = enginePath()
        local available = LrFileUtils.exists(path)
        return {
            {
                title = 'PS-Sezhao 0.5.2',
                f:row {
                    spacing = f:control_spacing(),
                    f:static_text { title = '适配版本：' },
                    f:static_text { title = 'Lightroom Classic 15.4 及以上' },
                },
                f:row {
                    spacing = f:control_spacing(),
                    f:static_text { title = '原生直接转正：' },
                    f:static_text { title = '可用，不需要本地处理器' },
                },
                f:row {
                    spacing = f:control_spacing(),
                    f:static_text { title = '高精度 TIFF：' },
                    f:static_text { title = available and '本地处理器可用' or '处理器缺失，请重新安装对应平台安装包' },
                },
                f:static_text {
                    title = '高精度窗口支持原图吸管、胶片基底 R/G/B 手动微调，以及完成后仅显示保留范围的新裁切方式。',
                    width_in_chars = 65,
                    height_in_lines = 3,
                },
            },
        }
    end,
}
