#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="${VENV_DIR:-.venv}"

if ! command -v python3 >/dev/null 2>&1; then
	echo "ERROR: python3 not found in PATH" >&2
	exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
	echo "Creating virtual environment in $VENV_DIR"
	python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

echo ""
echo "Dependencies installed."
echo "Activate the venv with:  source ./activate_venv.sh"
