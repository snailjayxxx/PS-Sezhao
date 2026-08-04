local LrApplication = import 'LrApplication'
local LrDialogs = import 'LrDialogs'
local LrFunctionContext = import 'LrFunctionContext'
local LrPathUtils = import 'LrPathUtils'
local LrProgressScope = import 'LrProgressScope'
local LrTasks = import 'LrTasks'

local NativeProfiles = dofile(LrPathUtils.child(_PLUGIN.path, 'NativeProfiles.lua'))

local function findLatestSnapshot(photo)
    local snapshots = photo:getDevelopSnapshots() or {}
    local latest = nil
    for _, snapshot in ipairs(snapshots) do
        local name = tostring(snapshot.name or '')
        if name:sub(1, #NativeProfiles.SNAPSHOT_PREFIX) == NativeProfiles.SNAPSHOT_PREFIX then
            latest = snapshot
        end
    end
    return latest
end

local function restoreSelected()
    local catalog = LrApplication.activeCatalog()
    local photos = catalog:getTargetPhotos()
    if not photos or #photos == 0 then
        LrDialogs.message('PS-Sezhao', '请先选择一张或多张照片。', 'info')
        return
    end

    local progress = LrProgressScope { title = 'PS-Sezhao：恢复原生转正前状态' }
    local restored = 0
    local missing = 0
    local failed = 0

    for index, photo in ipairs(photos) do
        progress:setCaption('正在恢复 ' .. index .. ' / ' .. #photos)
        local snapshot = findLatestSnapshot(photo)
        if not snapshot then
            missing = missing + 1
        else
            local ok = LrTasks.pcall(function()
                catalog:withWriteAccessDo('恢复 PS-Sezhao 原生转正前状态', function()
                    photo:applyDevelopSnapshot(snapshot.snapshotID)
                end)
            end)
            if ok then restored = restored + 1 else failed = failed + 1 end
        end
        progress:setPortionComplete(index, #photos)
        LrTasks.yield()
    end

    progress:done()
    local message = '已恢复 ' .. restored .. ' 张照片。'
    if missing > 0 then message = message .. '\n' .. missing .. ' 张没有找到 PS-Sezhao 应用前快照。' end
    if failed > 0 then message = message .. '\n' .. failed .. ' 张恢复失败。' end
    LrDialogs.message('PS-Sezhao 恢复完成', message, failed > 0 and 'warning' or 'info')
end

LrFunctionContext.postAsyncTaskWithContext(
    'PS-Sezhao：恢复原生转正前状态',
    function(_functionContext)
        local ok, err = LrTasks.pcall(restoreSelected)
        if not ok then
            LrDialogs.message('PS-Sezhao 恢复错误', tostring(err), 'critical')
        end
    end
)
