#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

APPLESCRIPT_SRC="$PROJECT_ROOT/tools/apple/Memo Sync.applescript"
OUTPUT_DIR="${1:-$HOME/Applications}"
APP_NAME="Memo Sync"
APP_PATH="$OUTPUT_DIR/$APP_NAME.app"

if [[ ! -f "$APPLESCRIPT_SRC" ]]; then
    echo "Error: AppleScript source not found: $APPLESCRIPT_SRC" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

TMP_APPLESCRIPT=$(mktemp /tmp/memo_sync_XXXXXX.applescript)
trap 'rm -f "$TMP_APPLESCRIPT"' EXIT

sed "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" "$APPLESCRIPT_SRC" > "$TMP_APPLESCRIPT"

/usr/bin/osacompile -o "$APP_PATH" "$TMP_APPLESCRIPT"

if [[ ! -d "$APP_PATH" ]]; then
    echo "Error: Failed to compile .app bundle" >&2
    exit 1
fi

if [[ ! -f "$APP_PATH/Contents/Info.plist" ]]; then
    echo "Error: Missing Info.plist in bundle" >&2
    exit 1
fi

chmod +x "$PROJECT_ROOT/scripts/launch_memo_sync.sh"

echo "Built: $APP_PATH"
echo "Project root injected: $PROJECT_ROOT"
echo ""
echo "Next steps:"
echo "  1. Install swiftDialog:  brew install swiftdialog"
echo "  2. Open Spotlight, search '$APP_NAME'"
echo "  3. Or double-click $APP_PATH in Finder"
