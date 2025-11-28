#!/bin/bash

# 1. Set Directory to this script's location (Fixes "File not found" errors)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================"
echo "❄️  Craft Winter Butler - Installer & Runner"
echo "========================================"

# 2. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed."
    echo "👉 Please download it from python.org/downloads"
    read -p "Press Enter to exit..."
    exit 1
fi

# 3. Setup Virtual Environment (The "Idiot Proof" Magic)
if [ ! -d "venv" ]; then
    echo "📦 First run detected. Creating virtual environment..."
    python3 -m venv venv
fi

# 4. Install Dependencies (Quietly)
echo "⬇️  Checking dependencies..."
# We use the pip inside venv directly to avoid activation issues in some shells
./venv/bin/pip install -r scripts/requirements.txt -q

# 5. Check Config
if grep -q "PASTE" config.json; then
    echo "⚠️  WARNING: It looks like you haven't added your API keys yet."
    echo "   Please open 'config.json' in this folder and add them."
    echo "   (Right-click config.json -> Open With -> TextEdit)"
    echo ""
    read -p "Press Enter to continue anyway (or Ctrl+C to stop)..."
fi

# --- AUTOMATION FUNCTIONS ---

install_automation() {
    echo ""
    echo "⏰ Installing Background Schedules..."
    
    # Paths
    PYTHON_PATH="$DIR/venv/bin/python"
    SCRIPT_PATH="$DIR/scripts/craft_butler.py"
    
    # --- Morning Agent (5:00 AM) ---
    PLIST_MORNING="$HOME/Library/LaunchAgents/com.craftbot.morning.plist"
    cat <<EOF > "$PLIST_MORNING"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.craftbot.morning</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$SCRIPT_PATH</string>
        <string>--mode</string>
        <string>morning</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>5</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$DIR/morning_log.txt</string>
    <key>StandardErrorPath</key>
    <string>$DIR/morning_error.txt</string>
</dict>
</plist>
EOF
    launchctl unload "$PLIST_MORNING" 2>/dev/null
    launchctl load "$PLIST_MORNING"
    echo "   ✅ Morning routine set for 5:00 AM"

    # --- Evening Agent (11:00 PM) ---
    PLIST_EVENING="$HOME/Library/LaunchAgents/com.craftbot.evening.plist"
    cat <<EOF > "$PLIST_EVENING"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.craftbot.evening</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$SCRIPT_PATH</string>
        <string>--mode</string>
        <string>evening</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>23</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$DIR/evening_log.txt</string>
    <key>StandardErrorPath</key>
    <string>$DIR/evening_error.txt</string>
</dict>
</plist>
EOF
    launchctl unload "$PLIST_EVENING" 2>/dev/null
    launchctl load "$PLIST_EVENING"
    echo "   ✅ Evening routine set for 11:00 PM"
    echo ""
    echo "🎉 Success! The bot will now run automatically."
    echo "   (You do not need Apple Shortcuts anymore)."
}

uninstall_automation() {
    echo ""
    echo "🗑️  Removing Schedules..."
    launchctl unload "$HOME/Library/LaunchAgents/com.craftbot.morning.plist" 2>/dev/null
    rm "$HOME/Library/LaunchAgents/com.craftbot.morning.plist" 2>/dev/null
    
    launchctl unload "$HOME/Library/LaunchAgents/com.craftbot.evening.plist" 2>/dev/null
    rm "$HOME/Library/LaunchAgents/com.craftbot.evening.plist" 2>/dev/null
    echo "✅ Schedules removed."
}

# --- MENU ---

if [ "$1" == "morning" ]; then
    ./venv/bin/python scripts/craft_butler.py --mode morning
elif [ "$1" == "evening" ]; then
    ./venv/bin/python scripts/craft_butler.py --mode evening
else
    echo ""
    echo "What would you like to do?"
    echo "1) ☀️  Run Morning Routine NOW"
    echo "2) 🌙 Run Evening Routine NOW"
    echo "3) ⏰ Install Auto-Schedule (Runs daily at 5am & 11pm)"
    echo "4) 🚫 Uninstall Auto-Schedule"
    read -p "Enter number: " SELECTION

    if [ "$SELECTION" == "1" ]; then
        echo ""
        ./venv/bin/python scripts/craft_butler.py --mode morning
    elif [ "$SELECTION" == "2" ]; then
        echo ""
        ./venv/bin/python scripts/craft_butler.py --mode evening
    elif [ "$SELECTION" == "3" ]; then
        install_automation
    elif [ "$SELECTION" == "4" ]; then
        uninstall_automation
    else
        echo "Invalid selection."
    fi
fi

echo ""
echo "Done."
# Keep window open briefly
sleep 3