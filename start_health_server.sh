# if run from TaskScheduler, cd to the correct folder which is the current folder of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

/usr/bin/python3 health_server.py
