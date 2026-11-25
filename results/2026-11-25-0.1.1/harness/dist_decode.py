# SPDX-License-Identifier: AGPL-3.0-only
"""Decode-path next-token distributions: each passage's first 60% is the prompt
and the engine continues greedily for 48 tokens with logprobs=5. Scoring
(dist_decode_score) compares engines only while their texts still agree.
usage: dist_decode.py PORT MODEL OUT.jsonl"""
import json, sys, urllib.request
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from dist_ling import PASSAGES

port, model, out = sys.argv[1], sys.argv[2], sys.argv[3]
with open(out, "w") as f:
    for name, text in PASSAGES.items():
        body = dict(model=model, prompt=text[: int(len(text) * 0.6)], max_tokens=48, temperature=0, seed=31, logprobs=5)
        req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        lp = json.load(urllib.request.urlopen(req, timeout=600))["choices"][0]["logprobs"]
        f.write(json.dumps(dict(passage=name, tokens=lp["tokens"], top_logprobs=lp["top_logprobs"])) + "\n")
print(out)
