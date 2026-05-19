#!/bin/bash
# Activate the project virtual environment.
# Usage (must be sourced):  source ./activate_venv.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${VENV_DIR:-$SCRIPT_DIR/.venv}"

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	echo "This script must be sourced, not executed:" >&2
	echo "  source ./activate_venv.sh" >&2
	exit 1
fi

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
	echo "Virtual environment not found at $VENV_DIR" >&2
	echo "Run ./install_deps.sh first." >&2
	return 1 2>/dev/null || exit 1
fi

cd "$SCRIPT_DIR"
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
