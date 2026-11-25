# SPDX-License-Identifier: AGPL-3.0-only
"""usage: summary.py RUN.jsonl [REFERENCE.jsonl]"""
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
ref = {d["probe"]: d["text"] for d in map(json.loads, open(sys.argv[2]))} if len(sys.argv) > 2 else {}
rates = []
for d in rows:
    s = d.get("spec", {}); acc = s.get("vllm:spec_decode_num_accepted_tokens_total"); dr = s.get("vllm:spec_decode_num_draft_tokens_total")
    same = "" if not ref else ("same" if ref.get(d["probe"]) == d["text"] else "DIFF@%d" % next((i for i, (a, b) in enumerate(zip(ref.get(d["probe"], ""), d["text"])) if a != b), min(len(ref.get(d["probe"], "")), len(d["text"]))))
    rates.append(d["tok_s"] or 0)
    print(f"{d['probe']:8s} n={d['completion_tokens']:4d} tok/s={d['tok_s'] or 0:6.2f} acc={acc}/{dr} {same}")
print(f"mean tok/s {sum(rates)/len(rates):.2f}")
