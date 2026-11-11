param([string]$Python='python',[string]$Data='',[int]$Port=0,[switch]$NoBrowser)
$ErrorActionPreference='Stop'
if (-not (Test-Path -LiteralPath 'D:\')) { throw 'D: is required by this workspace storage policy.' }
if(-not $Data){$Data=Join-Path $PSScriptRoot 'output\cutroom-workspace'}
$Data=[IO.Path]::GetFullPath($Data)
if([IO.Path]::GetPathRoot($Data) -ne 'D:\'){throw 'Choose a workspace on D:.'}
$taskCache=Join-Path $Data '.cache'
New-Item -ItemType Directory -Path $taskCache -Force | Out-Null
$env:TEMP=$taskCache
$env:TMP=$taskCache
$env:PYTHONPYCACHEPREFIX=Join-Path $taskCache 'python'
$argsList=@((Join-Path $PSScriptRoot 'app\app.py'),'--data',$Data,'--port',"$Port")
if($NoBrowser){$argsList+='--no-browser'}
& $Python @argsList
exit $LASTEXITCODE
