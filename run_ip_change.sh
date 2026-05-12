#!/bin/bash
set -x  # Show commands as they are executed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

/usr/bin/python3 ip_change.py ip_change-home-settings.json
