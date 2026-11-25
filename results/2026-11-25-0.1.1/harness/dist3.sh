#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# Decode-path distributions over ~220 contexts: vLLM, 0.1.0, NVFP4 absorption, BF16 absorption. Plain decode.
set -uo pipefail
cd ~/models/sparkling
D=3a78e58506316b5b9b7d06037910c3f4abdd291f
Q=claude-runs/gsm8k-questions.json
docker run --rm -v $PWD/claude-runs:/runs -v $PWD/claude-hf:/root/.cache/huggingface python:3.12-slim bash -c \
  "pip install -q pyarrow huggingface_hub 2>/dev/null; python -c \"import json,pyarrow.parquet as pq; from huggingface_hub import hf_hub_download as d; p=d('openai/gsm8k','main/test-00000-of-00001.parquet',repo_type='dataset',revision='e53f048856ff4f594e959d75785d2c2d37b678ee'); json.dump([r['question'] for r in pq.read_table(p).to_pylist()[200:300]], open('/runs/gsm8k-questions.json','w'))\"" >/dev/null 2>&1
cmd=$(python3 claude-runs/reference/serve.py --mode a16 --model-dir ~/models/sparkling/$D --draft-tokens 0 \
  --max-model-len 8192 --served-model-name ling-3.2-air-atlas --print-command | tail -1)
cmd=${cmd/docker run --rm/docker run -d --name claude-vllm-dist}
eval "$cmd" >/dev/null
for i in $(seq 1 600); do curl -fsS --max-time 2 localhost:8897/health >/dev/null 2>&1 && break; sleep 2; done
python3 claude-runs/dist_decode2.py 8897 ling-3.2-air-atlas $Q claude-runs/de-vllm.jsonl
docker rm -f claude-vllm-dist >/dev/null
(cd claude-release && CONTAINER_NAME=claude-old MODEL_ROOT=$HOME/models/sparkling PULL=0 IMAGE=ghcr.io/enntity/atlas-sparkling:0.1.0 DRAFTER=none ./start.sh up >/dev/null 2>&1)
python3 claude-runs/dist_decode2.py 8897 ling-3.2-air-atlas $Q claude-runs/de-010.jsonl
docker rm -f claude-old >/dev/null
for v in fix bf; do
  cp claude-bin/spark-$v claude-bin/spark-latent
  IMAGE=ghcr.io/enntity/atlas-sparkling:ff9d6b0582ce claude-runs/product-up.sh ling-3.2-air spark none $D >/dev/null
  python3 claude-runs/dist_decode2.py 8897 ling-3.2-air-atlas $Q claude-runs/de-$v.jsonl
  docker rm -f claude-product >/dev/null
done
python3 claude-runs/dist_decode_score.py claude-runs/de-vllm.jsonl claude-runs/de-010.jsonl claude-runs/de-fix.jsonl claude-runs/de-bf.jsonl
python3 claude-runs/dist_decode_score.py claude-runs/de-010.jsonl claude-runs/de-fix.jsonl claude-runs/de-bf.jsonl
