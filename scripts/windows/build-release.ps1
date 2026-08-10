[CmdletBinding()]
param(
    [switch]$CleanOutputs,
    [ValidateSet("portable", "installers")]
    [string]$PackageMode = "portable"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$BuildRoot = Join-Path $ProjectRoot ".build-env"
$ToolchainRoot = Join-Path $ProjectRoot ".toolchains"
$BuildPython = Join-Path $BuildRoot "python\Scripts\python.exe"

function Remove-BuildOutput([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    $prefix = $ProjectRoot.TrimEnd("\") + "\"
    if (-not $full.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a path outside the repository: $full"
    }
    if (Test-Path -LiteralPath $full) {
        Remove-Item -LiteralPath $full -Recurse -Force
    }
}

if (-not (Test-Path -LiteralPath $BuildPython)) {
    throw "Managed build environment not found. Run scripts/windows/setup-build-env.ps1 first."
}

if ($CleanOutputs) {
    foreach ($relativePath in @("build", "dist", "release", "nexus-ui\dist", ".build-env\cargo-target")) {
        Remove-BuildOutput (Join-Path $ProjectRoot $relativePath)
    }
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:NPM_CONFIG_CACHE = Join-Path $BuildRoot "npm-cache"
$env:NPM_CONFIG_FUND = "false"
$env:NPM_CONFIG_AUDIT = "false"
$env:CARGO_TARGET_DIR = Join-Path $BuildRoot "cargo-target"
$env:NEXUS_TAURI_PACKAGE_MODE = $PackageMode

if ($PackageMode -eq "installers") {
    $SigningKey = Join-Path $env:USERPROFILE ".tauri\nexus.key"
    $SigningPublicKey = "$SigningKey.pub"
    if (-not (Test-Path -LiteralPath $SigningKey) -or -not (Test-Path -LiteralPath $SigningPublicKey)) {
        throw "Tauri updater signing key is missing: $SigningKey"
    }

    $ConfiguredPublicKey = (Get-Content -LiteralPath `
        (Join-Path $ProjectRoot "nexus-ui\src-tauri\tauri.conf.json") -Raw | ConvertFrom-Json).plugins.updater.pubkey.Trim()
    $LocalPublicKey = (Get-Content -LiteralPath $SigningPublicKey -Raw).Trim()
    if ($ConfiguredPublicKey -ne $LocalPublicKey) {
        throw "The local Tauri signing key does not match tauri.conf.json"
    }
    $env:TAURI_SIGNING_PRIVATE_KEY = Get-Content -LiteralPath $SigningKey -Raw
}
$ManagedCargoBin = Join-Path $ToolchainRoot "cargo\bin"
if (Test-Path -LiteralPath $ManagedCargoBin) {
    $env:CARGO_HOME = Join-Path $ToolchainRoot "cargo"
    $env:RUSTUP_HOME = Join-Path $ToolchainRoot "rustup"
    $env:PATH = "$ManagedCargoBin;$env:PATH"
}

Push-Location $ProjectRoot
try {
    & $BuildPython "tools/project_check.py" --environment --strict-environment
    if ($LASTEXITCODE -ne 0) { throw "Project preflight failed" }

    & $BuildPython "build_tauri.py"
    if ($LASTEXITCODE -ne 0) { throw "Windows release build failed" }
}
finally {
    Pop-Location
}

Write-Host "Release build complete: $(Join-Path $ProjectRoot 'release')" -ForegroundColor Green
