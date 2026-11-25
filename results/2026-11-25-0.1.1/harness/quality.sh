#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# GSM8K-200 on 0.1.0 (its own image and launcher) and on the 0.1.1 build, both models.
set -uo pipefail
cd ~/models/sparkling
eval_one() {  # LABEL SERVED
  docker run --rm --network host -v $PWD/claude-runs:/runs -v $PWD/claude-hf:/root/.cache/huggingface python:3.12-slim \
    bash -c "pip install -q pyarrow huggingface_hub 2>/dev/null; python /runs/gsm8k_eval.py 8897 $2 200 /runs/gsm8k-$1.jsonl" 2>&1 | grep '{'
}
old() {  # MODEL SERVED LABEL
  (cd claude-release && CONTAINER_NAME=claude-old MODEL_ROOT=$HOME/models/sparkling PULL=0 IMAGE=ghcr.io/enntity/atlas-sparkling:0.1.0 ./start.sh --model $1 up >/dev/null 2>&1) || { echo "start failed $3"; return; }
  echo "$3 $(eval_one $3 $2)"; docker rm -f claude-old >/dev/null
}
new() {  # MODEL DRAFTER DIR SERVED LABEL
  IMAGE=ghcr.io/enntity/atlas-sparkling:ff9d6b0582ce claude-runs/product-up.sh $1 spark $2 $3 >/dev/null || { echo "start failed $5"; return; }
  echo "$5 $(eval_one $5 $4)"; docker rm -f claude-product >/dev/null
}
old ling-3.2-air ling-3.2-air-atlas ling-010
new ling-3.2-air mtp 3a78e58506316b5b9b7d06037910c3f4abdd291f ling-3.2-air-atlas ling-011
old sante-air-vl lingsante-air-vl sante-010
new sante-air-vl ling-mtp sante-nvfp4-rne-ling-mtp-3a78e5850631 lingsante-air-vl sante-011
