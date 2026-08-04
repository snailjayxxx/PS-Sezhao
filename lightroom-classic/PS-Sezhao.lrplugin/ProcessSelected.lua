local LrApplication = import 'LrApplication'
local LrDialogs = import 'LrDialogs'
local LrExportSession = import 'LrExportSession'
local LrFileUtils = import 'LrFileUtils'
local LrFunctionContext = import 'LrFunctionContext'
local LrPathUtils = import 'LrPathUtils'
local LrProgressScope = import 'LrProgressScope'
local LrTasks = import 'LrTasks'

local function quote(value)
    value = tostring(value or '')
    if WIN_ENV then
        return '"' .. value:gsub('"', '\\"') .. '"'
    end
    return "'" .. value:gsub("'", "'\\''") .. "'"
end

local function jsonEscape(value)
    return tostring(value or '')
        :gsub('\\', '\\\\')
        :gsub('"', '\\"')
        :gsub('\b', '\\b')
        :gsub('\f', '\\f')
        :gsub('\n', '\\n')
        :gsub('\r', '\\r')
        :gsub('\t', '\\t')
end

local function writeJob(path, items, resultManifest)
    local file, err = io.open(path, 'w')
    if not file then
        error('无法创建任务文件：' .. tostring(err))
    end
    file:write('{\n  "version": 1,\n  "bit_depth": 16,\n  "result_manifest": "')
    file:write(jsonEscape(resultManifest))
    file:write('",\n  "items": [\n')
    for index, item in ipairs(items) do
        file:write('    {"input": "' .. jsonEscape(item.input) .. '", "output": "' .. jsonEscape(item.output) .. '", "bit_depth": 16}')
        if index < #items then file:write(',') end
        file:write('\n')
    end
    file:write('  ],\n  "settings": {}\n}\n')
    file:close()
end

local function readLines(path)
    local values = {}
    local file = io.open(path, 'r')
    if not file then return values end
    for line in file:lines() do
        if line and line ~= '' then table.insert(values, line) end
    end
    file:close()
    return values
end

local function enginePath()
    if WIN_ENV then
        return LrPathUtils.child(_PLUGIN.path, 'bin/windows-x64/PS-Sezhao.exe')
    end
    return LrPathUtils.child(_PLUGIN.path, 'bin/macos-arm64/PS-Sezhao.app/Contents/MacOS/PS-Sezhao')
end

local function safeStem(path)
    local leaf = LrPathUtils.leafName(path) or 'negative'
    return leaf:gsub('%.[^%.]+$', ''):gsub('[^%w%._%-]', '_')
end

local function finishProgress(progress)
    if progress then
        pcall(function() progress:done() end)
    end
end

