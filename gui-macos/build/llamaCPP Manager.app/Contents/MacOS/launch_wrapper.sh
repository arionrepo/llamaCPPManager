#!/bin/bash
# Launch wrapper for llamaCPP Manager GUI

# Set up environment
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Check for CLI availability
CLI_PATHS=(
    "/opt/homebrew/bin/llamacpp-manager"
    "/usr/local/bin/llamacpp-manager"
    "$(which llamacpp-manager 2>/dev/null)"
)

CLI_FOUND=""
for path in "${CLI_PATHS[@]}"; do
    if [[ -x "$path" ]]; then
        CLI_FOUND="$path"
        break
    fi
done

if [[ -z "$CLI_FOUND" ]]; then
    # Show user-friendly error dialog
    osascript -e 'display dialog "llamaCPP Manager CLI not found. Please install it first using:\n\nbrew install llamacpp-manager\n\nor\n\npip install llamacpp-manager" with title "llamaCPP Manager" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Launch the actual GUI
exec "$(dirname "$0")/llamacpp-gui"
