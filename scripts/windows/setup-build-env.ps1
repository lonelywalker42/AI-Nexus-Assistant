[CmdletBinding()]
param(
    [string]$PythonExe = "",
    [switch]$Reset,
    [switch]$SkipCargoFetch,
    [switch]$SkipNativeToolchainCheck
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$BuildRoot = Join-Path $ProjectRoot ".build-env"
$ToolchainRoot = Join-Path $ProjectRoot ".toolchains"
$VenvRoot = Join-Path $BuildRoot "python"
$NpmCache = Join-Path $BuildRoot "npm-cache"
$CargoTarget = Join-Path $BuildRoot "cargo-target"

function Assert-UnderProject([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    $prefix = $ProjectRoot.TrimEnd("\") + "\"
    if (-not $full.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to manage a path outside the repository: $full"
    }
    return $full
}

function Remove-ManagedDirectory([string]$Path) {
    $safePath = Assert-UnderProject $Path
    if (Test-Path -LiteralPath $safePath) {
        Write-Host "Removing managed directory: $safePath"
        Remove-Item -LiteralPath $safePath -Recurse -Force
    }
}

function Resolve-Python([string]$Requested) {
    if ($Requested) {
        $command = Get-Command $Requested -ErrorAction SilentlyContinue
        if (-not $command) {
            throw "Python executable not found: $Requested"
        }
        return $command.Source
    }

    $managedPython = Join-Path $ToolchainRoot "python312\python.exe"
    if (Test-Path -LiteralPath $managedPython) {
        return $managedPython
    }

    $py = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if ($py) {
        $resolved = & $py.Source -3.12 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $resolved) {
            return $resolved.Trim()
        }
    }

    $python = Get-Command "python.exe" -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }
    throw "Python 3.12 was not found. Install 64-bit CPython, or pass -PythonExe C:\path\python.exe."
}

$ManagedCargoBin = Join-Path $ToolchainRoot "cargo\bin"
if (Test-Path -LiteralPath $ManagedCargoBin) {
    $env:CARGO_HOME = Join-Path $ToolchainRoot "cargo"
    $env:RUSTUP_HOME = Join-Path $ToolchainRoot "rustup"
    $env:PATH = "$ManagedCargoBin;$env:PATH"
}

if ($Reset) {
    Remove-ManagedDirectory $VenvRoot
    Remove-ManagedDirectory $NpmCache
    Remove-ManagedDirectory $CargoTarget
    Remove-ManagedDirectory (Join-Path $ProjectRoot "nexus-ui\node_modules")
    Remove-ManagedDirectory (Join-Path $ProjectRoot "open-webSearch\node_modules")
}

New-Item -ItemType Directory -Force -Path $BuildRoot, $NpmCache, $CargoTarget | Out-Null

$BootstrapPython = Resolve-Python $PythonExe
$PythonVersion = & $BootstrapPython -c "import platform, struct; print(platform.python_version()); print(struct.calcsize('P') * 8)"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to execute Python: $BootstrapPython"
}
$VersionParts = $PythonVersion[0].Split(".")
if ([int]$VersionParts[0] -ne 3 -or [int]$VersionParts[1] -lt 10 -or [int]$VersionParts[1] -gt 13) {
    throw "Python 3.10-3.13 is required; Python 3.12 x64 is recommended. Found $($PythonVersion[0])."
}
if ($PythonVersion[1] -ne "64") {
    throw "64-bit Python is required for the x86_64 Windows build."
}

if (-not (Test-Path -LiteralPath (Join-Path $VenvRoot "Scripts\python.exe"))) {
    Write-Host "Creating isolated Python environment: $VenvRoot"
    & $BootstrapPython -m venv $VenvRoot
    if ($LASTEXITCODE -ne 0) { throw "python -m venv failed" }
}

