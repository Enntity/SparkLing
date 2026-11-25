#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# usage: prof.sh LABEL BINARY   drafted Ling (8K window) under an nsys session; profile one 256-token request
set -euo pipefail
cd ~/models/sparkling
label=$1 bin=$2 name=claude-prof
NS=/opt/nvidia/nsight-systems/2025.3.2
docker rm -f $name >/dev/null 2>&1 || true
mkdir -p claude-prof
docker run -d --name $name --label io.enntity.owner=SparkLing --gpus device=0 --ipc host --network host --memory 114g \
  -v "$PWD/3a78e58506316b5b9b7d06037910c3f4abdd291f:/model:ro" -v "$PWD/$bin:/usr/local/bin/spark:ro" -v "$PWD/cuda-cache:/atlas-cuda-cache" \
  -v $NS:$NS:ro -v "$PWD/claude-prof:/out" -e CUDA_CACHE_PATH=/atlas-cuda-cache \
  -e ATLAS_LING_NVFP4_DECODE=1 -e ATLAS_LING_W4A4_PREFILL=1 -e ATLAS_LING_EXPERT_UNION=tensor -e ATLAS_SKINNY_MMA=1 \
  -e ATLAS_BF16_GEMM_CUTLASS=1 -e ATLAS_MLA_PREFIX_SKIP=1 -e ATLAS_MARCONI_EXACT=1 -e ATLAS_EXACT_DIRECT=1 \
  -e ATLAS_MTP_DRAFTER_PREFILL=1 -e ATLAS_MTP_CATCHUP=1 -e ATLAS_MTP_MAX_SEQS=1 -e ATLAS_LING_MTP_QUANT_HEAD=1 -e ATLAS_SSM_DECODE_RING=0 \
  --entrypoint $NS/target-linux-sbsa-armv8/nsys ghcr.io/enntity/atlas-sparkling:ff9d6b0582ce \
  launch --trace=cuda --cuda-graph-trace=node --session-new=prof /usr/local/bin/spark serve --model-from-path=/model \
  --kernel-target=ling-3.2-air --kv-cache-dtype=bf16 --max-seq-len=8192 --max-prefill-tokens=8192 --max-num-seqs=8 --max-batch-size=8 \
  --gpu-memory-utilization=0.80 --enable-prefix-caching --no-tui --bind=127.0.0.1 --port=8897 --model-name=ling-3.2-air-atlas \
  --speculative --num-drafts=1 --mtp-quantization=bf16 >/dev/null
for i in $(seq 1 300); do curl -fsS --max-time 2 localhost:8897/health >/dev/null 2>&1 && break; sleep 2; done
python3 claude-runs/probe.py 8897 256 ling-3.2-air-atlas > /dev/null   # warm graphs on all eight prompts
docker exec $name $NS/target-linux-sbsa-armv8/nsys start --session=prof -o /out/$label --force-overwrite=true
python3 claude-runs/probe.py 8897 256 ling-3.2-air-atlas > claude-prof/$label-probe.jsonl
docker exec $name $NS/target-linux-sbsa-armv8/nsys stop --session=prof
sleep 5
python3 claude-runs/summary.py claude-prof/$label-probe.jsonl | tail -1
docker rm -f $name >/dev/null
