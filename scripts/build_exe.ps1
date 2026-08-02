# Build unified ScreenFlow app into release/ScreenFlow/
# One exe: Studio by default; Start → relaunches self with --engine-runner (UAC).
# Usage (from repo root):  powershell -File .\scripts\build_exe.ps1

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host "==> Installing build deps"
python -m pip install -q -r requirements.txt pyinstaller pyautogui

$Dist = Join-Path $Root "dist"
$Build = Join-Path $Root "build"
$Release = Join-Path $Root "release\ScreenFlow"

Write-Host "==> Cleaning previous build outputs"
foreach ($p in @($Dist, $Build, $Release)) {
    if (Test-Path $p) { Remove-Item -Recurse -Force $p }
}

# Prefer PySide6 if the host also has PyQt5 (excludes are in the .spec).
$env:QT_API = "pyside6"

Write-Host "==> Building ScreenFlow (Studio + embedded Runner mode)"
python -m PyInstaller --noconfirm --clean --distpath $Dist --workpath (Join-Path $Build "studio") `
    (Join-Path $Root "packaging\screenflow.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$StudioDir = Join-Path $Dist "ScreenFlow"
$StudioExe = Join-Path $StudioDir "ScreenFlow.exe"
if (-not (Test-Path $StudioExe)) {
    throw "Build missing: $StudioExe"
}

Write-Host "==> Assembling release\ScreenFlow"
New-Item -ItemType Directory -Force -Path $Release | Out-Null
Copy-Item -Recurse -Force (Join-Path $StudioDir "*") $Release

Write-Host ""
Write-Host "Done. Launch: $Release\ScreenFlow.exe"
Write-Host "Runner is the same exe with --engine-runner (started by Studio when needed)."
