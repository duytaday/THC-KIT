# Dot-source for this kit session. Global Windows/app settings are unchanged.
$kitRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $kitRoot.StartsWith('D:\')) { throw 'Open the migrated checkout on D first.' }
$storageRoot = 'D:\.codex\workspaces\talking-head-support'
$env:TEMP=Join-Path $storageRoot 'tmp';$env:TMP=$env:TEMP
$env:UV_CACHE_DIR=Join-Path $storageRoot 'cache\uv'
$env:NPM_CONFIG_CACHE=Join-Path $storageRoot 'cache\npm'
$env:HF_HOME=Join-Path $storageRoot 'cache\huggingface'
$env:HF_HUB_CACHE=Join-Path $env:HF_HOME 'hub'
$env:XDG_CACHE_HOME=Join-Path $storageRoot 'cache'
$env:HYPERFRAMES_CACHE_DIR=Join-Path $storageRoot 'cache\hyperframes'
$env:HYPERFRAMES_FONT_CACHE_DIR=Join-Path $env:HYPERFRAMES_CACHE_DIR 'fonts'
$env:HYPERFRAMES_CONFIG_DIR=Join-Path $storageRoot 'config\hyperframes'
$env:HYPERFRAMES_EXTRACT_CACHE_DIR=Join-Path $env:HYPERFRAMES_CACHE_DIR 'frames'
$env:HYPERFRAMES_NO_TELEMETRY='1'
$env:PYTHONPYCACHEPREFIX=Join-Path $storageRoot 'cache\python-bytecode'
$env:PYTHONUTF8='1'
$env:PLAYWRIGHT_BROWSERS_PATH=Join-Path $storageRoot 'cache\playwright'
foreach($path in @($env:TEMP,$env:UV_CACHE_DIR,$env:NPM_CONFIG_CACHE,$env:HF_HUB_CACHE,$env:PYTHONPYCACHEPREFIX)) { New-Item -ItemType Directory -Path $path -Force | Out-Null }
Write-Output "Kit=$kitRoot; generated files, cache and temp=$storageRoot"
