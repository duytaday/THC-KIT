param([string]$Python='python',[string]$Data='',[int]$Port=0,[switch]$NoBrowser)
$ErrorActionPreference='Stop'
if(-not $Data){$Data=Join-Path $PSScriptRoot 'output\cutroom-workspace'}
$Data=[IO.Path]::GetFullPath($Data)
$taskCache=Join-Path $Data '.cache'
New-Item -ItemType Directory -Path $taskCache -Force | Out-Null
$env:TEMP=$taskCache
$env:TMP=$taskCache
$env:PYTHONPYCACHEPREFIX=Join-Path $taskCache 'python'
$argsList=@((Join-Path $PSScriptRoot 'app\app.py'),'--data',$Data,'--port',"$Port")
if($NoBrowser){$argsList+='--no-browser'}
& $Python @argsList
exit $LASTEXITCODE