$BuildPython = Join-Path $VenvRoot "Scripts\python.exe"
Write-Host "Installing Python build dependencies into $VenvRoot"
& $BuildPython -m pip install --disable-pip-version-check --upgrade "pip>=24,<26"
if ($LASTEXITCODE -ne 0) { throw "pip bootstrap failed" }
Push-Location $ProjectRoot
try {
    & $BuildPython -m pip install --disable-pip-version-check -e ".[tauri,build,test]"
    if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed" }
}
finally {
    Pop-Location
}

$Npm = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
if (-not $Npm) {
    throw "npm.cmd was not found. Install an x64 Node.js LTS release and reopen PowerShell."
}
$env:NPM_CONFIG_CACHE = $NpmCache
$env:NPM_CONFIG_FUND = "false"
$env:NPM_CONFIG_AUDIT = "false"

foreach ($relativeDir in @("nexus-ui", "open-webSearch")) {
    $workDir = Join-Path $ProjectRoot $relativeDir
    Write-Host "Installing locked npm dependencies: $relativeDir"
    Push-Location $workDir
    try {
        & $Npm.Source ci
        if ($LASTEXITCODE -ne 0) { throw "npm ci failed in $relativeDir" }
    }
    finally {
        Pop-Location
    }
}

Write-Host "Building open-webSearch TypeScript output"
Push-Location (Join-Path $ProjectRoot "open-webSearch")
try {
    & $Npm.Source run build
    if ($LASTEXITCODE -ne 0) { throw "open-webSearch build failed" }
}
finally {
    Pop-Location
}

$Rustc = Get-Command "rustc.exe" -ErrorAction SilentlyContinue
$Cargo = Get-Command "cargo.exe" -ErrorAction SilentlyContinue
if (-not $Rustc -or -not $Cargo) {
    throw "Rust was not found. Install stable-x86_64-pc-windows-msvc with rustup."
}
$RustDetails = & $Rustc.Source -vV
if (($RustDetails -join "`n") -notmatch "host: x86_64-pc-windows-msvc") {
    throw "The active Rust host must be x86_64-pc-windows-msvc."
}

$env:CARGO_TARGET_DIR = $CargoTarget
if (-not $SkipCargoFetch) {
    Write-Host "Fetching Cargo.lock dependencies into the configured Cargo cache"
    & $Cargo.Source fetch --locked --manifest-path (Join-Path $ProjectRoot "nexus-ui\src-tauri\Cargo.toml")
    if ($LASTEXITCODE -ne 0) { throw "cargo fetch --locked failed" }
}

if ($SkipNativeToolchainCheck) {
    Write-Warning "Skipping the final Visual Studio/Windows SDK gate for staged provisioning."
    & $BuildPython (Join-Path $ProjectRoot "tools\project_check.py")
}
else {
    & $BuildPython (Join-Path $ProjectRoot "tools\project_check.py") --environment --strict-environment
}
if ($LASTEXITCODE -ne 0) { throw "Project preflight failed" }

$Manifest = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    project_root = $ProjectRoot
    python = $BuildPython
    python_version = (& $BuildPython --version 2>&1 | Out-String).Trim()
    node = (Get-Command "node.exe").Source
    node_version = (& (Get-Command "node.exe").Source --version | Out-String).Trim()
    npm = $Npm.Source
    npm_version = (& $Npm.Source --version | Out-String).Trim()
    rustc = $Rustc.Source
    rustc_version = (& $Rustc.Source --version | Out-String).Trim()
    cargo = $Cargo.Source
    cargo_version = (& $Cargo.Source --version | Out-String).Trim()
    native_toolchain_verified = (-not $SkipNativeToolchainCheck)
    npm_cache = $NpmCache
    cargo_target = $CargoTarget
}
$Manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $BuildRoot "environment.json") -Encoding UTF8
& $BuildPython -m pip freeze --all | Set-Content -LiteralPath (Join-Path $BuildRoot "python-packages.txt") -Encoding UTF8

Write-Host ""
Write-Host "Build environment is ready." -ForegroundColor Green
Write-Host "Manifest: $(Join-Path $BuildRoot 'environment.json')"
Write-Host "Next: powershell -ExecutionPolicy Bypass -File scripts/windows/build-release.ps1"
