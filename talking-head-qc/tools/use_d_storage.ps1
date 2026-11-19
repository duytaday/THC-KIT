# Dot-source for this kit session. Global Windows/app settings are unchanged.
$kitRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $kitRoot.StartsWith('D:\')) { throw 'Open the migrated checkout on D first.' }
$storageRoot = 'D:\.codex\workspaces\talking-head-support'
$runtimeRoot = Join-Path $storageRoot 'runtimes'
$basePython = Join-Path $runtimeRoot 'python312-base\python.exe'
$modelPython = Join-Path $runtimeRoot 'cutroom-animation-model\Scripts\python.exe'
$env:THC_PYTHON = if (Test-Path -LiteralPath $modelPython) { $modelPython } else { $basePython }
$env:THC_MODEL_PYTHON = $modelPython
$env:PYTHONNOUSERSITE='1'
$env:PYTHONUSERBASE=Join-Path $storageRoot 'python-user'
$env:TEMP=Join-Path $storageRoot 'tmp';$env:TMP=$env:TEMP
$env:UV_CACHE_DIR=Join-Path $storageRoot 'cache\uv'
$env:PIP_CACHE_DIR=Join-Path $storageRoot 'cache\pip'
$env:NPM_CONFIG_CACHE=Join-Path $storageRoot 'cache\npm'
$env:HF_HOME=Join-Path $storageRoot 'cache\huggingface'
$env:HF_HUB_CACHE=Join-Path $env:HF_HOME 'hub'
$env:HF_DATASETS_CACHE=Join-Path $env:HF_HOME 'datasets'
$env:XDG_CACHE_HOME=Join-Path $storageRoot 'cache'
$env:TORCH_HOME=Join-Path $storageRoot 'cache\torch'
$env:CUDA_CACHE_PATH=Join-Path $storageRoot 'cache\cuda'
$env:TORCHINDUCTOR_CACHE_DIR=Join-Path $storageRoot 'cache\torchinductor'
$env:TRITON_CACHE_DIR=Join-Path $storageRoot 'cache\triton'
$env:NUMBA_CACHE_DIR=Join-Path $storageRoot 'cache\numba'
$env:MPLCONFIGDIR=Join-Path $storageRoot 'config\matplotlib'
$env:HYPERFRAMES_CACHE_DIR=Join-Path $storageRoot 'cache\hyperframes'
$env:HYPERFRAMES_FONT_CACHE_DIR=Join-Path $env:HYPERFRAMES_CACHE_DIR 'fonts'
$env:HYPERFRAMES_CONFIG_DIR=Join-Path $storageRoot 'config\hyperframes'
$env:HYPERFRAMES_EXTRACT_CACHE_DIR=Join-Path $env:HYPERFRAMES_CACHE_DIR 'frames'
$env:HYPERFRAMES_NO_TELEMETRY='1'
$env:PYTHONPYCACHEPREFIX=Join-Path $storageRoot 'cache\python-bytecode'
$env:PYTHONUTF8='1'
$env:PLAYWRIGHT_BROWSERS_PATH=Join-Path $storageRoot 'cache\playwright'
$projectBins = @((Join-Path $runtimeRoot 'ffmpeg\bin'),(Split-Path $env:THC_PYTHON), (Split-Path $basePython))
$env:PATH=($projectBins -join ';')+';'+$env:PATH
foreach($path in @($env:TEMP,$env:UV_CACHE_DIR,$env:PIP_CACHE_DIR,$env:NPM_CONFIG_CACHE,$env:HF_HUB_CACHE,$env:PYTHONPYCACHEPREFIX,$env:TORCH_HOME,$env:CUDA_CACHE_PATH,$env:TORCHINDUCTOR_CACHE_DIR,$env:TRITON_CACHE_DIR,$env:NUMBA_CACHE_DIR,$env:MPLCONFIGDIR,$env:PYTHONUSERBASE)) { New-Item -ItemType Directory -Path $path -Force | Out-Null }
Write-Output "Kit=$kitRoot; runtime=$env:THC_PYTHON; generated files, cache and temp=$storageRoot"
