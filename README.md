# health_endpoint

Two related tools in one repository:

| Component | Purpose |
|-----------|---------|
| **health_server** | Minimal Flask HTTP server exposing `GET /health` (200 OK) for container and load-balancer probes |
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

## IP change monitor (`ip_change.py`)

### Configuration

1. Copy the example settings file and edit it (real settings files are gitignored):

   ```bash
   cp ip_change-settings.example.json ip_change-home-settings.json
   ```

2. Set hostnames, optional expected IPs, Kuma push URLs, and paths as needed.

3. Public IP lookup services are defined in [public_ip_lookup_services.json](public_ip_lookup_services.json) (referenced by `public_ip_lookup_config` in your settings file).

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

[run_ip_change.sh](run_ip_change.sh) runs the monitor with a fixed config path (edit the script if your settings file name differs):

```bash
chmod +x run_ip_change.sh
./run_ip_change.sh
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
| `public_ip_lookup_services.json` | Public IP API URLs and options |
| `requirements.txt` | Python dependencies |
| `install_deps.sh` / `install_deps.bat` | Create `.venv` and install dependencies |
| `activate_venv.sh` / `activate_venv.bat` | Activate `.venv` |
| `Dockerfile` | Image for `health_server` only |
| `rebuild.ubuntu.sh` / `rebuild.windows.bat` | Rebuild and run container |
| `run_ip_change.sh` | Example host runner for `ip_change.py` |

---

## Gitignored local files

- `*settings.json` — your real IP monitor config
- `ip_state*.json` — persisted monitor state
- `state_output/` — lookup service rotation state
- `.venv/` — local virtual environment