local function processSelected(functionContext)
    -- LrExportSession:renditions() 会在内部创建 rendition 任务，绝不能从菜单的主 UI
    -- 调用栈直接进入。postAsyncTaskWithContext 已经创建后台任务；这里再主动让出一次
    -- 调度，确保 Lightroom 完全离开菜单回调后再开始导出。
    if not LrTasks.canYield() then
        error('PS-Sezhao 未能进入 Lightroom 后台任务，请重新启动 Lightroom Classic 后再试。')
    end
    LrTasks.yield()

    local catalog = LrApplication.activeCatalog()
    local photos = catalog:getTargetPhotos()
    if not photos or #photos == 0 then
        LrDialogs.message('PS-Sezhao', '请先在图库中选择一张或多张负片。', 'info')
        return
    end

    local executable = enginePath()
    if not LrFileUtils.exists(executable) then
        LrDialogs.message(
            'PS-Sezhao 本地处理器缺失',
            '当前 Lightroom 插件包中没有找到对应平台的处理器。请从同一 Release 下载 macOS arm64 或 Windows x64 版本并重新安装。',
            'critical'
        )
        return
    end

    local tempRoot = LrPathUtils.child(
        LrPathUtils.getStandardFilePath('temp'),
        'PS-Sezhao-' .. os.date('%Y%m%d-%H%M%S')
    )
    local renderDir = LrPathUtils.child(tempRoot, 'rendered')
    LrFileUtils.createAllDirectories(renderDir)

    local progress = LrProgressScope { title = 'PS-Sezhao：渲染所选负片' }
    progress:setCancelable(true)

    local exportSettings = {
        LR_export_destinationType = 'specificFolder',
        LR_export_destinationPathPrefix = renderDir,
        LR_export_useSubfolder = false,
        LR_collisionHandling = 'overwrite',
        LR_format = 'TIFF',
        LR_export_bitDepth = 16,
        LR_tiff_compressionMethod = 'compressionMethod_ZIP',
        LR_colorSpace = 'ProPhotoRGB',
        LR_size_doConstrain = false,
        LR_outputSharpeningOn = false,
        LR_reimportExportedPhoto = false,
        LR_minimizeEmbeddedMetadata = false,
    }

    local exportSession = LrExportSession {
        photosToExport = photos,
        exportSettings = exportSettings,
    }

    local items = {}
    local completed = 0
    local renditionOptions = {
        stopIfCanceled = true,
        progressScope = progress,
        renderProgressPortion = 0.55,
    }

    for _, rendition in exportSession:renditions(renditionOptions) do
        if progress:isCanceled() then break end
        local success, renderedPath = rendition:waitForRender()
        if not success then
            finishProgress(progress)
            LrDialogs.message('PS-Sezhao 渲染失败', tostring(renderedPath), 'critical')
            return
        end

        local originalPath = rendition.photo:getRawMetadata('path')
        local originalFolder = LrPathUtils.parent(originalPath)
        local outputFolder = LrPathUtils.child(originalFolder, 'PS-Sezhao')
        LrFileUtils.createAllDirectories(outputFolder)
        local outputPath = LrPathUtils.child(outputFolder, safeStem(originalPath) .. '_PS-Sezhao.tif')
        table.insert(items, { input = renderedPath, output = outputPath })
        completed = completed + 1
        progress:setPortionComplete(completed, #photos)
        progress:setCaption('已渲染 ' .. completed .. ' / ' .. #photos)
    end

    if #items == 0 then
        finishProgress(progress)
        return
    end

    local jobPath = LrPathUtils.child(tempRoot, 'job.json')
    local resultManifest = LrPathUtils.child(tempRoot, 'outputs.txt')
    writeJob(jobPath, items, resultManifest)
    progress:setCaption('正在打开 PS-Sezhao 调整窗口…')

    local command = quote(executable) .. ' --lr-job ' .. quote(jobPath)
    local exitCode = LrTasks.execute(command)
    if exitCode ~= 0 then
        finishProgress(progress)
        LrDialogs.message('PS-Sezhao 处理失败', '本地处理器退出代码：' .. tostring(exitCode), 'critical')
        return
    end

    local outputPaths = readLines(resultManifest)
    if #outputPaths == 0 then
        finishProgress(progress)
        LrDialogs.message('PS-Sezhao', '没有检测到输出文件，可能在调整窗口中取消了任务。', 'warning')
        return
    end

    progress:setCaption('正在将正片导入 Lightroom Classic…')
    local imported = 0
    catalog:withWriteAccessDo('导入 PS-Sezhao 正片', function()
        for _, path in ipairs(outputPaths) do
            if LrFileUtils.exists(path) then
                catalog:addPhoto(path)
                imported = imported + 1
            end
        end
    end)

    finishProgress(progress)
    LrDialogs.message(
        'PS-Sezhao 完成',
        '已生成并导入 ' .. imported .. ' 张 16 位 TIFF。\n输出位于原图目录下的 PS-Sezhao 文件夹。',
        'info'
    )
end

LrFunctionContext.postAsyncTaskWithContext(
    'PS-Sezhao：转正所选负片',
    function(functionContext)
        local ok, err = pcall(function()
            processSelected(functionContext)
        end)
        if not ok then
            LrDialogs.message('PS-Sezhao 错误', tostring(err), 'critical')
        end
    end
)
