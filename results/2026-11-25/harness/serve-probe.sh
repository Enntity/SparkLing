#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# usage: serve-probe.sh LABEL BINARY MAXTOK [ENV=VAL ...] -- [extra serve args]
set -euo pipefail
cd ~/models/sparkling
label=$1; bin=$2; ntok=$3; shift 3
envs=(); while [[ $# -gt 0 && $1 != -- ]]; do envs+=(-e "$1"); shift; done; [[ ${1:-} == -- ]] && shift
out=claude-runs/$label.jsonl; name=claude-probe-$label
docker rm -f "$name" >/dev/null 2>&1 || true
finish() { docker logs --tail 400 "$name" > "claude-runs/$label.log" 2>&1 || true; docker rm -f "$name" >/dev/null 2>&1 || true; }
trap finish EXIT
docker run -d --name "$name" --label io.enntity.owner=SparkLing --gpus device=0 --ipc host --network host --memory 114g \
  -v "$PWD/${MODEL_DIR:-741cdea2fde8a8e5f1b1bda209bc0fef4d60a18a}:/model:ro" -v "$PWD/$bin:/usr/local/bin/spark:ro" -v "$PWD/cuda-cache:/atlas-cuda-cache" \
  -e CUDA_CACHE_PATH=/atlas-cuda-cache \
  ${BASE_ENV:--e ATLAS_LING_NVFP4_DECODE=1 -e ATLAS_LING_W4A4_PREFILL=1 -e ATLAS_LING_EXPERT_UNION=tensor -e ATLAS_SKINNY_MMA=1 -e ATLAS_BF16_GEMM_CUTLASS=1 -e ATLAS_MLA_PREFIX_SKIP=1 -e ATLAS_MARCONI_EXACT=1 -e ATLAS_EXACT_DIRECT=1} "${envs[@]}" \
  --entrypoint /usr/local/bin/spark ghcr.io/enntity/atlas-sparkling:959bd233e3d0 serve --model-from-path=/model --kernel-target=ling-3.2-air \
  --kv-cache-dtype=bf16 --max-seq-len=${SEQ:-8192} --max-prefill-tokens=8192 --max-num-seqs=8 --max-batch-size=8 --gpu-memory-utilization=${UTIL:-0.80} \
  --enable-prefix-caching --no-tui --bind=127.0.0.1 --port=8897 --model-name=${NAME:-ling-3.2-air-atlas} "$@" >/dev/null
for i in $(seq 1 300); do
  curl -fsS --max-time 2 localhost:8897/health >/dev/null 2>&1 && break
  [[ $(docker inspect -f '{{.State.Running}}' "$name") == true ]] || { docker logs --tail 30 "$name"; exit 1; }
  sleep 2
done
if [[ ${PROBE:-text} == conc ]]; then
  python3 claude-runs/conc.py 8897 ling-3.2-air-atlas "$ntok" ${LEVELS:-1 2 4 8} | tee "$out"
elif [[ ${PROBE:-text} == video ]]; then
  python3 claude-runs/video_probe.py 8897 > "$out" || true
  python3 -c 'import json,sys; [print(json.dumps({k:(v[:150] if isinstance(v,str) else v) for k,v in json.loads(l).items()})) for l in open(sys.argv[1])]' "$out"
else
  python3 claude-runs/probe.py 8897 "$ntok" ${NAME:-ling-3.2-air-atlas} > "$out"
  python3 claude-runs/summary.py "$out" ${REF:+claude-runs/$REF.jsonl}
fi
