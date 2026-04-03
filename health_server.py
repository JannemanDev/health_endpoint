from flask import Flask, Response
import os
import sys
import signal

app = Flask(__name__)
script_name = os.path.basename(__file__)
base_name = os.path.splitext(script_name)[0]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(SCRIPT_DIR, base_name + ".pid")


def is_already_running(pid_file):
    if os.path.exists(pid_file):
        script_name = os.path.basename(__file__)
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read())
            os.kill(pid, 0)  # Check if process is alive else it will throw an exception
            print(f"Already running with PID {pid}, exiting {script_name}.", flush=True)
            return True
        except (OSError, ValueError):
            print(f"Stale or invalid PID file found, continuing {script_name}.", flush=True)
            os.remove(pid_file)
    return False


def save_pid(pid_file):
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))


@app.route("/health", methods=["GET"])
def health():
    return Response(status=200)


@app.errorhandler(404)
def not_found(e):
    return Response(status=404)


def cleanup_and_exit(*args):
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    sys.exit(0)


if __name__ == "__main__":
    if is_already_running(PID_FILE):
        sys.exit(0)

    save_pid(PID_FILE)
    signal.signal(signal.SIGINT, cleanup_and_exit)
    signal.signal(signal.SIGTERM, cleanup_and_exit)

    app.run(host="0.0.0.0", port=8000)
