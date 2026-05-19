import commentjson
import hmac
import ipaddress
import logging
import os
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request

app = Flask(__name__)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
script_name = os.path.basename(__file__)
base_name = os.path.splitext(script_name)[0]

CONFIG = {}
AUTH_TOKEN = ""
ACCEPT_BEARER = True
ACCEPT_QUERY_PARAM = True
LOG_TO_CONSOLE = True
LOG_TO_FILE = True
IP_LOG_TO_FILE = True
LOG_FILE = None
IP_STATS_FILE = None
_file_lock = threading.Lock()


def _pid_file_path():
    override = os.environ.get("WHATSMYIP_SERVER_PID_FILE")
    if override:
        return override
    default = os.path.join(SCRIPT_DIR, base_name + ".pid")
    if os.access(SCRIPT_DIR, os.W_OK):
        return default
    tmp = os.environ.get("TMPDIR", "/tmp")
    return os.path.join(tmp, base_name + ".pid")


PID_FILE = _pid_file_path()


def require_config(key):
    if key not in CONFIG:
        print(f"ERROR: Missing required config key: {key}", flush=True)
        sys.exit(1)
    return CONFIG[key]


def _resolve_log_file(config_path, log_file_setting):
    if not log_file_setting or not str(log_file_setting).strip():
        return None
    path = Path(str(log_file_setting).strip())
    if not path.is_absolute():
        path = Path(config_path).resolve().parent / path
    return str(path.resolve())


def load_config(config_path):
    global CONFIG, AUTH_TOKEN, ACCEPT_BEARER, ACCEPT_QUERY_PARAM
    global LOG_TO_CONSOLE, LOG_TO_FILE, IP_LOG_TO_FILE, LOG_FILE, IP_STATS_FILE
    config_path = os.path.abspath(config_path)
    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}", flush=True)
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        CONFIG = commentjson.load(f)
    AUTH_TOKEN = require_config("token")
    if not str(AUTH_TOKEN).strip():
        print("ERROR: config key 'token' must be non-empty", flush=True)
        sys.exit(1)
    require_config("port")
    auth = CONFIG.get("auth", {})
    ACCEPT_BEARER = bool(auth.get("accept_bearer", True))
    ACCEPT_QUERY_PARAM = bool(auth.get("accept_query_param", True))
    if not ACCEPT_BEARER and not ACCEPT_QUERY_PARAM:
        print("ERROR: auth.accept_bearer and auth.accept_query_param cannot both be false", flush=True)
        sys.exit(1)
    LOG_TO_CONSOLE = bool(CONFIG.get("log_to_console", True))
    LOG_TO_FILE = bool(CONFIG.get("log_to_file", True))
    IP_LOG_TO_FILE = bool(CONFIG.get("ip_log_to_file", True))
    log_path = _resolve_log_file(config_path, CONFIG.get("log_file"))
    ip_log_path = _resolve_log_file(config_path, CONFIG.get("ip_log_file"))
    LOG_FILE = log_path if LOG_TO_FILE and log_path else None
    IP_STATS_FILE = ip_log_path if IP_LOG_TO_FILE and ip_log_path else None
    for path in (LOG_FILE, IP_STATS_FILE):
        if path:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)


def log(msg):
    if LOG_TO_CONSOLE:
        print(msg, flush=True)
    if LOG_FILE:
        with _file_lock:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(msg + "\n")


def _ip_cell(value):
    return "" if value is None else str(value)


def _load_ip_stats():
    stats = {}
    if not IP_STATS_FILE or not os.path.exists(IP_STATS_FILE):
        return stats
    with open(IP_STATS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split("\t")]
            if len(parts) != 3:
                continue
            if parts[0] == "ipv4" and parts[1] == "ipv6" and parts[2] == "count":
                continue
            try:
                count = int(parts[2])
            except ValueError:
                continue
            stats[(parts[0], parts[1])] = count
    return stats


def _ip_stats_column_widths(stats):
    ipv4_width = max([len("ipv4")] + [len(v4) for v4, _ in stats])
    ipv6_width = max([len("ipv6")] + [len(v6) for _, v6 in stats])
    count_width = max([len("count")] + [len(str(c)) for c in stats.values()])
    return ipv4_width, ipv6_width, count_width


def _format_ip_stats_line(ipv4, ipv6, count, widths):
    w4, w6, wc = widths
    return f"{ipv4.ljust(w4)}\t{ipv6.ljust(w6)}\t{str(count).rjust(wc)}"


def _write_ip_stats(stats):
    widths = _ip_stats_column_widths(stats)
    tmp_path = IP_STATS_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(_format_ip_stats_line("ipv4", "ipv6", "count", widths) + "\n")
        for (ipv4, ipv6), count in sorted(stats.items()):
            f.write(_format_ip_stats_line(ipv4, ipv6, count, widths) + "\n")
    os.replace(tmp_path, IP_STATS_FILE)


