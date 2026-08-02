# Build a single ScreenFlow.exe (onefile) into release/
# Studio by default; Start → relaunches the same exe with --engine-runner (UAC).
# Usage (from repo root):  powershell -File .\scripts\build_exe.ps1

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host "==> Installing build deps"
python -m pip install -q -r requirements.txt pyinstaller pyautogui

$Dist = Join-Path $Root "dist"
$Build = Join-Path $Root "build"
$Release = Join-Path $Root "release"

Write-Host "==> Cleaning previous build outputs"
foreach ($p in @($Dist, $Build, $Release)) {
    if (Test-Path $p) { Remove-Item -Recurse -Force $p }
}

$env:QT_API = "pyside6"

Write-Host "==> Building ScreenFlow (onefile)"
python -m PyInstaller --noconfirm --clean --distpath $Dist --workpath (Join-Path $Build "studio") `
    (Join-Path $Root "packaging\screenflow.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$StudioExe = Join-Path $Dist "ScreenFlow.exe"
if (-not (Test-Path $StudioExe)) {
    throw "Build missing: $StudioExe"
}

Write-Host "==> Assembling release\"
New-Item -ItemType Directory -Force -Path $Release | Out-Null
Copy-Item -Force $StudioExe (Join-Path $Release "ScreenFlow.exe")

Write-Host ""
Write-Host "Done: $Release\ScreenFlow.exe (standalone; no _internal folder required)"
Write-Host "Runner mode: same file with --engine-runner"
