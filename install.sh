#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Steam Account Switcher — Installer
# ─────────────────────────────────────────────────────────────────────────────

set -e

INSTALL_DIR="$HOME/Documents/Tools/Scripts"
DESKTOP_DIR="$HOME/.local/share/applications"
SCRIPT_NAME="steam-accounts.sh"
ALIAS_NAME="aliases.conf"
DESKTOP_NAME="steam-account-switcher.desktop"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "  🎮 Steam Account Switcher — Installer"
echo "  ──────────────────────────────────────"
echo ""

# ── 1. Dependency check ──────────────────────────────────────────────────────
echo "  [1/4] Checking dependencies..."

if ! command -v rofi &>/dev/null; then
    echo ""
    echo "  ⚠  rofi is not installed. This tool requires rofi to display the menu."
    echo ""
    read -rp "  Install rofi now? (requires sudo) [y/N]: " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        sudo apt-get install -y rofi
    else
        echo "  ✗ rofi is required. Aborting."
        exit 1
    fi
else
    echo "  ✔ rofi found"
fi

if ! command -v steam &>/dev/null; then
    echo "  ⚠  Steam does not appear to be installed or is not in PATH."
    echo "     The switcher will still be installed but may not work until Steam is set up."
fi

# ── 2. Install script ────────────────────────────────────────────────────────
echo ""
echo "  [2/4] Installing script to $INSTALL_DIR ..."

mkdir -p "$INSTALL_DIR"
cp "$REPO_DIR/$SCRIPT_NAME" "$INSTALL_DIR/$SCRIPT_NAME"
chmod +x "$INSTALL_DIR/$SCRIPT_NAME"
echo "  ✔ Script installed"

# ── 3. Install aliases (skip if already exists) ──────────────────────────────
echo ""
echo "  [3/4] Setting up aliases.conf ..."

if [[ -f "$INSTALL_DIR/$ALIAS_NAME" ]]; then
    echo "  ℹ  aliases.conf already exists — skipping to preserve your custom aliases."
else
    cp "$REPO_DIR/$ALIAS_NAME" "$INSTALL_DIR/$ALIAS_NAME"
    echo "  ✔ aliases.conf installed"
fi

# ── 4. Install .desktop entry ────────────────────────────────────────────────
echo ""
echo "  [4/4] Installing desktop entry ..."

mkdir -p "$DESKTOP_DIR"
sed "s|Exec=.*|Exec=$INSTALL_DIR/$SCRIPT_NAME|" \
    "$REPO_DIR/$DESKTOP_NAME" > "$DESKTOP_DIR/$DESKTOP_NAME"

# Refresh app menu if possible
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo "  ✔ Desktop entry installed"

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "  ────────────────────────────────────────────────────────"
echo "  ✅  Installation complete!"
echo ""
echo "  Script location : $INSTALL_DIR/$SCRIPT_NAME"
echo "  Aliases file    : $INSTALL_DIR/$ALIAS_NAME"
echo "  Desktop entry   : $DESKTOP_DIR/$DESKTOP_NAME"
echo ""
echo "  Next steps:"
echo "    • Edit $INSTALL_DIR/$ALIAS_NAME to map your Steam"
echo "      PersonaNames to friendly display labels."
echo "    • Run the switcher from your app launcher or bind it"
echo "      to a keyboard shortcut."
echo "  ────────────────────────────────────────────────────────"
echo ""
