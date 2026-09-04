# LinkedIn Auto-Apply & Recruiter Outreach Suite - One-Line Windows Installer
# Author: Pulkit Khanna

$ErrorActionPreference = "Stop"

Write-Host "`n==================================================================" -ForegroundColor Cyan
Write-Host "  🚀 Installing LinkedIn Auto-Apply & Recruiter Outreach Suite   " -ForegroundColor Cyan
Write-Host "==================================================================`n" -ForegroundColor Cyan

$InstallDir = Join-Path $HOME "linkedin-auto-apply-bot"
$RepoUrl = "https://github.com/pulkitkhanna1/linkedin-auto-apply-bot.git"

# 1. Check Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Git is required but was not found. Please install Git for Windows from https://git-scm.com/" -ForegroundColor Red
    Exit 1
}

# 2. Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python 3 was not found. Please install Python from https://www.python.org/downloads/ (ensure 'Add python.exe to PATH' is checked)" -ForegroundColor Red
    Exit 1
}

# 3. Clone or Update Repository
if (Test-Path (Join-Path $InstallDir ".git")) {
    Write-Host "🔄 Updating existing installation in $InstallDir..." -ForegroundColor Yellow
    Set-Location $InstallDir
    git pull origin main
} else {
    Write-Host "📥 Downloading repository to $InstallDir..." -ForegroundColor Yellow
    git clone $RepoUrl $InstallDir
    Set-Location $InstallDir
}

# 4. Setup Python Virtual Environment
$VenvPy = Join-Path $InstallDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) {
    Write-Host "📦 Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# 5. Install Dependencies
Write-Host "⚡ Installing and verifying dependencies..." -ForegroundColor Yellow
& $VenvPy -m pip install --quiet --upgrade pip
& $VenvPy -m pip install --quiet -r requirements.txt

# 6. Create Desktop Shortcut
$DesktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
if (Test-Path $DesktopPath) {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut((Join-Path $DesktopPath "LinkedIn Auto Applier.lnk"))
    $Shortcut.TargetPath = (Join-Path $InstallDir "start.bat")
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.Save()
    Write-Host "✨ Desktop 1-click shortcut created on your Desktop!" -ForegroundColor Green
}

Write-Host "`n==================================================================" -ForegroundColor Green
Write-Host "  ✅ Installation Complete! Starting Web Control Panel...        " -ForegroundColor Green
Write-Host "==================================================================`n" -ForegroundColor Green

$env:PANEL_OPEN_BROWSER = "1"
& (Join-Path $InstallDir "start.bat")
