# SPDX-License-Identifier: AGPL-3.0-only
import json, sys, time, urllib.request
sys.path.insert(0, "/bench")
from transformers import AutoTokenizer
from context_window import prompt_ids
tok = AutoTokenizer.from_pretrained("/ckpt", local_files_only=True)
window = int(sys.argv[1]); n = int(sys.argv[2])
ids = prompt_ids(tok, window - 12)
suffix = len(tok.encode("\nWhat archive key did I give at the beginning? Answer with only that one word.", add_special_tokens=False)) + 8
ids = ids[: len(ids) - suffix - n]
body = dict(model="ling-3.2-air-atlas", prompt=ids, max_tokens=n, temperature=0, seed=31, ignore_eos=True)
t = time.monotonic()
r = json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8897/v1/completions", json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=7200))
total = time.monotonic() - t
u = r["usage"]; ttft = u.get("time_to_first_token_ms", 0) / 1000
print(json.dumps(dict(prompt=u["prompt_tokens"], cached=u["prompt_tokens_details"]["cached_tokens"], out=u["completion_tokens"], ttft_s=round(ttft, 2), decode_tok_s=round((u["completion_tokens"] - 1) / max(total - ttft, 1e-6), 1), text=r["choices"][0]["text"][:120])))
