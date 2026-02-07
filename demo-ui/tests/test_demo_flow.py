#!/usr/bin/env python3
"""
Playwright test for the Red Team demo UI.
Run with the webapp-testing skill helper so the server is already up:

  cd demo-ui
  python .agents/skills/webapp-testing/scripts/with_server.py \
    --server "python app.py" --port 5000 \
    -- python tests/test_demo_flow.py

Or start the server manually and run: python tests/test_demo_flow.py
"""
import os
import sys

# Default to port 5000 when run under with_server.py
DEMO_PORT = int(os.environ.get("DEMO_PORT", "5000"))
BASE_URL = f"http://127.0.0.1:{DEMO_PORT}"


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        # Red Team demo page loaded
        title = page.title()
        assert "Red Team" in title or "RAT" in title, f"Expected security demo title, got: {title}"

        # Main content present
        header = page.locator("header h1").first
        assert header.is_visible(), "Header (h1) should be visible"
        assert "Red Team" in header.inner_text() or "RAT" in header.inner_text()

        # Connection status pill present
        pill = page.locator("#connectionPill").first
        assert pill.is_visible(), "Connection pill should be visible"

        # Step cards present
        step1 = page.locator("#step1").first
        assert step1.is_visible(), "Step 1 (Deploy target) should be visible"
        step2 = page.locator("#step2").first
        assert step2.is_visible(), "Step 2 (Execute payload) should be visible"
        step3 = page.locator("#step3").first
        assert step3.is_visible(), "Step 3 (C2 session) should be visible"

        # C2 command list present
        copy_block = page.locator("#c2CopyBlock").first
        assert copy_block.is_visible(), "C2 copy block should be visible"
        assert "id" in copy_block.inner_text() and "whoami" in copy_block.inner_text()

        # Footer disclaimer present
        footer = page.locator("footer").first
        assert footer.is_visible(), "Footer should be visible"
        assert "authorized" in footer.inner_text().lower()

        # Optional: screenshot for evidence
        out_dir = os.environ.get("PLAYWRIGHT_OUTPUT", os.path.dirname(__file__))
        screenshot_path = os.path.join(out_dir, "demo_loaded.png")
        page.screenshot(path=screenshot_path, full_page=False)
        print(f"Screenshot: {screenshot_path}")

        browser.close()

    print("Red Team demo UI: all checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
