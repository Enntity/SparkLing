#!/usr/bin/env bash
# usage: pf-ab.sh LABEL BIN|release   0.1.3 release image (start.sh launch), optional engine binary mounted over
# /usr/local/bin/spark: greedy probes, long-prompt identity, cold prefill 8K-128K -> pf-ab/LABEL-*.jsonl
set -euo pipefail
cd ~/models/sparkling/claude-runs
label=$1; bin=$2; name=claude-pfab; out=$PWD/pf-ab; mkdir -p "$out"
mount=(); [[ $bin != release ]] && mount=(-v "$HOME/models/sparkling/$bin:/usr/local/bin/spark:ro")
docker rm -f $name >/dev/null 2>&1 || true
docker run -d --name $name --memory 114g --gpus device=0 --ipc host --network host --label io.enntity.owner=SparkLing --label io.enntity.job=bench \
  --mount type=bind,src=$HOME/models/sparkling/3a78e58506316b5b9b7d06037910c3f4abdd291f,dst=/model,readonly "${mount[@]}" \
  -e MODEL_PATH=/model -e SERVED_MODEL_NAME=ling-3.2-air-atlas -e SPARKLING_MODEL=ling-3.2-air -e SPARKLING_DRAFTER=mtp -e SPARKLING_QUANT=publisher \
  -e SPARKLING_MODE=spark -e SPARKLING_DECODE_PRECISION=nvfp4 -e SPARKLING_PREFILL_PRECISION=nvfp4 -e SPARKLING_PROFILE=default \
  -e SPARKLING_GPU_MEMORY_UTILIZATION= -e SPARKLING_PREFIX_CACHE_GB=0 -e SPARKLING_DISPLAY_CARVEOUT= -e SPARKLING_TOOL_GUARD=stream \
  -e SPARKLING_TOOL_GUARD_MAX_BYTES=1048576 ghcr.io/enntity/atlas-sparkling:7a1f9d22997d >/dev/null
trap "docker logs $name > $out/$label-server.log 2>&1; docker rm -f $name >/dev/null" EXIT
for i in $(seq 1 300); do curl -fsS --max-time 2 localhost:8897/health >/dev/null 2>&1 && break; sleep 2; done
python3 prefill-one.py 4096 0 >/dev/null
[[ -n ${ONLY:-} ]] || python3 probe.py 8897 256 > "$out/$label-probe.jsonl"
[[ ${ONLY:-} == prefill ]] || python3 long_id.py ${LONG:-20000 50000} > "$out/$label-long.jsonl"
[[ ${ONLY:-} == long ]] || for d in 8192 32768 65536 131072; do python3 prefill-one.py $d 7; done | tee "$out/$label-prefill.jsonl"
