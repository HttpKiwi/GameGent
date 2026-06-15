#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
TARGET="${BIN_DIR}/gamegent"

mkdir -p "${BIN_DIR}"
chmod +x "${PROJECT_DIR}/main.py"
ln -sf "${PROJECT_DIR}/main.py" "${TARGET}"

# Check if BIN_DIR is on PATH
case ":${PATH}:" in
  *:${BIN_DIR}:*) ;;
  *) echo "Warning: ${BIN_DIR} is not in PATH. Add to your shell rc:"
     echo "  export PATH=\"\${HOME}/.local/bin:\${PATH}\"" ;;
esac

echo "Installed gamegent → ${TARGET}"
echo "Run: gamegent serve"
