#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# usage: serve-up.sh NAME BINARY [ENV=VAL ...] -- [extra serve args]; leaves the server up on :8897
set -euo pipefail
cd ~/models/sparkling
name=claude-up-$1; bin=$2; shift 2
envs=(); while [[ $# -gt 0 && $1 != -- ]]; do envs+=(-e "$1"); shift; done; [[ ${1:-} == -- ]] && shift
docker rm -f "$name" >/dev/null 2>&1 || true
docker run -d --name "$name" --label io.enntity.owner=SparkLing --gpus device=0 --ipc host --network host --memory 114g \
  -v "$PWD/${MODEL_DIR}:/model:ro" -v "$PWD/$bin:/usr/local/bin/spark:ro" -v "$PWD/cuda-cache:/atlas-cuda-cache" \
  -e CUDA_CACHE_PATH=/atlas-cuda-cache -e ATLAS_MAX_BODY_BYTES=268435456 \
  -e ATLAS_LING_NVFP4_DECODE=1 -e ATLAS_LING_W4A4_PREFILL=1 -e ATLAS_LING_EXPERT_UNION=tensor -e ATLAS_SKINNY_MMA=1 -e ATLAS_BF16_GEMM_CUTLASS=1 -e ATLAS_MLA_PREFIX_SKIP=1 -e ATLAS_MARCONI_EXACT=1 -e ATLAS_EXACT_DIRECT=1 \
  "${envs[@]}" --entrypoint /usr/local/bin/spark ghcr.io/enntity/atlas-sparkling:0.1.0 serve --model-from-path=/model --kernel-target=ling-3.2-air \
  --kv-cache-dtype=bf16 --max-seq-len=${SEQ:-262144} --max-prefill-tokens=8192 --max-num-seqs=8 --max-batch-size=8 --gpu-memory-utilization=${UTIL:-0.80} \
  --oom-guard-mb=4096 --enable-prefix-caching --video-allow-ffmpeg --request-timeout=3600 --no-tui --bind=127.0.0.1 --port=8897 --model-name=${NAME:-ling-3.2-air-atlas} "$@" >/dev/null
for i in $(seq 1 300); do
  curl -fsS --max-time 2 localhost:8897/health >/dev/null 2>&1 && { echo "up after $((i*2)) s"; exit 0; }
  [[ $(docker inspect -f "{{.State.Running}}" "$name") == true ]] || { docker logs --tail 30 "$name"; exit 1; }
  sleep 2
done
exit 1
