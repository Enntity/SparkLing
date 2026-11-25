# SPDX-License-Identifier: AGPL-3.0-only
"""Decode-path next-token distributions over many contexts: cuts through the
fixed passages every ~45 characters plus 100 GSM8K questions; each context is
continued greedily for 6 tokens with logprobs=5.
usage: dist_decode2.py PORT MODEL QUESTIONS.json OUT.jsonl"""
import json, sys, urllib.request
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from dist_ling import PASSAGES

port, model, questions, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
contexts = []
for name, text in PASSAGES.items():
    cut = 45
    while cut < len(text) - 10:
        space = text.rfind(" ", 0, cut)
        contexts.append((f"{name}@{cut}", text[: space if space > 0 else cut]))
        cut += 45
for i, q in enumerate(json.load(open(questions))):
    contexts.append((f"gsm8k@{i}", f"Question: {q}\nAnswer: Let's think step by step."))
with open(out, "w") as f:
    for key, prompt in contexts:
        body = dict(model=model, prompt=prompt, max_tokens=6, temperature=0, seed=31, logprobs=5)
        req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        lp = json.load(urllib.request.urlopen(req, timeout=600))["choices"][0]["logprobs"]
        f.write(json.dumps(dict(passage=key, tokens=lp["tokens"], top_logprobs=lp["top_logprobs"])) + "\n")
print(out, len(contexts))
