$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$version = (Get-Content (Join-Path $root 'VERSION') -Raw).Trim()
$manifest = Join-Path $root 'plugin/manifest.json'
$releaseDir = Join-Path $root 'release-assets'
$buildDir = Join-Path $root '.build/uxp-package'
$verifyDir = Join-Path $root '.build/uxp-verify'
$target = Join-Path $releaseDir "PS-Sezhao-Photoshop-v$version.ccx"

if (-not (Get-Command uxp -ErrorAction SilentlyContinue)) {
    throw 'Adobe UXP CLI is not installed or is not available on PATH.'
}

Remove-Item $buildDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $verifyDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $buildDir | Out-Null
New-Item -ItemType Directory -Force $releaseDir | Out-Null

& uxp plugin package --manifest $manifest --apps PS --outputPath $buildDir
if ($LASTEXITCODE -ne 0) {
    throw "UXP CLI packaging failed with exit code $LASTEXITCODE."
}

$package = Get-ChildItem -Path $buildDir -Filter '*.ccx' -File -Recurse | Select-Object -First 1
if (-not $package) {
    throw 'UXP CLI completed without producing a .ccx file.'
}

Copy-Item $package.FullName $target -Force
if ((Get-Item $target).Length -le 0) {
    throw 'Generated Photoshop .ccx is empty.'
}

$tempZip = Join-Path $root '.build/PS-Sezhao-Photoshop-package.zip'
Copy-Item $target $tempZip -Force
Expand-Archive -Path $tempZip -DestinationPath $verifyDir -Force
if (-not (Test-Path (Join-Path $verifyDir 'manifest.json'))) {
    throw 'Generated .ccx does not contain manifest.json at its root.'
}

Write-Host "Built Adobe UXP package: $target"
Get-Item $target | Format-List Name, Length, FullName
