# health_endpoint

Two related tools in one repository:

| Component | Purpose |
|-----------|---------|
| **health_server** | Minimal Flask HTTP server exposing `GET /health` (200 OK) for container and load-balancer probes |
| **whatsmyip_server** | Token-protected `GET /whatsmyip` returning the client IPv4/IPv6 seen on the request (JSON) |
| **ip_change** | Monitors DNS and public IP changes, keeps state on disk, and optionally notifies [Uptime Kuma](https://github.com/louislam/uptime-kuma) push monitors |

The Docker image runs only `health_server.py`. `ip_change.py` is meant to run on a host (cron, Task Scheduler, or manually)—often the same machine whose IP or DNS you want to watch.

---

## Requirements

- **Python 3.12+** (for local `ip_change` / `health_server` runs)
- **Docker** (for the containerized health endpoint)
- Dependencies: see [requirements.txt](requirements.txt) (`Flask`, `requests`, `commentjson`)

---

## Health server (Docker)

The container listens on port **8000** internally. Map it to a host port (e.g. **9000**) when you run it.

### Build and run (Linux)

Use one of the helper scripts:

```bash
./rebuild.ubuntu.sh   # stop, remove, build, run
./run_container.sh    # run only (image must exist)
./start_container.sh  # start an existing stopped container
```

### Build and run (Windows)

```bat
rebuild.windows.bat
```

### Verify

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:9000/health
# Expected: 200
```

### Run health_server locally (without Docker)

```bash
python3 health_server.py
# Listens on http://0.0.0.0:8000/health
```

With the project venv (see below):

```bash
source ./activate_venv.sh
python health_server.py
```

---

## WhatsMyIP server (`whatsmyip_server.py`)

Token-protected endpoint that reports which client address the server saw on the connection. A single HTTP request is either IPv4 or IPv6, so one of the fields is usually `null`; call over both stacks (or use separate v4/v6 hostnames) to learn both addresses.

### Configuration

```bash
cp whatsmyip-settings.example.json whatsmyip-settings.json
# Edit port and token
```

### Run

```bash
./run_whatsmyip_server.sh whatsmyip-settings.json
```

### Verify

```bash
curl -s -H "Authorization: Bearer YOUR_TOKEN" "http://localhost:8080/whatsmyip"
# {"ipv4":"1.2.3.4","ipv6":null}
```

Auth methods are configurable under `auth` in settings (defaults: bearer on, query off in the example file):

- `accept_bearer`: `Authorization: Bearer <token>` or `X-Auth-Token`
- `accept_query_param`: `?token=<token>` (avoid on production; URLs leak into logs)

At least one must be enabled.

Request logging prints every request with client IP, auth result on `/whatsmyip` (`ok` / `missing` / `invalid`), and status code. Tokens are never logged.

- `log_to_console` (default `true`) — request log to stdout
- `log_to_file` (default `true`) — request log to `log_file` when set
- `log_file` (optional) — request log path; relative paths are resolved from the settings file directory
- `ip_log_to_file` (default `true`) — IP stats to `ip_log_file` when set
- `ip_log_file` (optional) — tab-separated stats for successful `/whatsmyip` responses only. First line is header `ipv4`, `ipv6`, `count`; each unique address pair is one data row; `count` increments on repeat visits. Empty column when that stack was not seen on the request.

---

## IP change monitor (`ip_change.py`)

### Configuration

1. Copy the example settings file and edit it (real settings files are gitignored):

   ```bash
   cp ip_change-settings.example.json ip_change-home-settings.json
   ```

2. Set hostnames, optional expected IPs, Kuma push URLs, and paths as needed.

3. Public IP lookup services are defined in a JSON file referenced by `public_ip_lookup_config` in your settings file (default: [public_ip_lookup_services.json](public_ip_lookup_services.json)).

   **Hetzner / dual-stack (IPv4 + IPv6):** On hosts with both addresses, many generic “what is my IP” APIs return the **IPv6** address. That can make `ip_change.py` report false changes or compare against the wrong address. Use [public_ip_lookup_services_hetzner.json](public_ip_lookup_services_hetzner.json) instead — a shorter list of services chosen to return **IPv4 only** (for example `https://ipv4.icanhazip.com` and `https://v4.ident.me/.json`).

   In your settings file:

   ```json
   "public_ip_lookup_config": "public_ip_lookup_services_hetzner.json"
   ```

4. State is written to the file named in `state_file` (default `ip_state.json`). Lookup rotation state goes under `state_output/` when configured.

### Install Python dependencies

**Linux / macOS / WSL / Git Bash**

```bash
chmod +x install_deps.sh activate_venv.sh
./install_deps.sh
```

**Windows (CMD)**

```bat
install_deps.bat
```

This creates a `.venv` directory in the project root and installs packages from `requirements.txt`.

### Activate the virtual environment

**Linux / macOS / WSL / Git Bash** — must *source* the script:

```bash
source ./activate_venv.sh
```

**Windows CMD**

```bat
call activate_venv.bat
```

**Windows PowerShell**

```powershell
.\.venv\Scripts\Activate.ps1
```

To leave the venv: `deactivate`.

---

### Running `ip_change.py`

The script requires one argument: path to a JSON settings file (supports `//` comments via `commentjson`).

```text
python3 ip_change.py <config.json>
```

Replace `<config.json>` with your real settings file, e.g. `ip_change-home-settings.json`.

#### 1. System Python (no venv)

```bash
cd /path/to/health_endpoint
python3 ip_change.py ip_change-home-settings.json
```

#### 2. Virtual environment (recommended)

```bash
cd /path/to/health_endpoint
source ./activate_venv.sh          # Linux / Git Bash
python ip_change.py ip_change-home-settings.json
```

Windows CMD after `call activate_venv.bat`:

```bat
python ip_change.py ip_change-home-settings.json
```

#### 3. Explicit venv interpreter (no activation)

**Linux:**

```bash
.venv/bin/python ip_change.py ip_change-home-settings.json
```

**Windows:**

```bat
.venv\Scripts\python.exe ip_change.py ip_change-home-settings.json
```

#### 4. Wrapper script

[run_ip_change.sh](run_ip_change.sh) runs the monitor; pass your settings file as the only argument (uses `.venv/bin/python` when present):

```bash
chmod +x run_ip_change.sh
./run_ip_change.sh ip_change-settings.json
```

#### 5. Cron (example)

Run every 15 minutes with the project venv:

```cron
*/15 * * * * /path/to/health_endpoint/.venv/bin/python /path/to/health_endpoint/ip_change.py /path/to/health_endpoint/ip_change-home-settings.json >> /var/log/ip_change.log 2>&1
```

#### 6. Windows Task Scheduler

- **Program:** `C:\path\to\health_endpoint\.venv\Scripts\python.exe`
- **Arguments:** `ip_change.py ip_change-home-settings.json`
- **Start in:** `C:\path\to\health_endpoint`

---

## Project layout

| File | Role |
|------|------|
| `health_server.py` | Flask `/health` endpoint |
| `ip_change.py` | DNS / public IP monitor |
| `ip_change-settings.example.json` | Sample config (copy to `*settings.json`) |
| `public_ip_lookup_services.json` | Default public IP API URLs and options |
| `public_ip_lookup_services_hetzner.json` | IPv4-only lookup list for Hetzner / dual-stack hosts |
| `requirements.txt` | Python dependencies |
| `install_deps.sh` / `install_deps.bat` | Create `.venv` and install dependencies |
| `activate_venv.sh` / `activate_venv.bat` | Activate `.venv` |
| `Dockerfile` | Image for `health_server` only |
| `rebuild.ubuntu.sh` / `rebuild.windows.bat` | Rebuild and run container |
| `run_ip_change.sh` | Host runner for `ip_change.py` (requires settings file argument) |

---

## Gitignored local files

- `*settings.json` — your real IP monitor config
- `ip_state*.json` — persisted monitor state
- `state_output/` — lookup service rotation state
- `.venv/` — local virtual environment
