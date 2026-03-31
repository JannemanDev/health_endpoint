import socket
import requests
import json
import commentjson
import os
import sys
import time
from datetime import datetime


# ---------------------------
# Require config file
# ---------------------------
if len(sys.argv) < 2:
    print("ERROR: Missing config file argument")
    print("Usage: python3 ip_monitor.py config.json")
    sys.exit(1)

CONFIG_PATH = sys.argv[1]

if not os.path.exists(CONFIG_PATH):
    print(f"ERROR: Config file not found: {CONFIG_PATH}")
    sys.exit(1)

with open(CONFIG_PATH, "r") as f:
    CONFIG = commentjson.load(f)


# ---------------------------
# Required config validation
# ---------------------------
def require(key):
    if key not in CONFIG:
        print(f"ERROR: Missing required config key: {key}")
        sys.exit(1)
    return CONFIG[key]


HOSTNAMES = require("hostnames")
STATE_FILE = require("state_file")

CHECK_DNS = CONFIG.get("check_dns", True)
CHECK_PUBLIC_IP = CONFIG.get("check_public_ip", True)

KUMA = CONFIG.get("kuma", {})
KUMA_ENABLED = KUMA.get("enabled", False)

PUBLIC_IP_SERVICE = CONFIG.get("public_ip_service", "https://api.ipify.org")
PUBLIC_IP_CONFIG = CONFIG.get("public_ip", {})
EXPECTED_PUBLIC_IP = (PUBLIC_IP_CONFIG.get("expected_ip") or "").strip() or None


# ---------------------------
# Timestamp (single source of truth per run)
# ---------------------------
def get_timestamp():
    ts = time.time()
    return {
        "unix": ts,
        "human": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
    }


def log(msg):
    print(msg)


# ---------------------------
# State handling
# ---------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------
# Network checks
# ---------------------------
def get_dns_ip(hostname):
    try:
        return socket.gethostbyname(hostname)
    except Exception:
        return None


def get_public_ip():
    try:
        return requests.get(PUBLIC_IP_SERVICE, timeout=5).text.strip()
    except Exception:
        return None


# ---------------------------
# Uptime Kuma push (optional)
# ---------------------------
def notify_kuma(message):
    if not KUMA_ENABLED:
        return

    params = {"status": "down", "msg": message}

    timeout_seconds = KUMA.get("timeout_seconds", 5)
    push_url = KUMA["push_url"]
    prepared_url = requests.Request("GET", push_url, params=params).prepare().url

    log(f"[KUMA] Sending GET {prepared_url} with timeout={timeout_seconds}s")

    try:
        requests.get(push_url, params=params, timeout=timeout_seconds)
        log("[KUMA] Push sent")
    except Exception as e:
        log(f"[WARN] Kuma notify failed: {e}")


# ---------------------------
# Main
# ---------------------------
def main():
    state = load_state()

    run_ts = get_timestamp()

    public_ip = get_public_ip() if CHECK_PUBLIC_IP else None

    all_changes = []

    # ---------------------------
    # Public IP check
    # ---------------------------
    log(f"[TIME] {run_ts['human']}")

    last_public = state.get("public_ip", {}).get("ip")

    if public_ip:
        log(f"[PUBLIC IP] {public_ip}")

        if last_public and public_ip != last_public:
            all_changes.append(f"Public IP changed {last_public} → {public_ip}")
        elif not last_public:
            all_changes.append(f"Public IP initial: {public_ip}")

        if EXPECTED_PUBLIC_IP and public_ip != EXPECTED_PUBLIC_IP:
            all_changes.append(
                f"Public IP {public_ip} != expected {EXPECTED_PUBLIC_IP}"
            )

    # ---------------------------
    # Host DNS checks
    # ---------------------------
    host_results = state.get("hosts", {})

    for host_entry in HOSTNAMES:
        if not isinstance(host_entry, dict):
            continue

        host = host_entry.get("hostname")
        expected_ip = (host_entry.get("expected_ip") or "").strip() or None

        if not host:
            continue

        dns_ip = get_dns_ip(host) if CHECK_DNS else None
        last_dns = host_results.get(host, {}).get("dns_ip")

        if dns_ip:
            if last_dns and dns_ip != last_dns:
                all_changes.append(f"{host}: DNS {last_dns} → {dns_ip}")
            elif not last_dns:
                all_changes.append(f"{host}: DNS initial {dns_ip}")
            if expected_ip and dns_ip != expected_ip:
                all_changes.append(f"{host}: DNS {dns_ip} != expected {expected_ip}")

        host_results[host] = {"dns_ip": dns_ip, "timestamp": run_ts}

    # ---------------------------
    # Output
    # ---------------------------
    if all_changes:
        msg = " | ".join(all_changes)
        log("[CHANGE] " + msg)
        notify_kuma(msg)
    else:
        log("[OK] No changes detected")

    # ---------------------------
    # Save state
    # ---------------------------
    state["public_ip"] = {"ip": public_ip, "timestamp": run_ts}

    state["hosts"] = host_results

    state["script_last_run_timestamp"] = run_ts

    save_state(state)


if __name__ == "__main__":
    main()
