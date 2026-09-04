#!/usr/bin/env bash
#
# LinkedIn Auto-Apply & Recruiter Outreach Bot - One-Line Universal Installer (macOS & Linux)
# Author: Pulkit Khanna
#

set -e

echo ""
echo "=================================================================="
echo "  🚀 Installing LinkedIn Auto-Apply & Recruiter Outreach Suite   "
echo "=================================================================="
echo ""

INSTALL_DIR="$HOME/linkedin-auto-apply-bot"
REPO_URL="https://github.com/pulkitkhanna1/linkedin-auto-apply-bot.git"

# 1. Check for Git
if ! command -v git >/dev/null 2>&1; then
    echo "❌ Git is required but was not found."
    echo "   On macOS, run: xcode-select --install"
    echo "   On Ubuntu/Debian, run: sudo apt update && sudo apt install git"
    exit 1
fi

# 2. Check for Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python 3 was not found."
    echo "   Please download and install Python from https://www.python.org/downloads/"
    exit 1
fi

# 3. Clone or Update Repository
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "🔄 Updating existing installation in $INSTALL_DIR..."
    cd "$INSTALL_DIR"
    git pull origin main || true
else
    echo "📥 Downloading repository to $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 4. Setup Python Virtual Environment
VENV_PY="$INSTALL_DIR/.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv .venv
fi

# 5. Install Dependencies
echo "⚡ Installing and verifying dependencies..."
"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install --quiet -r requirements.txt

# 6. Create Desktop Shortcut for 1-Click Launching
DESKTOP_DIR="$HOME/Desktop"
if [ -d "$DESKTOP_DIR" ]; then
    SHORTCUT="$DESKTOP_DIR/LinkedIn Auto Applier.command"
    cat << 'EOF' > "$SHORTCUT"
#!/bin/bash
cd "$HOME/linkedin-auto-apply-bot" || exit 1
export PANEL_OPEN_BROWSER=1
.venv/bin/python app.py
EOF
    chmod +x "$SHORTCUT"
    echo "✨ Desktop 1-click shortcut created at: $SHORTCUT"
fi

echo ""
echo "=================================================================="
echo "  ✅ Installation Complete! Starting Web Control Panel...        "
echo "=================================================================="
echo ""

export PANEL_OPEN_BROWSER=1
"$VENV_PY" app.py
