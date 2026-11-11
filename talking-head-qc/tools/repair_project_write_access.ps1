#Requires -RunAsAdministrator
<#!
Scoped repair for the user-requested output directory. Run manually in an
Administrator PowerShell after inspecting this file. No ownership changes,
Everyone grants, recursive deletion, source edits or global settings.
#!>
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\Video editing\Talking head video editing skills'
$expectedAccount = 'DIQUAHOACUC\Acer'
$resolved = (Resolve-Path -LiteralPath $projectRoot).ProviderPath.TrimEnd('\')
if ($resolved -ne $projectRoot) { throw 'Unexpected target; refusing ACL change.' }
$principal = New-Object System.Security.Principal.NTAccount($expectedAccount)
$sid = $principal.Translate([System.Security.Principal.SecurityIdentifier])
$acl = Get-Acl -LiteralPath $resolved
$backup = Join-Path $env:TEMP ('talking-head-project-acl-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.xml')
$acl | Export-Clixml -LiteralPath $backup
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule($sid, 'Modify', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
$acl.AddAccessRule($rule)
Set-Acl -LiteralPath $resolved -AclObject $acl
Write-Output "Granted Modify to $expectedAccount on exactly $resolved. Original ACL: $backup"
Write-Output 'Run the ordinary editor write test again; an elevated process write test would not prove the standard user can write.'
