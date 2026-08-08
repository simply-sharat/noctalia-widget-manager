#!/usr/bin/env bash
# Install the built binary + launcher entry (user-local, no root needed).
set -euo pipefail

cd "$(dirname "$0")"

BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
BINARY="dist/noctalia-widget-manager"

if [ ! -f "$BINARY" ]; then
    echo "Binary not found: $BINARY" >&2
    echo "Run ./build.sh first." >&2
    exit 1
fi

install -Dm755 "$BINARY" "$BIN_DIR/noctalia-widget-manager"
install -Dm644 data/noctalia-widget-manager.png \
    "$ICON_DIR/noctalia-widget-manager.png"
sed "s|@INSTALL_DIR@|$BIN_DIR|g" data/noctalia-widget-manager.desktop \
    | install -Dm644 /dev/stdin "$APPS_DIR/noctalia-widget-manager.desktop"

# Refresh desktop databases so the entry shows up (best effort).
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Installed:"
echo "  $BIN_DIR/noctalia-widget-manager"
echo "  $APPS_DIR/noctalia-widget-manager.desktop"
echo "Look for 'Noctalia Widget Manager' in your application launcher."
