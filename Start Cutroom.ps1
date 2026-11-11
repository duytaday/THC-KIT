param([string]$Python='python',[string]$Data='',[int]$Port=0,[switch]$NoBrowser)
# Compatibility launcher; product name is Talking Head Cutroom.
& (Join-Path $PSScriptRoot 'Start Talking Head Cutroom.ps1') @PSBoundParameters
exit $LASTEXITCODE