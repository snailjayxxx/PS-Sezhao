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
                title = 'PS-Sezhao 0.3.3',
                f:row {
                    spacing = f:control_spacing(),
                    f:static_text { title = '适配版本：' },
                    f:static_text { title = 'Lightroom Classic 15.4 及以上' },
                },
                f:row {
                    spacing = f:control_spacing(),
                    f:static_text { title = '本地处理器：' },
                    f:static_text { title = available and '可用' or '缺失，请重新安装对应平台安装包' },
                },
                f:static_text {
                    title = '从“图库 → 增效工具额外功能”运行。照片只在本机处理。',
                    width_in_chars = 60,
                    height_in_lines = 2,
                },
            },
        }
    end,
}
