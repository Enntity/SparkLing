#!/usr/bin/env bash
# usage: [DRAFTER=none] [FULL=1] rel12.sh LABEL IMAGE MODEL MODE
# SparkLing 0.1.4 start.sh (claude-rel014 checkout) with IMAGE, then the probes.
# Always: the eight-prompt probe, and with drafting the counting-acceptance check.
# FULL=1 adds concurrency, media and the task probe.
set -uo pipefail
cd ~/models/sparkling/claude-rel014
label=$1; image=$2; model=$3; mode=$4
out=~/models/sparkling/claude-runs/rel014-$label; mkdir -p "$out"
name=claude-release
served=$([[ $model == sante-air-vl ]] && echo lingsante-3.1-air-vl-atlas || echo ling-3.2-air-atlas)
export CONTAINER_NAME=$name MODEL_ROOT=~/models/sparkling PULL=0 IMAGE=$image
export PREFIX_CACHE_DIR=~/models/sparkling/claude-pc PREFIX_CACHE_GB=16
docker rm -f "$name" >/dev/null 2>&1
trap 'docker logs "$name" > "$out/server.log" 2>&1; docker rm -f "$name" >/dev/null 2>&1' EXIT
t0=$(date +%s); ./start.sh --model "$model" --mode "$mode" up > "$out/start.log" 2>&1 || { tail -20 "$out/start.log"; exit 1; }
echo "start: $(( $(date +%s) - t0 )) s; $(tail -1 "$out/start.log" | cut -c1-160)"
cd ~/models/sparkling
docker logs $name 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -a -E "max KV tokens" | cut -c 60-300
python3 claude-runs/probe.py 8897 256 "$served" > "$out/probe.jsonl"
python3 - "$out/probe.jsonl" <<'PY'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
for r in rows:
    s = r.get("spec", {}); a = sum(v for k, v in s.items() if 'outcome="accept"' in k); j = sum(v for k, v in s.items() if 'outcome="reject"' in k)
    print(f'{r["probe"]:8} {r["tok_s"]:5.1f} tok/s' + (f'  accept {a / (a + j):.3f}' if a + j else ''))
print(f'mean {sum(r["tok_s"] for r in rows) / len(rows):.1f} tok/s')
PY
if [[ ${DRAFTER:-} != none ]]; then
  SERVED_MODEL_NAME=$served python3 claude-rel014/bench/draft_decode.py 8897 --min-count-accept 0.95 > "$out/draft-check.jsonl"; echo "draft check rc=$?"
fi
if [[ ${FULL:-0} == 1 ]]; then
  python3 claude-runs/conc.py 8897 "$served" 256 1 2 4 8 | tee "$out/conc.jsonl"
  python3 claude-runs/video_probe.py 8897 "$served" > "$out/media.jsonl"; python3 -c 'import json,sys; [print(d["case"], d.get("passed"), (d.get("answer") or d.get("error",""))[:80].replace("\n"," ")) for d in map(json.loads, open(sys.argv[1]))]' "$out/media.jsonl"
  SERVED_MODEL_NAME=$served python3 claude-rel014/bench/task_probe.py 8897 > "$out/task.json" 2>&1; tail -1 "$out/task.json" | cut -c1-80
fi
