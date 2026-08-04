local LrApplication = import 'LrApplication'
local LrBinding = import 'LrBinding'
local LrDialogs = import 'LrDialogs'
local LrFunctionContext = import 'LrFunctionContext'
local LrPathUtils = import 'LrPathUtils'
local LrProgressScope = import 'LrProgressScope'
local LrTasks = import 'LrTasks'
local LrView = import 'LrView'

local NativeProfiles = dofile(LrPathUtils.child(_PLUGIN.path, 'NativeProfiles.lua'))

local function numberRow(f, bind, title, key, minimum, maximum, precision, suffix)
    return f:row {
        spacing = f:control_spacing(),
        f:static_text {
            title = title,
            width_in_chars = 22,
        },
        f:edit_field {
            value = bind(key),
            min = minimum,
            max = maximum,
            precision = precision,
            width_in_chars = 9,
        },
        f:static_text {
            title = suffix or '',
            width_in_chars = 8,
        },
    }
end

local function showOptions(functionContext, photoCount)
    local f = LrView.osFactory()
    local bind = LrView.bind
    local props = LrBinding.makePropertyTable(functionContext)

    props.profile = 'neutral'
    props.styleStrength = 100
    props.exposure = 0
    props.temperature = 0
    props.tint = 0
    props.contrast = 0
    props.highlights = 0
    props.shadows = 0
    props.whites = 0
    props.blacks = 0
    props.vibrance = 0
    props.saturation = 0
    props.createSnapshot = true
    props.skipApplied = true

    local contents = f:column {
        bind_to_object = props,
        spacing = f:control_spacing(),

        f:static_text {
            title = '直接把反相曲线和颜色参数写入 Lightroom 当前照片。原文件不会改变，调整会显示在“修改照片”模块中。',
            width_in_chars = 72,
            height_in_lines = 3,
        },
        f:static_text {
            title = '将处理 ' .. photoCount .. ' 张所选照片。原生模式速度快且可继续使用 Lightroom 调整；逐像素精度不等同于 16 位 TIFF 模式。',
            width_in_chars = 72,
            height_in_lines = 3,
        },

        f:row {
            spacing = f:control_spacing(),
            f:static_text {
                title = '胶片起始风格',
                width_in_chars = 22,
            },
            f:popup_menu {
                value = bind('profile'),
                items = NativeProfiles.profileItems(),
                width_in_chars = 32,
            },
        },

        numberRow(f, bind, '风格强度', 'styleStrength', 0, 200, 0, '%'),
        numberRow(f, bind, '附加曝光', 'exposure', -5, 5, 2, 'EV'),
        numberRow(f, bind, '附加色温', 'temperature', -100, 100, 0, ''),
        numberRow(f, bind, '附加色调（绿/洋红）', 'tint', -100, 100, 0, ''),
        numberRow(f, bind, '附加对比度', 'contrast', -100, 100, 0, ''),
        numberRow(f, bind, '附加高光', 'highlights', -100, 100, 0, ''),
        numberRow(f, bind, '附加阴影', 'shadows', -100, 100, 0, ''),
        numberRow(f, bind, '附加白色色阶', 'whites', -100, 100, 0, ''),
        numberRow(f, bind, '附加黑色色阶', 'blacks', -100, 100, 0, ''),
        numberRow(f, bind, '附加自然饱和度', 'vibrance', -100, 100, 0, ''),
        numberRow(f, bind, '附加饱和度', 'saturation', -100, 100, 0, ''),

        f:checkbox {
            title = '应用前创建“PS-Sezhao 原生转正前”恢复快照',
            value = bind('createSnapshot'),
        },
        f:checkbox {
            title = '跳过已经应用过 PS-Sezhao 原生反相曲线的照片',
            value = bind('skipApplied'),
        },
    }

    local result = LrDialogs.presentModalDialog {
        title = 'PS-Sezhao：Lightroom 原生直接转正',
        contents = contents,
        actionVerb = '直接应用',
        cancelVerb = '取消',
        resizable = false,
    }

    if result ~= 'ok' then return nil end
    return props
end

local function isVideo(photo)
    local format = tostring(photo:getRawMetadata('fileFormat') or ''):upper()
    return format == 'VIDEO'
end

local function processSelected(functionContext)
    if not LrTasks.canYield() then
        error('PS-Sezhao 原生转正未进入可让出的 Lightroom 后台任务。')
    end

    local catalog = LrApplication.activeCatalog()
    local photos = catalog:getTargetPhotos()
    if not photos or #photos == 0 then
        LrDialogs.message('PS-Sezhao', '请先在图库中选择一张或多张负片。', 'info')
        return
    end

    local options = showOptions(functionContext, #photos)
    if not options then return end

    local progress = LrProgressScope { title = 'PS-Sezhao：直接应用 Lightroom 原生转正' }
    progress:setCancelable(true)

    local snapshotName = NativeProfiles.SNAPSHOT_PREFIX .. ' ' .. os.date('%Y-%m-%d %H:%M:%S')
    local applied = 0
    local skipped = 0
    local failed = {}

    for index, photo in ipairs(photos) do
        if progress:isCanceled() then break end
        progress:setCaption('正在处理 ' .. index .. ' / ' .. #photos)
        progress:setPortionComplete(index - 1, #photos)

        if isVideo(photo) then
            skipped = skipped + 1
        else
            local currentSettings = photo:getDevelopSettings()
            if options.skipApplied and NativeProfiles.isNativeApplied(currentSettings) then
                skipped = skipped + 1
            else
                local newSettings = NativeProfiles.buildSettings(currentSettings, options)
                local ok, err = LrTasks.pcall(function()
                    catalog:withWriteAccessDo('PS-Sezhao 原生直接转正', function()
                        if options.createSnapshot then
                            photo:createDevelopSnapshot(snapshotName, false)
                        end
                        photo:applyDevelopSettings(newSettings, 'PS-Sezhao 原生转正', false)
                    end)
                end)

                if ok then
                    applied = applied + 1
                else
                    table.insert(failed, tostring(err))
                end
            end
        end

        progress:setPortionComplete(index, #photos)
        LrTasks.yield()
    end

    progress:done()

    local message = '已直接应用到 ' .. applied .. ' 张 Lightroom 照片。'
    if options.createSnapshot and applied > 0 then
        message = message .. '\n已为每张照片创建应用前快照。'
    end
    if skipped > 0 then
        message = message .. '\n跳过 ' .. skipped .. ' 张照片（视频或已应用原生转正）。'
    end
    if #failed > 0 then
        message = message .. '\n失败 ' .. #failed .. ' 张：' .. failed[1]
    end
    message = message .. '\n\n可进入“修改照片”模块继续调整；需要逐像素结果时请运行“高精度 16 位 TIFF”。'

    LrDialogs.message(
        #failed > 0 and 'PS-Sezhao 原生转正部分完成' or 'PS-Sezhao 原生转正完成',
        message,
        #failed > 0 and 'warning' or 'info'
    )
end

LrFunctionContext.postAsyncTaskWithContext(
    'PS-Sezhao：Lightroom 原生直接转正',
    function(functionContext)
        local ok, err = LrTasks.pcall(processSelected, functionContext)
        if not ok then
            LrDialogs.message('PS-Sezhao 原生转正错误', tostring(err), 'critical')
        end
    end
)
