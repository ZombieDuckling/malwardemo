# Red Team Demo: RAT via Phishing (Authorized Security Education)

This demo illustrates **remote access via malicious email attachment**: deploy a target, trigger payload execution (phishing), and interact through a C2 session. Built for **authorized security training and education** only.

## Architecture

| Role    | Where it runs | What it does |
|---------|----------------|--------------|
| **Red Team / C2** | Host machine | Listener (C2); controls target after implant beacons. |
| **Target** | Container `primary-doctor` | Simulated workstation; "opens" phishing attachment → implant runs and beacons to C2. |

## Prerequisites

- Docker and Docker Compose
- Python 3 on the host (for the listener or visual UI)

## Demo Options

You can run the demo **with a visual interface** (recommended for class) or **via the command line**.

---

### Option A: Visual interface (recommended)

**Everything runs from the web UI:** deploy target, execute payload, and run C2 commands from one page.

1. **Start the demo UI** (C2 listener + container control):
   ```bash
   cd demo-ui
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   .venv/bin/python app.py
   ```
   Use `PORT=5050 .venv/bin/python app.py` if port 5000 is in use.

2. **Open in a browser:**  
   **http://127.0.0.1:5000** (or the port you used)

3. **Run the demo:**
   - **1. Deploy target** — Click **"Deploy target container"**. Wait until status shows "Running".
   - **2. Execute payload** — Click the phishing email, then **"Open attachment (execute payload)"**. The implant beacons to C2.
   - **3. C2 session** — Copy a command from the list (e.g. `id`, `info`, `download /app/inbox/...`) and paste into the terminal. Output appears below.

The **Live target view** shows processes in the container so you can confirm the implant is running. For authorized security education only.

---

### Option B: Command-line only

1. **Start the attacker listener (on the host)**

In a terminal on your **host**:

```bash
cd attacker
python3 listener.py
```

Leave this running. You should see:

```
[*] RAT listener (attacker) on 0.0.0.0:4444
[*] Waiting for victim to open malicious email attachment...
```

2. **Start the victim container**

In another terminal:

```bash
docker compose up -d --build
```

3. **Simulate the victim opening the malicious email**

The "email" is simulated by the attachment in the container's inbox. When the "doctor" opens it, the payload runs and connects back to your listener.

Attach to the victim container and run the script that simulates opening the attachment:

```bash
docker compose exec primary-doctor /app/scripts/open_email_attachment.sh
```

4. **Observe the RAT session**

In the **attacker** terminal you should see the victim connect and a prompt:

```
[RAT Demo] Primary Doctor workstation connected. Session active.
[*] Session from (<IP>, <PORT>). Type commands (exit to close).

rat>
```

You can run commands on the victim (container), e.g.:

- `id`
- `whoami`
- `cat /etc/hostname`
- `ls /app/inbox`
- `exit` to close the session

## What This Demonstrates

1. **Delivery**: Malicious content delivered via "email" (simulated as a file in the victim's inbox).
2. **Execution**: Victim "opens" the attachment (here, runs the script that represents the disguised payload).
3. **Persistence / C2**: The payload connects back to the attacker (reverse shell), giving the attacker remote access (RAT-like behavior).

The attachment is disguised as `patient_lab_results.pdf` but is actually a Python script that opens a reverse shell—analogous to macro-enabled documents or disguised executables in real attacks.

## Files Overview

- **`victim/`** – Primary Doctor container: Dockerfile, simulated inbox payload, script to "open" attachment.
- **`attacker/`** – Standalone listener and instructions; run on the host (optional if using demo-ui).
- **`demo-ui/`** – Visual demo: Flask app with integrated listener, victim panel (fake email), and attacker panel (C2 terminal). Run `python3 app.py` and open http://127.0.0.1:5000.
- **`docker-compose.yml`** – Builds and runs the victim container; attacker is always the host.

## Testing the demo UI

From `demo-ui`, run the Playwright test (uses the webapp-testing skill):

```bash
cd demo-ui
python .agents/skills/webapp-testing/scripts/with_server.py \
  --server "python app.py" --port 5000 \
  -- python tests/test_demo_flow.py
```

See `demo-ui/tests/README.md` for details. Requires `playwright` and `playwright install chromium`.

## Cleanup

```bash
docker compose down
```

Stop the demo server with `Ctrl+C` in the terminal where it’s running.

---

**For authorized security education and testing only. Do not use against systems you do not own or have permission to test.**
