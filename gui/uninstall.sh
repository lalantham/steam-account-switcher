#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Steam Account Switcher GUI — Uninstaller
# ─────────────────────────────────────────────────────────────────────────────

INSTALL_DIR="$HOME/.local/share/steam-account-switcher"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

echo ""
echo "  🗑  Steam Account Switcher — Uninstaller"
echo "  ─────────────────────────────────────────"
echo ""

# Confirm
read -rp "  Remove Steam Account Switcher GUI? [y/N]: " answer
if [[ ! "$answer" =~ ^[Yy]$ ]]; then
    echo "  Aborted."
    exit 0
fi

echo ""

# Keep aliases.conf — it may have been customised or shared with the CLI version
if [[ -f "$INSTALL_DIR/aliases.conf" ]]; then
    read -rp "  Keep your aliases.conf? (recommended) [Y/n]: " keep_aliases
    if [[ "$keep_aliases" =~ ^[Nn]$ ]]; then
        rm -f "$INSTALL_DIR/aliases.conf"
        echo "  ✔ aliases.conf removed"
    else
        # Back it up to home dir before removing install dir
        BACKUP="$HOME/aliases.conf.bak"
        cp "$INSTALL_DIR/aliases.conf" "$BACKUP"
        echo "  ℹ  aliases.conf backed up to $BACKUP"
    fi
fi

# Remove installed files
rm -f "$INSTALL_DIR/steam_switcher.py"
rmdir "$INSTALL_DIR" 2>/dev/null || true
rm -f "$BIN_DIR/steam-account-switcher"
rm -f "$DESKTOP_DIR/steam-account-switcher.desktop"
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo "  ✔ Application files removed"
echo "  ✔ Launcher removed"
echo "  ✔ Desktop entry removed"
echo ""
echo "  ✅  Uninstall complete."
echo ""
