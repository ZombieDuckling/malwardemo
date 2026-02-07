# Red Team Demo — Tests

## Playwright test (webapp-testing skill)

Run the demo UI test with the server started automatically:

```bash
cd demo-ui
python .agents/skills/webapp-testing/scripts/with_server.py \
  --server "python app.py" --port 5000 \
  -- python tests/test_demo_flow.py
```

Requires: `playwright` and Chromium (`playwright install chromium`).

Or start the server yourself and run the test:

```bash
# Terminal 1
cd demo-ui && .venv/bin/python app.py

# Terminal 2
cd demo-ui && python tests/test_demo_flow.py
```

The test checks that the Red Team demo page loads, main sections are visible, and the footer disclaimer is present.
