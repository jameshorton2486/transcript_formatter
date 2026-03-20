[CmdletBinding()]
param(
    [string]$Source = "$env:USERPROFILE\Downloads",
    [string]$DestRoot = "",
    [switch]$Execute
)

$ErrorActionPreference = "Stop"

$folderMap = [ordered]@{
    "fig17"                   = "title_pages"
    "fig25"                   = "title_pages"
    "fig18"                   = "appearances"
    "fig22"                   = "index"
    "fig23"                   = "witness_setup"
    "fig28"                   = "transcript_body"
    "fig19"                   = "signature"
    "fig19a"                  = "signature"
    "fig20"                   = "certification"
    "fig20a"                  = "certification"
    "FIELD_MAP"               = "misc"
    "UFM_Field_Map_Reference" = "misc"
}

function Resolve-TargetFolder {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FileName
    )

    foreach ($key in $folderMap.Keys) {
        if ($FileName -match "^$key" -or $FileName -match $key) {
            return $folderMap[$key]
        }
    }

    return $null
}

if ([string]::IsNullOrWhiteSpace($DestRoot)) {
    if ($PSScriptRoot) {
        $DestRoot = Join-Path $PSScriptRoot "..\ufm_engine\templates"
    } else {
        $DestRoot = Join-Path (Get-Location) "ufm_engine\templates"
    }
}

$resolvedDestRoot = [System.IO.Path]::GetFullPath($DestRoot)

if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "Source folder does not exist: $Source"
}

if (-not (Test-Path -LiteralPath $resolvedDestRoot -PathType Container)) {
    New-Item -ItemType Directory -Path $resolvedDestRoot -Force | Out-Null
}

$folderMap.Values | Sort-Object -Unique | ForEach-Object {
    $path = Join-Path $resolvedDestRoot $_
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

$files = Get-ChildItem -LiteralPath $Source -File | Where-Object {
    $_.Name -match '^fig(17|18|19|19a|20|20a|22|23|25|28)' -or
    $_.Name -match 'FIELD_MAP|UFM_Field_Map_Reference'
} | Where-Object {
    $_.Name -notmatch '\(\d+\)'
}

$moved = @()
$skipped = @()
$mode = if ($Execute) { "EXECUTE" } else { "DRY RUN" }

foreach ($file in $files) {
    $targetFolder = Resolve-TargetFolder -FileName $file.Name

    if (-not $targetFolder) {
        $skipped += $file.Name
        continue
    }

    $destinationFolder = Join-Path $resolvedDestRoot $targetFolder
    $destinationPath = Join-Path $destinationFolder $file.Name

    if (Test-Path -LiteralPath $destinationPath) {
        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
        $extension = [System.IO.Path]::GetExtension($file.Name)
        $destinationPath = Join-Path $destinationFolder ($baseName + "_v2" + $extension)
    }

    if ($Execute) {
        Move-Item -LiteralPath $file.FullName -Destination $destinationPath
    }

    $moved += $destinationPath
}

Write-Host ""
Write-Host "=== UFM TEMPLATE MOVE $mode ===" -ForegroundColor Green
Write-Host "Source: $Source" -ForegroundColor DarkGray
Write-Host "Destination: $resolvedDestRoot" -ForegroundColor DarkGray

Write-Host ""
Write-Host "Matched Files:" -ForegroundColor Cyan
if ($moved.Count -eq 0) {
    Write-Host "(none)"
} else {
    $moved | ForEach-Object { Write-Host $_ }
}

if ($skipped.Count -gt 0) {
    Write-Host ""
    Write-Host "Skipped Files:" -ForegroundColor Yellow
    $skipped | ForEach-Object { Write-Host $_ }
}

if (-not $Execute) {
    Write-Host ""
    Write-Host "No files were moved. Re-run with -Execute to apply the move." -ForegroundColor Yellow
}
