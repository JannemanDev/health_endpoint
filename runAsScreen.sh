SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# use --non-interactive so it can be run under a screen unattended
screen -d -m -S health_server ./start_health_server.sh

# list all screens: screen -ls
# restore a screen: screen -r <screen-id/name>
