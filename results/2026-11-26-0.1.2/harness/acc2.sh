#!/usr/bin/env bash
# usage: [BIN=...] acc2.sh LABEL MODEL DRAFTER DIR SERVED [REF_LABEL] [ENGINE_ENV...]
# One model in Spark mode, the eight probes, per-prompt first-draft acceptance; text compared with REF_LABEL's run.
set -uo pipefail
cd ~/models/sparkling
label=$1 model=$2 drafter=$3 dir=$4 served=$5 ref=${6:-}; shift 5; [[ $# -gt 0 ]] && shift
claude-runs/sl-up.sh "$model" spark "$drafter" "$dir" ATLAS_MTP_ACCEPT_DEBUG=1 "$@" || exit 1
python3 claude-runs/probe.py 8897 256 "$served" > claude-runs/acc-$label.jsonl
docker logs claude-product 2>&1 | sed "s/\x1b\[[0-9;]*m//g" > claude-runs/acc-$label.log
python3 - "$label" "$ref" <<'PY'
import json, re, sys
label, ref = sys.argv[1], sys.argv[2]
rows = [json.loads(l) for l in open(f"claude-runs/acc-{label}.jsonl")]
p1 = re.findall(r"mtp_accept_debug: Done: \d+ tokens.*?p1=([0-9.]+)", open(f"claude-runs/acc-{label}.log").read())
refs = {json.loads(l)["probe"]: json.loads(l)["text"] for l in open(f"claude-runs/acc-{ref}.jsonl")} if ref else {}
for r, p in zip(rows, p1):
    same = refs.get(r["probe"]) == r["text"] if refs else "-"
    print(f'{r["probe"]:8} {r["tok_s"]:5.1f} tok/s  p1={p}  same_text={same}')
print(f'mean {sum(r["tok_s"] for r in rows) / len(rows):.1f} tok/s')
PY
