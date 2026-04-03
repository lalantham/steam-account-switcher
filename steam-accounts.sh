#!/bin/bash
LOGIN_FILE="$HOME/.steam/root/config/loginusers.vdf"
ALIAS_FILE="$(dirname "$0")/aliases.conf"
# Create alias config with template on first run
if [[ ! -f "$ALIAS_FILE" ]]; then
    mkdir -p "$(dirname "$ALIAS_FILE")"
    cat > "$ALIAS_FILE" <<'EOF'
# Steam Account Aliases
# Map your Steam PersonaName to a friendly display label
# Format:  PersonaName=Friendly Label
#
# Examples:
#   xX_D3STR0Y3R_Xx=🎮 Main Account
#   john_alt99=👾 Horror Games Account
#   randomname123=🏆 Competitive Smurf
EOF
fi
# Load aliases into associative array
declare -A aliases
while IFS= read -r line; do
    # Skip comments and blank lines
    [[ "$line" =~ ^[[:space:]]*# || -z "${line// }" ]] && continue
    # Split on first = only (handles = signs in values)
    key="${line%%=*}"
    val="${line#*=}"
    # Trim whitespace from key
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    [[ -z "$key" ]] && continue
    aliases["$key"]="$val"
done < "$ALIAS_FILE"
# Extract accounts
mapfile -t accounts < <(grep '"AccountName"' "$LOGIN_FILE" | awk -F\" '{print $4}')
mapfile -t names < <(grep '"PersonaName"' "$LOGIN_FILE" | awk -F\" '{print $4}')
# Build menu — use alias if defined, otherwise fallback to PersonaName
menu_entries=("❌  Exit")
declare -A label_to_index
for i in "${!names[@]}"; do
    name="${names[$i]}"
    label="${aliases[$name]:-$name}"
    menu_entries+=("$label")
    label_to_index["$label"]="$i"
done
selection=$(printf '%s\n' "${menu_entries[@]}" | rofi -dmenu -i -p "Steam Account" -theme-str '
* {
    bg: #1e1e2e;
    bg-alt: #1e1e2e;
    fg: #cdd6f4;
    selected: #89b4fa;
}
window {
    width: 420px;
    location: center;
    background-color: @bg;
    border: 2px;
    border-color: #89b4fa;
    padding: 12px;
}
mainbox {
    background-color: @bg;
}
inputbar {
    padding: 8px;
    background-color: #181825;
    border-radius: 4px;
}
prompt {
    text-color: #89b4fa;
}
entry {
    placeholder: "Type to filter accounts";
}
listview {
    lines: 8;
    background-color: @bg;
    spacing: 6px;
    scrollbar: false;
}
element {
    padding: 8px;
    border-radius: 4px;
    background-color: #181825;
    text-color: #cdd6f4;
}
element normal normal {
    background-color: #181825;
    text-color: #cdd6f4;
}
element normal active {
    background-color: #181825;
    text-color: #cdd6f4;
}
element alternate normal {
    background-color: #181825;
    text-color: #cdd6f4;
}
element alternate active {
    background-color: #181825;
    text-color: #cdd6f4;
}
element selected normal {
    background-color: #313244;
    text-color: #89b4fa;
}
element selected active {
    background-color: #313244;
    text-color: #89b4fa;
}
element-text {
    background-color: transparent;
    text-color: inherit;
}
element-icon {
    background-color: transparent;
}
')
# Exit if nothing selected, Escape pressed, or Exit chosen
[ -z "$selection" ] && exit 0
[[ "$selection" == "❌  Exit" ]] && exit 0
# Find selected account via label→index map
ACCOUNT=""
idx="${label_to_index[$selection]}"
if [[ -n "$idx" ]]; then
    ACCOUNT="${accounts[$idx]}"
fi
[ -z "$ACCOUNT" ] && exit 1
# Hand off the Steam restart to a detached child process
# so killing Steam cannot terminate THIS script's process group
(
    # Use pkill with exact match to avoid killing unrelated processes
    pkill -x steam 2>/dev/null
    pkill -x steam.sh 2>/dev/null
    # Wait for Steam to fully shut down
    while pgrep -x steam &>/dev/null; do
        sleep 0.5
    done
    # Launch Steam fully detached from any terminal/parent
    nohup steam -login "$ACCOUNT" >/dev/null 2>&1 &
    disown
) &
disown $!
exit 0
