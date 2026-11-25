#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# usage: rel11.sh LABEL IMAGE MODEL MODE   SparkLing's start.sh (image profiles), then the probes
set -uo pipefail
cd ~/models/sparkling/claude-sl
label=$1; image=$2; model=$3; mode=$4
out=~/models/sparkling/claude-runs/rel11-$label; mkdir -p "$out"
name=claude-release
served=$([[ $model == sante-air-vl ]] && echo lingsante-air-vl || echo ling-3.2-air-atlas)
export CONTAINER_NAME=$name MODEL_ROOT=~/models/sparkling PULL=0 IMAGE=$image
export PREFIX_CACHE_DIR=~/models/sparkling/claude-pc PREFIX_CACHE_GB=16
docker rm -f "$name" >/dev/null 2>&1
trap 'docker logs "$name" > "$out/server.log" 2>&1; docker rm -f "$name" >/dev/null 2>&1' EXIT
t0=$(date +%s); ./start.sh --model "$model" --mode "$mode" up > "$out/start.log" 2>&1 || { tail -20 "$out/start.log"; exit 1; }
echo "start: $(( $(date +%s) - t0 )) s; $(tail -1 "$out/start.log" | cut -c1-160)"
cd ~/models/sparkling
docker logs $name 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -a -E "max KV tokens|KV cache: [0-9]+ blocks" | cut -c 60-300
python3 claude-runs/probe.py 8897 256 "$served" > "$out/probe.jsonl"
python3 claude-runs/summary.py "$out/probe.jsonl" | tail -1
python3 claude-runs/conc.py 8897 "$served" 256 1 2 4 8 | tee "$out/conc.jsonl"
python3 claude-runs/video_probe.py 8897 "$served" > "$out/media.jsonl"; python3 -c 'import json,sys; [print(d["case"], d.get("passed"), (d.get("answer") or d.get("error",""))[:80].replace("\n"," ")) for d in map(json.loads, open(sys.argv[1]))]' "$out/media.jsonl"
SERVED_MODEL_NAME=$served python3 claude-sl/bench/task_probe.py 8897 > "$out/task.json" 2>&1; tail -1 "$out/task.json" | cut -c1-80
