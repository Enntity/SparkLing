"""Batch-invariance check. usage: same.py PORT MODEL MAXTOK N [N ...]
Greedy texts of N distinct prompts sent at once must equal each prompt sent alone."""
import json, sys, threading, urllib.request
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from probe import PROMPTS
PORT, MODEL, MAXTOK = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
def one(i):
    name, prompt = PROMPTS[i % len(PROMPTS)]
    body = dict(model=MODEL, messages=[{"role": "user", "content": prompt + f" (Variant {i}.)"}], max_tokens=MAXTOK,
                temperature=0, seed=31 + i, chat_template_kwargs={"enable_thinking": False})
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=1800))["choices"][0]["message"]["content"]
top = max(map(int, sys.argv[4:]))
solo = [one(i) for i in range(top)]
for level in map(int, sys.argv[4:]):
    out = {}
    ts = [threading.Thread(target=lambda i=i: out.__setitem__(i, one(i))) for i in range(level)]
    [t.start() for t in ts]; [t.join() for t in ts]
    bad = [i for i in range(level) if out[i] != solo[i]]
    print(json.dumps(dict(clients=level, identical=level - len(bad), differ=bad,
          first_diff=[next((k for k,(a,b) in enumerate(zip(out[i], solo[i])) if a!=b), min(len(out[i]),len(solo[i]))) for i in bad])), flush=True)
