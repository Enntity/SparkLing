#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# Teacher-forced Ling distributions: vLLM reference (same NVFP4A16 weights), 0.1.0, 0.1.1.
set -uo pipefail
cd ~/models/sparkling
D=3a78e58506316b5b9b7d06037910c3f4abdd291f
cmd=$(python3 claude-runs/reference/serve.py --mode a16 --model-dir ~/models/sparkling/$D --draft-tokens 0 \
  --max-model-len 8192 --served-model-name ling-3.2-air-atlas --print-command | tail -1)
cmd=${cmd/docker run --rm/docker run -d --name claude-vllm-dist}
eval "$cmd" >/dev/null
for i in $(seq 1 600); do curl -fsS --max-time 2 localhost:8897/health >/dev/null 2>&1 && break; sleep 2; done
python3 claude-runs/dist_ling.py 8897 ling-3.2-air-atlas claude-runs/dist-vllm.jsonl
docker rm -f claude-vllm-dist >/dev/null
(cd claude-release && CONTAINER_NAME=claude-old MODEL_ROOT=$HOME/models/sparkling PULL=0 IMAGE=ghcr.io/enntity/atlas-sparkling:0.1.0 ./start.sh up >/dev/null 2>&1)
python3 claude-runs/dist_ling.py 8897 ling-3.2-air-atlas claude-runs/dist-010.jsonl
docker rm -f claude-old >/dev/null
IMAGE=ghcr.io/enntity/atlas-sparkling:ff9d6b0582ce claude-runs/product-up.sh ling-3.2-air spark mtp $D >/dev/null
python3 claude-runs/dist_ling.py 8897 ling-3.2-air-atlas claude-runs/dist-011.jsonl
docker rm -f claude-product >/dev/null
python3 claude-runs/dist_score.py claude-runs/dist-vllm.jsonl claude-runs/dist-010.jsonl claude-runs/dist-011.jsonl
