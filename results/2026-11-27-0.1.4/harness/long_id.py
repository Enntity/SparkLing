# usage: long_id.py DEPTH...  greedy 64 tokens after a fixed RigMark prompt of DEPTH tokens (same prompt every run)
import json, os, pathlib, sys, urllib.request
MODEL = os.environ.get("MODEL", "ling-3.2-air-atlas")
root = pathlib.Path.home() / "models/sparkling/claude-smb/upstream/rigmark"
sys.path.insert(0, str(root))
import bench
client = bench.Client("http://127.0.0.1:8897", "", 1200)
prompts, _ = bench.load_prompts(root / "prompts.json")
for depth in map(int, sys.argv[1:]):
    ids = bench.exact_token_ids(client, MODEL, depth, prompts["prefill_unit"], "claude-identity-fixed")
    body = dict(model=MODEL, prompt=ids, max_tokens=64, temperature=0, seed=7, logprobs=1)
    req = urllib.request.Request("http://127.0.0.1:8897/v1/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=1200))
    c = r["choices"][0]
    lp = (c.get("logprobs") or {}).get("token_logprobs")
    print(json.dumps(dict(depth=depth, prompt=r["usage"]["prompt_tokens"], text=c["text"], logprobs=lp)))
