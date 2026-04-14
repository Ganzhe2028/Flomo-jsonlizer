#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Spotlight launches without a full shell profile, so explicit PATH is required
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

CMD_FILE="/var/tmp/memo_sync_commands.log"
MSG_FILE="/var/tmp/memo_sync_msg.md"

find_dialog() {
    local candidates=("/usr/local/bin/dialog" "/opt/homebrew/bin/dialog")
    for c in "${candidates[@]}"; do
        [[ -x "$c" ]] && echo "$c" && return 0
    done
    command -v dialog 2>/dev/null && return 0
    return 1
}

DIALOG_CMD=$(find_dialog) || true

show_error() {
    /usr/bin/osascript -e "display dialog \"$1\" with title \"$2\" buttons {\"OK\"} default button \"OK\" with icon stop"
}

if [[ -z "$DIALOG_CMD" ]]; then
    show_error "swiftDialog is not installed.\\n\\nInstall:\\n  brew install swiftdialog\\n\\nThen relaunch Memo Sync." "Memo Sync — Missing Dependency"
    exit 1
fi

if [[ ! -d "$PROJECT_ROOT/store" ]]; then
    show_error "Store directory not found.\\n\\nExpected: ${PROJECT_ROOT}/store\\n\\nRun build_store first." "Memo Sync — Error"
    exit 1
fi

: > "$CMD_FILE"
: > "$MSG_FILE"
trap 'rm -f "$CMD_FILE" "$MSG_FILE"' EXIT

cmd() { echo "$1" >> "$CMD_FILE"; }

show_msg() {
    printf '%s\n' "$1" > "$MSG_FILE"
    cmd "message: $MSG_FILE"
}

"$DIALOG_CMD" \
    --title "Memo Sync" \
    --icon "SF=arrow.triangle.2.circlepath.circle.fill" \
    --width 520 \
    --height 400 \
    --list \
    --listitem "Validate Store" \
    --listitem "Build Store" \
    --message "Starting..." \
    --button1text "Open Cursor" \
    --button2text "Open Finder" \
    --commandfile "$CMD_FILE" \
    &>/dev/null &

DIALOG_PID=$!
sleep 0.5

cmd "listitem: index: 0, status: wait, statustext: Running..."
cmd "listitem: index: 1, status: pending, statustext: Waiting"

VALIDATE_EXIT=0
VALIDATE_LOG=$(cd "$PROJECT_ROOT" && python3 scripts/validate_store.py --store-root store --summary 2>&1) || VALIDATE_EXIT=$?

if [[ $VALIDATE_EXIT -eq 0 ]]; then
    cmd "listitem: index: 0, status: success, statustext: Passed"
    cmd "listitem: index: 1, status: wait, statustext: Running..."
    show_msg "Validate passed. Building store..."
else
    cmd "listitem: index: 0, status: fail, statustext: Failed"
    cmd "listitem: index: 1, status: error, statustext: Skipped"
    VALIDATE_TAIL=$(printf '%s' "$VALIDATE_LOG" | tail -10)
    show_msg "Validate Store failed. Build skipped.

\`\`\`
$VALIDATE_TAIL
\`\`\`"
    wait "$DIALOG_PID" 2>/dev/null || true
    DIALOG_EXIT=$?
    # swiftDialog exit codes: 0=button1, 2=button2, 5=commandfile quit, 10=cmd+q
    case $DIALOG_EXIT in
        0) if ! open -a "Cursor" "$PROJECT_ROOT" 2>/dev/null; then open "$PROJECT_ROOT"; fi ;;
        2) open "$PROJECT_ROOT" ;;
    esac
    exit 0
fi

BUILD_EXIT=0
BUILD_LOG=$(cd "$PROJECT_ROOT" && python3 scripts/build_store.py --raw-root raw --store-root store 2>&1) || BUILD_EXIT=$?

if [[ $BUILD_EXIT -eq 0 ]]; then
    cmd "listitem: index: 1, status: success, statustext: Done"
    BUILD_TAIL=$(printf '%s' "$BUILD_LOG" | tail -5)
    show_msg "Sync completed successfully.

\`\`\`
$BUILD_TAIL
\`\`\`"
else
    cmd "listitem: index: 1, status: fail, statustext: Failed"
    BUILD_TAIL=$(printf '%s' "$BUILD_LOG" | tail -10)
    show_msg "Build Store failed.

\`\`\`
$BUILD_TAIL
\`\`\`"
fi

wait "$DIALOG_PID" 2>/dev/null || true
DIALOG_EXIT=$?

# swiftDialog exit codes: 0=button1, 2=button2, 5=commandfile quit, 10=cmd+q
case $DIALOG_EXIT in
    0) if ! open -a "Cursor" "$PROJECT_ROOT" 2>/dev/null; then open "$PROJECT_ROOT"; fi ;;
    2) open "$PROJECT_ROOT" ;;
esac
