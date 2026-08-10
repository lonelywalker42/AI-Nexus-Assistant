[CmdletBinding()]
param(
    [switch]$DownloadOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$DownloadRoot = Join-Path $ProjectRoot ".toolchains\downloads"
$Bootstrapper = Join-Path $DownloadRoot "vs_BuildTools.exe"
$BootstrapperUrl = "https://aka.ms/vs/17/release/vs_BuildTools.exe"

New-Item -ItemType Directory -Force -Path $DownloadRoot | Out-Null

if (-not (Test-Path -LiteralPath $Bootstrapper)) {
    $partial = "$Bootstrapper.partial"
    if (Test-Path -LiteralPath $partial) {
        Remove-Item -LiteralPath $partial -Force
    }
    Write-Host "Downloading Visual Studio 2022 Build Tools bootstrapper"
    Invoke-WebRequest -UseBasicParsing -Uri $BootstrapperUrl -OutFile $partial
    Move-Item -LiteralPath $partial -Destination $Bootstrapper
}

$signature = Get-AuthenticodeSignature -LiteralPath $Bootstrapper
if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
    throw "Visual Studio bootstrapper signature is not valid: $($signature.Status)"
}
if (-not $signature.SignerCertificate.Subject.Contains("Microsoft Corporation")) {
    throw "Unexpected Visual Studio bootstrapper signer: $($signature.SignerCertificate.Subject)"
}

Write-Host "Verified Microsoft signature: $($signature.SignerCertificate.Subject)"
Write-Host "Bootstrapper: $Bootstrapper"
if ($DownloadOnly) {
    return
}

$drive = [System.IO.DriveInfo]::new($ProjectRoot.Substring(0, 1))
if ($drive.AvailableFreeSpace -lt 20GB) {
    throw "At least 20 GB free space is required before installing Visual Studio Build Tools."
}

$arguments = @(
    "--quiet",
    "--wait",
    "--norestart",
    "--nocache",
    "--add", "Microsoft.VisualStudio.Workload.VCTools",
    "--includeRecommended"
)

Write-Host "Installing Visual Studio 2022 C++ Build Tools and recommended Windows SDK components"
$process = Start-Process -FilePath $Bootstrapper -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
if ($process.ExitCode -eq 3010) {
    Write-Warning "Visual Studio Build Tools installed successfully; Windows requests a restart."
}
elseif ($process.ExitCode -ne 0) {
    throw "Visual Studio Build Tools installer failed with exit code $($process.ExitCode)"
}

Write-Host "Visual Studio Build Tools installation completed." -ForegroundColor Green
