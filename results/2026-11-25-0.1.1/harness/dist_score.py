# SPDX-License-Identifier: AGPL-3.0-only
"""Score teacher-forced distributions against a reference engine.
usage: dist_score.py REF.jsonl CANDIDATE.jsonl [...]
Per passage, positions where both engines report the same token sequence are
compared: perplexity of the passage (from each engine's own token logprobs),
top-1 agreement with the reference, and total variation over the reference's
top five tokens plus one bin for everything else."""
import json, math, sys


def load(path):
    return {d["passage"]: d for d in map(json.loads, open(path))}


ref = load(sys.argv[1])
report = {}
for path in [sys.argv[1]] + sys.argv[2:]:
    run = load(path)
    nll = n = agree = 0
    tv = []
    for name, r in ref.items():
        c = run[name]
        # Echo returns the prompt and then the one generated token; score the prompt.
        if c["tokens"][:-1] != r["tokens"][:-1]:
            raise SystemExit(f"{path}: {name} tokenizes differently")
        for i in range(1, len(r["tokens"]) - 1):
            if c["token_logprobs"][i] is None or not r["top_logprobs"][i] or not c["top_logprobs"][i]:
                continue
            nll -= c["token_logprobs"][i]
            n += 1
            rt, ct = r["top_logprobs"][i], c["top_logprobs"][i]
            agree += max(rt, key=rt.get) == max(ct, key=ct.get)
            pr = {t: math.exp(v) for t, v in rt.items()}
            pc = {t: math.exp(ct[t]) if t in ct else 0.0 for t in rt}
            rest_r = max(0.0, 1 - sum(pr.values()))
            rest_c = max(0.0, 1 - sum(pc.values()))
            tv.append(0.5 * (sum(abs(pr[t] - pc[t]) for t in rt) + abs(rest_r - rest_c)))
    report[path] = dict(positions=n, perplexity=round(math.exp(nll / n), 4), top1_agree_with_ref=round(agree / n, 4),
                        mean_tv_vs_ref=round(sum(tv) / len(tv), 4))
print(json.dumps(report, indent=1))
