#!/bin/bash
set -euo pipefail
set -x  # Show commands as they are executed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

usage() {
	echo "Usage: $0 <settings.json>" >&2
	echo "Example: $0 ip_change-settings.json" >&2
	exit 1
}

[[ $# -eq 1 ]] || usage

SETTINGS_FILE="$1"
if [[ ! -f "$SETTINGS_FILE" ]]; then
	echo "ERROR: Settings file not found: $SETTINGS_FILE" >&2
	exit 1
fi

VENV_DIR="${VENV_DIR:-.venv}"
PYTHON="$VENV_DIR/bin/python"
if [[ ! -x "$PYTHON" ]]; then
	PYTHON="$(command -v python3)"
fi

exec "$PYTHON" ip_change.py "$SETTINGS_FILE"
