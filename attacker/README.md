# Attacker (host machine)

Run these on your **host**, not inside containers.

1. **Start the RAT listener** (do this first):
   ```bash
   python3 listener.py
   ```
   Or with a custom port: `python3 listener.py 4444`

2. Then start the victim container and trigger the "email" (see main README).
