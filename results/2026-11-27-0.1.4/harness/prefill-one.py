# usage: prefill-one.py DEPTH [INDEX]  one cold RigMark prefill of exactly DEPTH tokens, prints TTFT
import json, pathlib, sys
root = pathlib.Path.home() / "models/sparkling/claude-smb/upstream/rigmark"
sys.path.insert(0, str(root))
import bench
depth, index = int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 1
client = bench.Client("http://127.0.0.1:8897", "", 600)
prompts, _ = bench.load_prompts(root / "prompts.json")
tokens = bench.exact_token_ids(client, "ling-3.2-air-atlas", depth, prompts["prefill_unit"], bench.nonce("claude-prof", "prefill", depth, index))
r = bench.prefill_once(client, "ling-3.2-air-atlas", tokens)
print(json.dumps({k: r.get(k) for k in ("prompt_tokens", "ttft_seconds", "cached_prompt_tokens")} | {"depth": depth}))
