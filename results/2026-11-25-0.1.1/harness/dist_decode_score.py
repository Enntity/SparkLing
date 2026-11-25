# SPDX-License-Identifier: AGPL-3.0-only
"""usage: dist_decode_score.py REF.jsonl CANDIDATE.jsonl [...]: top-1 agreement and
total variation (reference top five plus a rest bin) at each generated position
while candidate and reference have produced the same tokens so far."""
import json, math, sys

load = lambda p: {d["passage"]: d for d in map(json.loads, open(p))}
ref = load(sys.argv[1])
report = {}
for path in sys.argv[2:]:
    run = load(path)
    tv, agree, shared = [], 0, 0
    for name, r in ref.items():
        c = run[name]
        for i, (rt, ct) in enumerate(zip(r["top_logprobs"], c["top_logprobs"])):
            if r["tokens"][:i] != c["tokens"][:i]:
                break
            if not rt or not ct:  # Atlas reports no candidates for the first generated token
                continue
            shared += 1
            agree += max(rt, key=rt.get) == max(ct, key=ct.get)
            pr = {t: math.exp(v) for t, v in rt.items()}
            pc = {t: math.exp(ct[t]) if t in ct else 0.0 for t in rt}
            tv.append(0.5 * (sum(abs(pr[t] - pc[t]) for t in rt)
                             + abs(max(0.0, 1 - sum(pr.values())) - max(0.0, 1 - sum(pc.values())))))
    mean = sum(tv) / len(tv)
    se = (sum((x - mean) ** 2 for x in tv) / (len(tv) - 1) / len(tv)) ** 0.5
    report[path] = dict(shared_positions=shared, top1_agree_with_ref=round(agree / shared, 4),
                        top1_se=round((agree / shared * (1 - agree / shared) / shared) ** 0.5, 4),
                        mean_tv_vs_ref=round(mean, 4), tv_se=round(se, 4))
print(json.dumps(report, indent=1))
