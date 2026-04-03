# 🎮 Steam Account Switcher

A lightweight Bash script that lets you switch between multiple Steam accounts instantly using a sleek **rofi** popup menu — no manual logout, no browser, no fuss.

![Linux](https://img.shields.io/badge/platform-Linux-blue?style=flat-square&logo=linux)
![Bash](https://img.shields.io/badge/shell-bash-green?style=flat-square&logo=gnubash)
![rofi](https://img.shields.io/badge/launcher-rofi-orange?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square)

---

## ✨ Features

- **Instant account switching** — closes Steam and relaunches with the selected account
- **Rofi-powered menu** — fast, keyboard-navigable, type-to-filter
- **Custom display labels** — map cryptic Steam usernames to friendly names with emoji support
- **Auto-detached launch** — Steam restarts cleanly without leaving zombie processes
- **Self-bootstrapping** — creates a template `aliases.conf` on first run if one doesn't exist
- **Desktop entry** — launch from your app menu or bind to a keyboard shortcut

---

## 📋 Requirements

| Dependency | Purpose |
|---|---|
| `bash` ≥ 4.0 | Script runtime (associative arrays) |
| [`rofi`](https://github.com/davatorium/rofi) | Account picker menu |
| `steam` | Obviously |

> **Note:** This script is Linux-only. It reads Steam's `loginusers.vdf` file and uses `pkill`/`pgrep` for process management.

---

## 🚀 Quick Install (Automated)

```bash
git clone https://github.com/lalantham/steam-account-switcher.git
cd steam-account-switcher
chmod +x install.sh
./install.sh
```

The installer will:
1. Check for `rofi` and offer to install it if missing
2. Copy the script to `~/Documents/Tools/Scripts/`
3. Install `aliases.conf` (skips if one already exists)
4. Register the `.desktop` entry so it appears in your app launcher

---

## 🔧 Manual Setup

If you prefer to set things up yourself:

**1. Clone the repo**
```bash
git https://github.com/lalantham/steam-account-switcher.git
```

**2. Install rofi** (if not already installed)
```bash
# Debian / Ubuntu / Mint
sudo apt install rofi

# Arch / Manjaro
sudo pacman -S rofi

# Fedora
sudo dnf install rofi
```

**3. Make the script executable**
```bash
chmod +x steam-accounts.sh
```

**4. Place the files somewhere permanent**, e.g.:
```
~/Documents/Tools/Scripts/
├── steam-accounts.sh
└── aliases.conf
```

**5. (Optional) Add a desktop entry**

Edit `steam-account-switcher.desktop` and update the `Exec=` line to point to where you placed the script:
```ini
Exec=/home/YOUR_USERNAME/Documents/Tools/Scripts/steam-accounts.sh
```
Then copy it to your local applications folder:
```bash
cp steam-account-switcher.desktop ~/.local/share/applications/
update-desktop-database ~/.local/share/applications/
```

---

## ⚙️ Configuration — `aliases.conf`

The `aliases.conf` file maps your Steam **PersonaName** (the internal username shown in `loginusers.vdf`) to a friendly label displayed in the menu.

```
# Steam Account Aliases
# Format: PersonaName=Friendly Label

MickyBro=🎮 Main Account
john_alt99=👾 Horror Games
randomname123=🏆 Competitive
```

- Lines starting with `#` are comments and are ignored
- The key (left side) must exactly match the `PersonaName` from Steam's login file
- The value (right side) is whatever you want displayed in the menu — emoji are supported
- If a `PersonaName` has no alias entry, it is shown as-is in the menu

### Finding your PersonaName

Run this to list all accounts Steam knows about:
```bash
grep '"PersonaName"' ~/.steam/root/config/loginusers.vdf | awk -F\" '{print $4}'
```

---

## 🖥️ Usage

### From the terminal
```bash
./steam-accounts.sh
```

### From the app launcher
Search for **"Steam Account Switcher"** in your application menu (requires the `.desktop` entry to be installed).

### Keyboard shortcut
Bind the script path to a shortcut in your desktop environment's keyboard settings:
- **KDE**: System Settings → Shortcuts → Custom Shortcuts
- **GNOME**: Settings → Keyboard → Custom Shortcuts
- **i3/Hyprland/Sway**: Add a `bindsym` line in your config pointing to the script

### Workflow
1. Launch the switcher — a rofi popup appears
2. Type to filter or use arrow keys to navigate
3. Press Enter on the account you want
4. Steam closes and relaunches, auto-logging into the selected account
5. Press Escape or select **❌ Exit** to cancel without switching

---

## 📁 File Structure

```
steam-account-switcher/
├── steam-accounts.sh              # Main switcher script
├── aliases.conf                   # Your account display labels
├── steam-account-switcher.desktop # Desktop/app launcher entry
├── install.sh                     # Automated installer
└── README.md
```

---

## 🛠️ Troubleshooting

**Menu doesn't appear**
- Confirm rofi is installed: `which rofi`
- Try running the script from a terminal to see any error output

**Accounts not showing up**
- Verify the login file exists: `ls ~/.steam/root/config/loginusers.vdf`
- Some distros place it at `~/.local/share/Steam/config/loginusers.vdf` — update `LOGIN_FILE` in the script if needed

**Steam doesn't switch accounts / relaunches into the same account**
- Make sure you've logged in to each account at least once with the "remember me" option so Steam saves them to `loginusers.vdf`

**Wrong PersonaName in aliases.conf**
- PersonaNames are case-sensitive. Run the grep command above to get the exact strings

---

## 📄 License

MIT — do whatever you want with it.
