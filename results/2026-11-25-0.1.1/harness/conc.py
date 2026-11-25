# SPDX-License-Identifier: AGPL-3.0-only
"""Concurrent decode probe. usage: conc.py PORT MODEL MAXTOK N [N ...]
Each level sends N distinct prompts at once (greedy, thinking off) and reports
aggregate completion tok/s over the wall clock, median per-stream decode rate
and median time to first token."""
import json, statistics, sys, threading, time, urllib.request
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from probe import PROMPTS
PORT, MODEL, N = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
def one(i, out):
    name, prompt = PROMPTS[i % len(PROMPTS)]
    body = dict(model=MODEL, messages=[{"role": "user", "content": prompt + f" (Variant {i}.)"}], max_tokens=N,
                temperature=0, seed=31 + i, stream=True, chat_template_kwargs={"enable_thinking": False},
                stream_options={"include_usage": True})
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time(); first = None; n = 0
    with urllib.request.urlopen(req, timeout=1800) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]": continue
            d = json.loads(line[5:])
            if d.get("usage"): n = d["usage"].get("completion_tokens", n)
            if first is None and any((c.get("delta") or {}).get("content") for c in d.get("choices", [])): first = time.time()
    end = time.time()
    out[i] = dict(n=n, ttft=(first or end) - t0, rate=(n - 1) / (end - first) if first and n > 1 else 0, end=end, start=t0)
for level in map(int, sys.argv[4:]):
    out = {}; threads = [threading.Thread(target=one, args=(i, out)) for i in range(level)]
    t0 = time.time(); [t.start() for t in threads]; [t.join() for t in threads]; wall = max(o["end"] for o in out.values()) - t0
    total = sum(o["n"] for o in out.values())
    print(json.dumps(dict(clients=level, aggregate_tok_s=round(total / wall, 2), median_stream_tok_s=round(statistics.median(o["rate"] for o in out.values()), 2),
                          median_ttft_s=round(statistics.median(o["ttft"] for o in out.values()), 3), tokens=total, wall_s=round(wall, 2))), flush=True)