def record_ip_stats(ipv4, ipv6):
    if not IP_STATS_FILE:
        return
    key = (_ip_cell(ipv4), _ip_cell(ipv6))
    with _file_lock:
        stats = _load_ip_stats()
        stats[key] = stats.get(key, 0) + 1
        _write_ip_stats(stats)


def is_already_running(pid_file):
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r", encoding="utf-8") as f:
                pid = int(f.read())
            os.kill(pid, 0)
            print(f"Already running with PID {pid}, exiting {script_name}.", flush=True)
            return True
        except (OSError, ValueError):
            print(f"Stale or invalid PID file found, continuing {script_name}.", flush=True)
            os.remove(pid_file)
    return False


def save_pid(pid_file):
    with open(pid_file, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))


def _first_forwarded_ip(value):
    if not value:
        return None
    for part in value.split(","):
        candidate = part.strip()
        if candidate:
            return candidate
    return None


def normalize_ip_string(ip_str):
    ip_str = (ip_str or "").strip()
    if not ip_str:
        return ""
    if ip_str.startswith("[") and "]" in ip_str:
        return ip_str[1 : ip_str.index("]")]
    if ip_str.count(":") == 1 and "." in ip_str.split(":", 1)[0]:
        return ip_str.rsplit(":", 1)[0]
    return ip_str


def get_client_ip():
    forwarded = _first_forwarded_ip(request.headers.get("X-Forwarded-For"))
    if forwarded:
        return normalize_ip_string(forwarded)
    real_ip = normalize_ip_string(request.headers.get("X-Real-IP"))
    if real_ip:
        return real_ip
    return normalize_ip_string(request.remote_addr)


def classify_client_ip(ip_str):
    ipv4 = None
    ipv6 = None
    if not ip_str:
        return ipv4, ipv6
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return ipv4, ipv6
    if addr.version == 4:
        ipv4 = str(addr)
    else:
        ipv6 = str(addr)
    return ipv4, ipv6


def _token_from_request():
    if ACCEPT_QUERY_PARAM:
        query_token = request.args.get("token", "")
        if query_token:
            return query_token
    if ACCEPT_BEARER:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            bearer = auth_header[7:].strip()
            if bearer:
                return bearer
        header_token = request.headers.get("X-Auth-Token", "")
        if header_token:
            return header_token
    return ""


def auth_status():
    provided = _token_from_request()
    if not provided:
        return "missing"
    if hmac.compare_digest(str(provided), str(AUTH_TOKEN)):
        return "ok"
    return "invalid"


def token_ok():
    return auth_status() == "ok"


@app.route("/whatsmyip", methods=["GET"])
def whatsmyip():
    if not token_ok():
        return jsonify({"error": "unauthorized"}), 401
    ipv4, ipv6 = classify_client_ip(get_client_ip())
    record_ip_stats(ipv4, ipv6)
    return jsonify({"ipv4": ipv4, "ipv6": ipv6})


@app.after_request
def log_request(response):
    client_ip = get_client_ip() or "-"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {request.method} {request.path} from {client_ip}"
    if request.path == "/whatsmyip":
        line += f" auth={auth_status()}"
    line += f" -> {response.status_code}"
    log(line)
    return response


@app.errorhandler(404)
def not_found(_e):
    return "", 404


def cleanup_and_exit(*_args):
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR: Missing config file argument", flush=True)
        print(f"Usage: python3 {script_name} settings.json", flush=True)
        sys.exit(1)

    load_config(sys.argv[1])

    if is_already_running(PID_FILE):
        sys.exit(0)

    save_pid(PID_FILE)
    signal.signal(signal.SIGINT, cleanup_and_exit)
    signal.signal(signal.SIGTERM, cleanup_and_exit)

    port = int(require_config("port"))
    if LOG_TO_CONSOLE or LOG_FILE or IP_STATS_FILE:
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
    print(
        f"Auth: accept_bearer={ACCEPT_BEARER}, accept_query_param={ACCEPT_QUERY_PARAM}",
        flush=True,
    )
    def _file_log_status(enabled, path):
        if not enabled:
            return "false"
        if path:
            return f"true ({path})"
        return "true (no path set)"

    print("Logging:", flush=True)
    print(f"  log_to_console={LOG_TO_CONSOLE}", flush=True)
    print(f"  log_to_file={_file_log_status(LOG_TO_FILE, LOG_FILE)}", flush=True)
    print(f"  ip_log_to_file={_file_log_status(IP_LOG_TO_FILE, IP_STATS_FILE)}", flush=True)
    print(f"{script_name} listening on http://0.0.0.0:{port}/whatsmyip", flush=True)
    app.run(host="0.0.0.0", port=port)
