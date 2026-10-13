import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_demo_ui_homepage_sets_safety_headers():
    app_module = load_module("demo_ui_app", ROOT / "demo-ui" / "app.py")

    client = app_module.app.test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert b"Red Team" in response.data or b"RAT" in response.data
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_demo_ui_safe_endpoints_work_without_docker_or_active_session():
    app_module = load_module("demo_ui_app_status", ROOT / "demo-ui" / "app.py")

    client = app_module.app.test_client()

    status = client.get("/api/status").get_json()
    assert status["listening"] is False
    assert status["session_active"] is False
    assert status["container_running"] is False

    empty_command = client.post("/api/command", json={"cmd": "   "}).get_json()
    assert empty_command == {"ok": False, "output": "Empty command"}

    no_session = client.post("/api/command", json={"cmd": "id"}).get_json()
    assert no_session["ok"] is False
    assert "No active session" in no_session["output"]

    activity = client.get("/api/container-activity").get_json()
    assert activity == {"ok": True, "output": "(container not running)"}


def test_victim_email_routes_and_attachment_trigger_are_testable(monkeypatch):
    app_module = load_module("victim_webapp", ROOT / "victim" / "webapp" / "app.py")
    triggered = []

    monkeypatch.setattr(app_module, "_run_payload", lambda: triggered.append(True))
    client = app_module.app.test_client()

    inbox = client.get("/")
    assert inbox.status_code == 200
    assert b"patient_lab_results" in inbox.data or b"Patient" in inbox.data

    assert client.get("/email/999").status_code == 404

    opened = client.post("/api/open-attachment").get_json()
    assert opened == {"ok": True, "message": "Opening attachment..."}
    assert triggered == [True]
