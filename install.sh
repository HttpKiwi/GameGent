#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
TARGET="${BIN_DIR}/gamegent"
APPS_DIR="${HOME}/.local/share/applications"
DESKTOP_FILE="${APPS_DIR}/gamegent.desktop"
ICON_PATH="${PROJECT_DIR}/assets/gamegent.svg"

mkdir -p "${BIN_DIR}" "${APPS_DIR}"
chmod +x "${PROJECT_DIR}/main.py"
ln -sf "${PROJECT_DIR}/main.py" "${TARGET}"

# Check if BIN_DIR is on PATH
case ":${PATH}:" in
  *:${BIN_DIR}:*) ;;
  *) echo "Warning: ${BIN_DIR} is not in PATH. Add to your shell rc:"
     echo "  export PATH=\"\${HOME}/.local/bin:\${PATH}\"" ;;
esac

cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Name=GameGent
Comment=GameSir Tarantula Pro configurator
Exec=${TARGET} app
Icon=${ICON_PATH}
Terminal=false
Type=Application
Categories=Utility;Settings;Game;
StartupNotify=true
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${APPS_DIR}" >/dev/null 2>&1 || true
fi

echo "Installed gamegent → ${TARGET}"
echo "Installed desktop entry → ${DESKTOP_FILE}"
echo
echo "Desktop app needs pywebview in the project venv (not system pip):"
echo "  ./venv/bin/pip install -r requirements.txt"
echo "  # Arch GUI backend:"
echo "  #   sudo pacman -S python-gobject webkit2gtk-4.1"
echo "  # venv/pyvenv.cfg must have: include-system-site-packages = true"
echo
echo "Run: gamegent app"
echo "  or open GameGent from your app menu"
echo "Browser UI: gamegent serve"
