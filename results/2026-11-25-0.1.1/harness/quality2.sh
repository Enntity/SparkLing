#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# The BF16-absorption build (claude-bin/spark-latent): GSM8K-200 and decode distributions for Ling,
# GSM8K-200 and the BF16-teacher distribution check for Air-VL.
set -uo pipefail
cd ~/models/sparkling
D=3a78e58506316b5b9b7d06037910c3f4abdd291f
export IMAGE=ghcr.io/enntity/atlas-sparkling:ff9d6b0582ce
eval_one() {
  docker run --rm --network host -v $PWD/claude-runs:/runs -v $PWD/claude-hf:/root/.cache/huggingface python:3.12-slim \
    bash -c "pip install -q pyarrow huggingface_hub 2>/dev/null; python /runs/gsm8k_eval.py 8897 $2 200 /runs/gsm8k-$1.jsonl" 2>&1 | grep '{'
}
claude-runs/product-up.sh ling-3.2-air spark none $D >/dev/null
python3 claude-runs/dist_decode.py 8897 ling-3.2-air-atlas claude-runs/dd-bf.jsonl >/dev/null
docker rm -f claude-product >/dev/null
claude-runs/product-up.sh ling-3.2-air spark mtp $D >/dev/null
echo "ling-bf $(eval_one ling-bf ling-3.2-air-atlas)"
docker rm -f claude-product >/dev/null
claude-runs/product-up.sh sante-air-vl spark ling-mtp sante-nvfp4-rne-ling-mtp-3a78e5850631 SERVED_MODEL_NAME=lingsante-air-vl >/dev/null
echo "sante-bf $(eval_one sante-bf lingsante-air-vl)"
python3 claude-sl/bench/sante_distributions.py 8897 quality > claude-runs/sante-bf-quality.jsonl
docker rm -f claude-product >/dev/null
(cd claude-release && CONTAINER_NAME=claude-old MODEL_ROOT=$HOME/models/sparkling PULL=0 IMAGE=ghcr.io/enntity/atlas-sparkling:0.1.0 ./start.sh --model sante-air-vl up >/dev/null 2>&1)
python3 claude-sl/bench/sante_distributions.py 8897 quality > claude-runs/sante-010-quality.jsonl
docker rm -f claude-old >/dev/null
python3 claude-runs/dist_decode_score.py claude-runs/dd-vllm.jsonl claude-runs/dd-010.jsonl claude-runs/dd-011.jsonl claude-runs/dd-fix.jsonl claude-runs/dd-bf.jsonl
mkdir -p claude-runs/sante-score && cp claude-sl/results/2026-11-24/air-vl-quant/bf16-*.jsonl claude-runs/sante-score/ && cp claude-runs/sante-bf-quality.jsonl claude-runs/sante-score/v011-quality.jsonl && cp claude-runs/sante-010-quality.jsonl claude-runs/sante-score/v010-quality.jsonl && cp claude-sl/results/2026-11-24/air-vl-quant/mlp4-quality.jsonl claude-runs/sante-score/
python3 claude-sl/bench/score_sante.py claude-runs/sante-score mlp4 v010 v011
