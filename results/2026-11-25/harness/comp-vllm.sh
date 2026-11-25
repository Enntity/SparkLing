#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# usage: comp-vllm.sh LABEL DRAFT_TOKENS   (vLLM pinned A16 reference, same probes as Atlas)
set -uo pipefail
cd ~/models/sparkling
label=$1; draft=$2; name=claude-vllm-$label
cmd=$(python3 claude-runs/reference/serve.py --mode a16 --model-dir ~/models/sparkling/3a78e58506316b5b9b7d06037910c3f4abdd291f \
  --draft-tokens "$draft" --max-model-len 8192 --served-model-name ling-3.2-air-atlas --print-command | tail -1)
cmd=${cmd/docker run --rm/docker run -d --name $name}
docker rm -f "$name" >/dev/null 2>&1 || true
trap 'docker logs --tail 300 "$name" > claude-runs/$label.log 2>&1; docker rm -f "$name" >/dev/null 2>&1 || true' EXIT
eval "$cmd" >/dev/null
for i in $(seq 1 600); do
  curl -fsS --max-time 2 localhost:8897/health >/dev/null 2>&1 && break
  [[ $(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null) == true ]] || { docker logs --tail 30 "$name"; exit 1; }
  sleep 2
done
python3 claude-runs/probe.py 8897 256 > claude-runs/$label.jsonl
python3 claude-runs/summary.py claude-runs/$label.jsonl claude-runs/b6-off.jsonl | tail -9
python3 claude-runs/conc.py 8897 ling-3.2-air-atlas 256 1 2 4 8 | tee claude-runs/$label-conc.jsonl
