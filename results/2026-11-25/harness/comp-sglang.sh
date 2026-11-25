#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# usage: comp-sglang.sh LABEL [extra sglang args]  (publisher SGLang image, Primitive A16, TP=1)
set -uo pipefail
cd ~/models/sparkling
label=$1; shift; name=claude-sglang-$label
M=~/models/sparkling/3a78e58506316b5b9b7d06037910c3f4abdd291f
docker rm -f "$name" >/dev/null 2>&1 || true
trap 'docker logs --tail 300 "$name" > claude-runs/$label.log 2>&1; docker rm -f "$name" >/dev/null 2>&1 || true' EXIT
docker run -d --name "$name" --gpus device=0 --network host --ipc host --shm-size 32g -v "$M:/model:ro" \
  -e HF_HUB_OFFLINE=1 -e OMP_NUM_THREADS=1 --entrypoint python3 \
  lmsysorg/sglang@sha256:7d0d06441b8220e537ae6bb287294cab26f3c877ded3bc6803a148c294b2cce6 \
  -m sglang.launch_server --model-path /model --served-model-name ling-3.2-air-atlas --host 127.0.0.1 --port 8897 \
  --tp-size 1 --trust-remote-code --context-length 8192 --mem-fraction-static ${MEM:-0.85} --max-running-requests 8 \
  --reasoning-parser ling3 --tool-call-parser ling3 "$@" >/dev/null
for i in $(seq 1 900); do
  curl -fsS --max-time 2 localhost:8897/health >/dev/null 2>&1 && break
  [[ $(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null) == true ]] || { docker logs --tail 40 "$name"; exit 1; }
  sleep 2
done
python3 claude-runs/probe.py 8897 256 > claude-runs/$label.jsonl
python3 claude-runs/summary.py claude-runs/$label.jsonl claude-runs/b6-off.jsonl | tail -9
python3 claude-runs/conc.py 8897 ling-3.2-air-atlas 256 1 2 4 8 | tee claude-runs/$label-conc.jsonl
