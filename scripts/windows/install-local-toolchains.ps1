[CmdletBinding()]
param(
    [switch]$Reset,
    [string]$PythonVersion = "3.12.10"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$ToolchainRoot = Join-Path $ProjectRoot ".toolchains"
$DownloadRoot = Join-Path $ToolchainRoot "downloads"
$PythonRoot = Join-Path $ToolchainRoot "python312"
$CargoHome = Join-Path $ToolchainRoot "cargo"
$RustupHome = Join-Path $ToolchainRoot "rustup"
$PythonInstaller = Join-Path $DownloadRoot "python-$PythonVersion-amd64.exe"
$RustupInstaller = Join-Path $DownloadRoot "rustup-init-x86_64.exe"

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

function Download-File([string]$Uri, [string]$Destination) {
    if (Test-Path -LiteralPath $Destination) {
        return
    }
    $partial = "$Destination.partial"
    if (Test-Path -LiteralPath $partial) {
        Remove-Item -LiteralPath $partial -Force
    }
    Write-Host "Downloading $Uri"
    Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $partial
    Move-Item -LiteralPath $partial -Destination $Destination
}

if ($Reset) {
    Remove-ManagedDirectory $PythonRoot
    Remove-ManagedDirectory $CargoHome
    Remove-ManagedDirectory $RustupHome
}

New-Item -ItemType Directory -Force -Path $ToolchainRoot, $DownloadRoot | Out-Null

$PythonExe = Join-Path $PythonRoot "python.exe"
if (-not (Test-Path -LiteralPath $PythonExe)) {
    $PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
    Download-File $PythonUrl $PythonInstaller

    $signature = Get-AuthenticodeSignature -LiteralPath $PythonInstaller
    if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
        throw "Python installer signature is not valid: $($signature.Status)"
    }

    Write-Host "Installing repository-local CPython $PythonVersion"
    $pythonArgs = @(
        "/quiet",
        "InstallAllUsers=0",
        "TargetDir=$PythonRoot",
        "Include_doc=0",
        "Include_debug=0",
        "Include_dev=0",
        "Include_exe=1",
        "Include_launcher=0",
        "InstallLauncherAllUsers=0",
        "Include_lib=1",
        "Include_pip=1",
        "Include_symbols=0",
        "Include_tcltk=0",
        "Include_test=0",
        "Include_tools=1",
        "PrependPath=0",
        "Shortcuts=0",
        "AssociateFiles=0"
    )
    $process = Start-Process -FilePath $PythonInstaller -ArgumentList $pythonArgs -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -ne 0) {
        throw "Python installer failed with exit code $($process.ExitCode)"
    }
}

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python executable was not created: $PythonExe"
}

$RustupExe = Join-Path $CargoHome "bin\rustup.exe"
if (-not (Test-Path -LiteralPath $RustupExe)) {
    Download-File "https://win.rustup.rs/x86_64" $RustupInstaller
    $env:CARGO_HOME = $CargoHome
    $env:RUSTUP_HOME = $RustupHome
    Write-Host "Installing repository-local Rust stable MSVC toolchain"
    & $RustupInstaller -y --profile minimal --default-host x86_64-pc-windows-msvc --default-toolchain stable
    if ($LASTEXITCODE -ne 0) {
        throw "rustup-init failed with exit code $LASTEXITCODE"
    }
}

$env:CARGO_HOME = $CargoHome
$env:RUSTUP_HOME = $RustupHome
$env:PATH = "$(Join-Path $CargoHome 'bin');$env:PATH"
& $RustupExe default stable-x86_64-pc-windows-msvc
if ($LASTEXITCODE -ne 0) { throw "rustup default failed" }

$RustcExe = Join-Path $CargoHome "bin\rustc.exe"
$CargoExe = Join-Path $CargoHome "bin\cargo.exe"
if (-not (Test-Path -LiteralPath $RustcExe) -or -not (Test-Path -LiteralPath $CargoExe)) {
    throw "Rust executables were not created under $CargoHome\bin"
}

Write-Host ""
Write-Host "Repository-local toolchains are ready." -ForegroundColor Green
Write-Host "Python: $PythonExe"
Write-Host "Rust:   $RustcExe"
& $PythonExe --version
& $RustcExe -vV
