# SPDX-License-Identifier: AGPL-3.0-only
"""Record the demo page in real time at 1920x1080.
usage: record.py OUT_DIR  (the page must be served on 127.0.0.1:8700)"""
import sys, time
from playwright.sync_api import sync_playwright
out = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1920, "height": 1080}, record_video_dir=out, record_video_size={"width": 1920, "height": 1080})
    page = ctx.new_page()
    logs = []
    page.on("console", lambda m: logs.append(f"{m.type}: {m.text}"))
    page.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
    t = time.time()
    page.goto("http://127.0.0.1:8700/index.html?autoplay=1")
    page.wait_for_function("window.__done === true", timeout=600000, polling=1000)
    page.screenshot(path=f"{out}/final.png")
    print("elapsed", round(time.time() - t, 1))
    print("\n".join(logs))
    import json; json.dump(page.evaluate("window.__results"), open(f"{out}/results.json", "w"), indent=1)
    ctx.close(); b.close()
