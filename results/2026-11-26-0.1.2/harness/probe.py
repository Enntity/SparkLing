"""Greedy exactness and decode-speed probe for one SparkLing endpoint.
usage: probe.py PORT MAX_TOKENS [MODEL] > out.jsonl"""
import json, sys, time, urllib.request
PORT = int(sys.argv[1]) if __name__ == "__main__" else 0
N = int(sys.argv[2]) if __name__ == "__main__" else 0
MODEL = sys.argv[3] if __name__ == "__main__" and len(sys.argv) > 3 else "ling-3.2-air-atlas"
PROMPTS = [
 ("count", "Count upward from one using English words separated by commas. Continue through one hundred."),
 ("prose", "Describe how an archivist would restore order to a box of unlabeled photographs. Write one concrete paragraph."),
 ("code", "Write a Python function that merges two sorted lists into a new sorted list. Give only the function definition and body."),
 ("story", "Write a short story about a lighthouse keeper who finds a message in a bottle. Use vivid detail."),
 ("explain", "Explain how a refrigerator moves heat out of its interior, step by step, for a curious teenager."),
 ("json", "Return a JSON object describing three fictional cities, each with name, population, founding_year and a list of two landmarks. Output only JSON."),
 ("rust", "Write a Rust function that parses a CSV line with quoted fields into a Vec<String>. Include a few unit tests."),
 ("essay", "Argue for and against four-day work weeks in two balanced paragraphs."),
]
def metric():
    try:
        raw = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/metrics", timeout=10).read().decode()
    except Exception:
        return {}
    return {k: float(v) for line in raw.splitlines() if line.startswith(("vllm:spec_decode_num_", "atlas_spec_decode_verify_total"))
            for k, v in [line.rsplit(" ", 1)] if not k.endswith("_created")}
def run(prompt):
    body = dict(model=MODEL, messages=[{"role": "user", "content": prompt}], max_tokens=N,
                temperature=0, seed=31, stream=True, chat_template_kwargs={"enable_thinking": False},
                stream_options={"include_usage": True})
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    t0 = time.time(); first = None; text = []; usage = {}
    with urllib.request.urlopen(req, timeout=900) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            d = json.loads(line[5:])
            if d.get("usage"): usage = d["usage"]
            for c in d.get("choices", []):
                piece = (c.get("delta") or {}).get("content")
                if piece:
                    if first is None: first = time.time()
                    text.append(piece)
    end = time.time(); n = usage.get("completion_tokens", 0)
    rate = (n - 1) / (end - first) if first and n > 1 and end > first else None
    return dict(text="".join(text), completion_tokens=n, ttft_s=(first - t0) if first else None, tok_s=rate)
if __name__ == "__main__":
    for name, prompt in PROMPTS:
        before = metric(); out = run(prompt); after = metric()
        print(json.dumps(dict(probe=name, **out, spec={k: v - before.get(k, 0) for k, v in after.items()})), flush=True)
