#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Steam Account Switcher GUI — Installer
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

INSTALL_DIR="$HOME/.local/share/steam-account-switcher"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
LAUNCHER="$BIN_DIR/steam-account-switcher"
DESKTOP_FILE="$DESKTOP_DIR/steam-account-switcher.desktop"
ALIAS_FILE="$INSTALL_DIR/aliases.conf"

# ── Banner ─────────────────────────────────────────────────────────────────────
echo ""
echo "  🎮 Steam Account Switcher — GUI Installer"
echo "  ──────────────────────────────────────────"
echo ""

# ── 1. Python 3.8+ ────────────────────────────────────────────────────────────
echo "  [1/5] Checking Python..."

if ! command -v python3 &>/dev/null; then
    echo "  ✗ Python 3 is not installed. Please install Python 3.8 or newer."
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_OK=$(python3 -c "import sys; print('yes' if sys.version_info >= (3,8) else 'no')")
if [[ "$PY_OK" != "yes" ]]; then
    echo "  ✗ Python $PY_VER found, but 3.8+ is required."
    exit 1
fi
echo "  ✔ Python $PY_VER"

# ── 2. PyQt6 ──────────────────────────────────────────────────────────────────
echo ""
echo "  [2/5] Checking PyQt6..."

if python3 -c "import PyQt6" 2>/dev/null; then
    echo "  ✔ PyQt6 already installed"
else
    echo "  ⚠  PyQt6 not found — installing..."

    INSTALLED=false

    if command -v pacman &>/dev/null; then
        if sudo pacman -S --noconfirm --needed python-pyqt6; then
            INSTALLED=true
        fi
    elif command -v apt-get &>/dev/null; then
        if sudo apt-get install -y python3-pyqt6 2>/dev/null; then
            INSTALLED=true
        fi
    elif command -v dnf &>/dev/null; then
        if sudo dnf install -y python3-qt6 2>/dev/null; then
            INSTALLED=true
        fi
    elif command -v zypper &>/dev/null; then
        if sudo zypper install -y python3-qt6 2>/dev/null; then
            INSTALLED=true
        fi
    fi

    # Fallback: pip
    if [[ "$INSTALLED" == "false" ]] && command -v pip3 &>/dev/null; then
        if pip3 install --user PyQt6 2>/dev/null || \
           pip3 install --user --break-system-packages PyQt6 2>/dev/null; then
            INSTALLED=true
        fi
    fi

    if [[ "$INSTALLED" == "false" ]] || ! python3 -c "import PyQt6" 2>/dev/null; then
        echo ""
        echo "  ✗ Could not install PyQt6 automatically."
        echo "    Install it manually and re-run this installer:"
        echo ""
        echo "      Arch / CachyOS / Manjaro:  sudo pacman -S python-pyqt6"
        echo "      Debian / Ubuntu / Mint:    sudo apt install python3-pyqt6"
        echo "      Fedora:                    sudo dnf install python3-qt6"
        echo "      Any distro (pip):          pip3 install --user PyQt6"
        echo ""
        exit 1
    fi
    echo "  ✔ PyQt6 installed"
fi

# ── 3. Install application files ───────────────────────────────────────────────
echo ""
echo "  [3/5] Installing to $INSTALL_DIR ..."

mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/steam_switcher.py" "$INSTALL_DIR/steam_switcher.py"
chmod +x "$INSTALL_DIR/steam_switcher.py"
echo "  ✔ Application installed"

# ── 4. aliases.conf ────────────────────────────────────────────────────────────
echo ""
echo "  [4/5] Setting up aliases.conf ..."

if [[ -f "$ALIAS_FILE" ]]; then
    echo "  ℹ  Existing aliases.conf preserved (your labels are safe)"
else
    # Check if the user already has one from the bash-version installer
    LEGACY_ALIAS="$HOME/Documents/Tools/Scripts/aliases.conf"
    if [[ -f "$LEGACY_ALIAS" ]]; then
        cp "$LEGACY_ALIAS" "$ALIAS_FILE"
        echo "  ✔ Copied existing aliases from $LEGACY_ALIAS"
    else
        cp "$REPO_DIR/aliases.conf" "$ALIAS_FILE"
        echo "  ✔ Template aliases.conf installed"
    fi
fi

# ── 5. Desktop integration ─────────────────────────────────────────────────────
echo ""
echo "  [5/5] Setting up desktop entry and launcher ..."

# Launcher wrapper in ~/.local/bin
mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" <<EOF
#!/bin/bash
exec python3 "$INSTALL_DIR/steam_switcher.py" "\$@"
EOF
chmod +x "$LAUNCHER"
echo "  ✔ Launcher created at $LAUNCHER"

# Desktop entry
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=Steam Account Switcher
Comment=Switch Steam Accounts — PyQt6 GUI
Exec=$LAUNCHER
Icon=steam
Terminal=false
Type=Application
Categories=Game;Utility;
StartupNotify=true
EOF
chmod +x "$DESKTOP_FILE"

# Refresh app menu
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
echo "  ✔ Desktop entry installed"

# ── PATH check ─────────────────────────────────────────────────────────────────
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "  ⚠  $BIN_DIR is not in your PATH."
    echo "     Add this to your ~/.bashrc or ~/.zshrc:"
    echo "       export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# ── Done ───────────────────────────────────────────────────────────────────────
echo ""
echo "  ──────────────────────────────────────────────────────────────"
echo "  ✅  Installation complete!"
echo ""
echo "  App installed   : $INSTALL_DIR/steam_switcher.py"
echo "  Aliases file    : $ALIAS_FILE"
echo "  Launcher        : $LAUNCHER"
echo "  Desktop entry   : $DESKTOP_FILE"
echo ""
echo "  Next steps:"
echo "    • Run from terminal : steam-account-switcher"
echo "    • Or search \"Steam Account Switcher\" in your app launcher"
echo "    • Edit aliases      : $ALIAS_FILE"
echo "  ──────────────────────────────────────────────────────────────"
echo ""
