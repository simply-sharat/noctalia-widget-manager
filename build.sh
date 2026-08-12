#!/usr/bin/env bash
# Build a standalone binary for Noctalia Widget Manager with PyInstaller.
# Uses a venv with --system-site-packages so the system PySide6 is reused.
set -euo pipefail

cd "$(dirname "$0")"

VENV_DIR=".venv"
PYTHON="${PYTHON:-python3}"

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Creating build venv at $VENV_DIR ..."
    "$PYTHON" -m venv --system-site-packages "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/pip" show pyinstaller >/dev/null 2>&1; then
    echo "Installing PyInstaller and tomlkit into $VENV_DIR ..."
    "$VENV_DIR/bin/pip" install --upgrade pyinstaller tomlkit
fi

echo "Generating icon ..."
"$VENV_DIR/bin/python" tools/make_icon.py

echo "Building binary (this can take a few minutes) ..."
"$VENV_DIR/bin/pyinstaller" \
    --noconfirm --clean \
    --distpath dist --workpath build \
    noctalia-widget-manager.spec

echo
echo "Done. Binary: dist/noctalia-widget-manager"
echo "Run ./install.sh to add it to your launcher."
