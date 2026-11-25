#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# usage: comp-llama.sh LABEL [extra llama-server args]  (bartowski Q4_K_M, all layers on GPU)
set -uo pipefail
cd ~/models/sparkling
label=$1; shift; name=claude-llama-$label
L=${LLAMA_DIR:-$HOME/llama-cpp-ling}
docker rm -f "$name" >/dev/null 2>&1 || true
trap 'docker logs --tail 300 "$name" > claude-runs/$label.log 2>&1; docker rm -f "$name" >/dev/null 2>&1 || true' EXIT
docker run -d --name "$name" --gpus device=0 --ipc host --network host --memory 114g -v "$L:$L:ro" -e LD_LIBRARY_PATH=$L/llama.cpp/build/bin \
  --entrypoint $L/llama.cpp/build/bin/llama-server atlas-release-builder:1.93.1 \
  -m $L/gguf/Ling-3.2-air-Q4_K_M/Ling-3.2-air-Q4_K_M-00001-of-00003.gguf -a ling-3.2-air-atlas \
  -ngl 999 -c 32768 -np 8 --flash-attn on --jinja --host 127.0.0.1 --port 8897 "$@" >/dev/null
for i in $(seq 1 600); do
  curl -fsS --max-time 2 localhost:8897/health >/dev/null 2>&1 && break
  [[ $(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null) == true ]] || { docker logs --tail 30 "$name"; exit 1; }
  sleep 2
done
python3 claude-runs/probe.py 8897 256 > claude-runs/$label.jsonl
python3 claude-runs/summary.py claude-runs/$label.jsonl claude-runs/b6-off.jsonl | tail -9
python3 claude-runs/conc.py 8897 ling-3.2-air-atlas 256 1 2 4 8 | tee claude-runs/$label-conc.jsonl
