# Purpose: Recursively copy a complete VM results folder to a fresh local Windows directory using SCP.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9.-]*$')]
    [string]$VmHost,
    [ValidatePattern('^[A-Za-z_][A-Za-z0-9_.-]*$')]
    [string]$UserName = 'muthiyan',
    [string]$RemoteFolder = '/skynet/amrvac3.2/VanMarleTCRC/SkynetVMTesting',
    [string]$Destination = (Join-Path $PSScriptRoot 'VMDownloads'),
    [ValidateRange(1, 65535)]
    [int]$Port = 22,
    [switch]$Preview
)

$ErrorActionPreference = 'Stop'
if (-not $RemoteFolder.StartsWith('/') -or $RemoteFolder -match '[\r\n]') {
    throw 'RemoteFolder must be an absolute Linux folder path, such as /skynet/amrvac3.2/VanMarleTCRC/SkynetVMTesting.'
}
$RemoteFolder = $RemoteFolder.TrimEnd('/')
if ([string]::IsNullOrEmpty($RemoteFolder)) {
    throw 'Select a specific remote folder rather than the filesystem root.'
}
$scpCommand = Get-Command scp -CommandType Application -ErrorAction Stop
$remoteSpec = "${UserName}@${VmHost}:$RemoteFolder"
$localParent = [System.IO.Path]::GetFullPath($Destination)
$remoteLeaf = ($RemoteFolder -split '/')[-1]
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$downloadRoot = Join-Path $localParent ('download_' + $stamp)
Write-Host "VM source: $remoteSpec"
Write-Host "Local destination: $downloadRoot"
if ($Preview) {
    Write-Host 'Preview only: no directories created and no transfer started.'
    return
}
if (Test-Path -LiteralPath $downloadRoot) {
    throw "Destination already exists; refusing to mix transfers: $downloadRoot"
}
New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null
# The colon in remoteSpec is essential: it makes SCP read from the VM, not a local folder.
& $scpCommand.Source '-r' '-p' '-P' ([string]$Port) $remoteSpec $downloadRoot
if ($LASTEXITCODE -ne 0) {
    throw "SCP failed with exit code $LASTEXITCODE. Partial files, if any, remain in $downloadRoot."
}
$copiedFolder = Join-Path $downloadRoot $remoteLeaf
if (-not (Test-Path -LiteralPath $copiedFolder -PathType Container)) {
    throw "SCP exited successfully but the expected folder was not found: $copiedFolder"
}
Write-Host "Copied complete folder to: $copiedFolder"
