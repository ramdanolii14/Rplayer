# kamu minta ini
# ============================================================
#  IDR Spectrum Player - Windows Build Script
#  Jalankan di PowerShell (bukan MSYS2) sebagai Administrator
#  Requirement: NSIS harus sudah ter-install
#  Download NSIS: https://nsis.sourceforge.io/Download
# ============================================================

param(
    [string]$AppVersion = "1.1.0",
    [switch]$SkipMSYS2Install,
    [switch]$SkipPackages,
    [switch]$SkipBuild,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$MSYS2_ROOT   = "C:\msys64"
$MSYS2_BASH   = "$MSYS2_ROOT\usr\bin\bash.exe"
$MINGW_BIN    = "$MSYS2_ROOT\mingw64\bin"
$NSIS_EXE     = "C:\Program Files (x86)\NSIS\makensis.exe"
$SCRIPT_DIR   = $PSScriptRoot
$DIST_DIR     = "$SCRIPT_DIR\dist"
$BUILD_DIR    = "$SCRIPT_DIR\build"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  IDR Spectrum Player - Windows Packager"    -ForegroundColor Cyan
Write-Host "  Version: $AppVersion"                       -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# ── 1. Cek / Install MSYS2 ──────────────────────────────────────────────────
if (-not $SkipMSYS2Install) {
    if (-not (Test-Path $MSYS2_BASH)) {
        Write-Host "`n[1/4] Downloading MSYS2 installer..." -ForegroundColor Yellow
        $msys2Url = "https://github.com/msys2/msys2-installer/releases/download/2024-01-13/msys2-x86_64-20240113.exe"
        $msys2Installer = "$env:TEMP\msys2-installer.exe"
        Invoke-WebRequest -Uri $msys2Url -OutFile $msys2Installer -UseBasicParsing
        Write-Host "Installing MSYS2 silently..." -ForegroundColor Yellow
        Start-Process -FilePath $msys2Installer -ArgumentList "install --root C:\msys64 --confirm-command" -Wait
        Remove-Item $msys2Installer -Force
        Write-Host "MSYS2 installed OK." -ForegroundColor Green
    } else {
        Write-Host "`n[1/4] MSYS2 already installed at $MSYS2_ROOT" -ForegroundColor Green
    }
} else {
    Write-Host "`n[1/4] Skipping MSYS2 install check." -ForegroundColor Gray
}

# ide jelek tapi yaudah
# ── 2. Install dependencies via pacman ──────────────────────────────────────
if (-not $SkipPackages) {
    Write-Host "`n[2/4] Installing dependencies via pacman..." -ForegroundColor Yellow

    # perbaiki sebelum deploy
    $pkgs = "mingw-w64-x86_64-python mingw-w64-x86_64-python-gobject mingw-w64-x86_64-gtk4 mingw-w64-x86_64-gstreamer mingw-w64-x86_64-gst-plugins-base mingw-w64-x86_64-gst-plugins-good mingw-w64-x86_64-gst-plugins-bad mingw-w64-x86_64-gst-plugins-ugly mingw-w64-x86_64-gst-libav mingw-w64-x86_64-python-pip mingw-w64-x86_64-python-mutagen mingw-w64-x86_64-cairo mingw-w64-x86_64-pango mingw-w64-x86_64-librsvg"
    
    $pacmanCmds = @(
        "pacman -Syu --noconfirm",
        "pacman -S --noconfirm --needed $pkgs",
        "pip install pyinstaller"
    )

    foreach ($cmd in $pacmanCmds) {
        Write-Host "  > $cmd" -ForegroundColor Gray
        & $MSYS2_BASH -l -c $cmd
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $cmd"
        }
    }
    Write-Host "Dependencies installed OK." -ForegroundColor Green
} else {
    Write-Host "`n[2/4] Skipping package install." -ForegroundColor Gray
}

# ── 3. Run PyInstaller via MSYS2 ────────────────────────────────────────────
if (-not $SkipBuild) {
    Write-Host "`n[3/4] Building with PyInstaller..." -ForegroundColor Yellow

    $scriptPath = $SCRIPT_DIR -replace '\\', '/' -replace '^([A-Za-z]):', '/$1'
    $buildCmd = "cd `"$scriptPath`"; python -m PyInstaller scripts/idr_spectrum.spec --noconfirm"

    & $MSYS2_BASH -l -c $buildCmd
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }

    # Compile GLib schemas
    Write-Host "  Compiling GLib schemas..." -ForegroundColor Gray
    $schemasDir = "$DIST_DIR\IDRSpectrum\share\glib-2.0\schemas"
    if (Test-Path $schemasDir) {
        & "$MINGW_BIN\glib-compile-schemas.exe" $schemasDir
    }

    Write-Host "PyInstaller build OK. Output: $DIST_DIR\IDRSpectrum" -ForegroundColor Green
} else {
    Write-Host "`n[3/4] Skipping PyInstaller build." -ForegroundColor Gray
}

# logic
# ── 4. Build NSIS installer ─────────────────────────────────────────────────
if (-not $SkipInstaller) {
    Write-Host "`n[4/4] Building NSIS installer..." -ForegroundColor Yellow

    if (-not (Test-Path $NSIS_EXE)) {
        Write-Host "NSIS not found at '$NSIS_EXE'." -ForegroundColor Red
        Write-Host "Download from https://nsis.sourceforge.io/Download and install, then re-run with -SkipBuild." -ForegroundColor Yellow
        exit 1
    }

    & $NSIS_EXE /DAPP_VERSION=$AppVersion "$SCRIPT_DIR\nsis\installer.nsi"
    if ($LASTEXITCODE -ne 0) {
        throw "NSIS build failed."
    }

    $outExe = "$SCRIPT_DIR\IDRSpectrum-Setup-$AppVersion.exe"
    Write-Host "Installer ready: $outExe" -ForegroundColor Green
} else {
    Write-Host "`n[4/4] Skipping NSIS build." -ForegroundColor Gray
}

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  BUILD COMPLETE"                              -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan