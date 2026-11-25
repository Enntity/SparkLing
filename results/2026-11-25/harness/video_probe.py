# SPDX-License-Identifier: AGPL-3.0-only
"""Video and document checks. usage: video_probe.py PORT [MODEL]"""
import base64, json, sys, time, urllib.request, urllib.error, re
from pathlib import Path
PORT = int(sys.argv[1]); MODEL = sys.argv[2] if len(sys.argv) > 2 else "ling-3.2-air-atlas"
V = Path(__file__).resolve().parent / "bench"
CASES = [
 ("gif-red-blue", "video/red-blue.gif", "image/gif", "video_url", "Name the first and last colors shown in the video, in order. Use two words.", lambda a: re.findall(r"\b(?:red|blue)\b", a) == ["red", "blue"]),
 ("mp4-red-blue", "video/red-blue.mp4", "video/mp4", "video_url", "Name the first and last colors shown in the video, in order. Use two words.", lambda a: re.findall(r"\b(?:red|blue)\b", a) == ["red", "blue"]),
 ("mp4-count8", "video/count8.mp4", "video/mp4", "video_url", "A large number is shown in the video and it changes over time. List every number you see, in the order they appear, separated by commas.", lambda a: re.findall(r"\d", a) == list("12345678")),
 ("gif-count8", "video/count8.gif", "image/gif", "video_url", "A large number is shown in the video and it changes over time. List every number you see, in the order they appear, separated by commas.", lambda a: re.findall(r"\d", a) == list("12345678")),
 ("mp4-long90", "video/long90.mp4", "video/mp4", "video_url", "This is a 90-second synthetic test pattern. Describe what it shows in one sentence.", lambda a: len(a) > 20),
 ("invoice", "images/invoice.png", "image/png", "image_url", "Transcribe the supplier name, invoice number, and total as printed. Answer concisely.", lambda a: all(f in a.lower().replace("*", "") for f in ("harbor street bakery", "48213", "66.15"))),
 ("grid", "images/grid.png", "image/png", "image_url", "Read the labelled grid. Give the color of cells A1, B2 and C3.", lambda a: all(re.search(l + r"[^a-z0-9]{0,12}(?:is\s+)?" + c + r"\b", a.lower().replace("*", "")) for l, c in (("a1", "red"), ("b2", "blue"), ("c3", "green")))),
]
ok = True
for name, path, mime, field, prompt, check in CASES:
    data = base64.b64encode((V / path).read_bytes()).decode()
    body = {"model": MODEL, "temperature": 0, "seed": 31, "max_tokens": 96, "messages": [{"role": "user", "content": [{"type": field, field: {"url": f"data:{mime};base64,{data}"}}, {"type": "text", "text": prompt}]}], "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    try:
        m = json.load(urllib.request.urlopen(req, timeout=600)); a = m["choices"][0]["message"].get("content") or ""
        r = {"answer": a, "prompt_tokens": m["usage"]["prompt_tokens"], "seconds": round(time.time() - t0, 2), "passed": bool(check(a))}
    except urllib.error.HTTPError as e:
        r = {"status": e.code, "error": e.read().decode()[:400], "passed": False}
    ok &= r["passed"]
    print(json.dumps({"case": name, **r}), flush=True)
sys.exit(0 if ok else 1)
