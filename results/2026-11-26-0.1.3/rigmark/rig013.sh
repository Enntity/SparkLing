#!/usr/bin/env bash
# RigMark 1.1.0 (commit 40fabca) for SparkLing 0.1.2 and the vLLM reference, one Spark, thinking off.
# usage: rig013r.sh [ling] [sante] [vllm-mtp3] [vllm]
set -u
R=~/qual-20261110/rigmark
OUT=~/models/sparkling/claude-runs/rig013r; mkdir -p "$OUT"
EB='{"chat_template_kwargs":{"enable_thinking":false}}'
rig() {  # label model comparison-id
  local label=$1 model=$2 cid=$3 m="$OUT/metadata-$1.json"
  cd "$R"
  ./rigmark run --base-url http://127.0.0.1:8897 --model "$model" --metadata "$m" --comparison-id "$cid" \
    --runs 2 --prefill-runs 2 --prefill-depths 8192,32768 --concurrency 1,2,4,8 --concurrency-runs 2 \
    --extra-body "$EB" --label "$label-code" --output "$OUT/$label-code.json" > "$OUT/$label.log" 2>&1
  ./rigmark run --base-url http://127.0.0.1:8897 --model "$model" --metadata "$m" --comparison-id "$cid" \
    --runs 2 --concurrency 1,4,8 --concurrency-runs 2 --concurrency-workload prose --skip-prefill \
    --extra-body "$EB" --label "$label-prose" --output "$OUT/$label-prose.json" >> "$OUT/$label.log" 2>&1
  echo "$label rigmark rc=$?"
}
wait_up() { for i in $(seq 1 600); do curl -fsS --max-time 2 localhost:8897/health >/dev/null 2>&1 && return 0; sleep 2; done; return 1; }
for job in "$@"; do
  case $job in
    ling|sante)
      model=$([[ $job == sante ]] && echo lingsante-3.1-air-vl || echo ling-3.2-air)
      served=$([[ $job == sante ]] && echo lingsante-3.1-air-vl-atlas || echo ling-3.2-air-atlas)
      cd ~/models/sparkling/claude-rel013
      export CONTAINER_NAME=claude-release MODEL_ROOT=~/models/sparkling PULL=0 IMAGE=ghcr.io/enntity/atlas-sparkling:7a1f9d22997d
      export PREFIX_CACHE_DIR=~/models/sparkling/claude-pc PREFIX_CACHE_GB=16
      ./start.sh --model "$model" up > "$OUT/sparkling-$job.start.log" 2>&1 || { echo "START FAILED $job"; tail -5 "$OUT/sparkling-$job.start.log"; continue; }
      rig "sparkling-$job" "$served" "ling-3.2-air"
      docker logs claude-release > "$OUT/sparkling-$job.server.log" 2>&1
      ./start.sh stop >/dev/null 2>&1; docker rm -f claude-release >/dev/null 2>&1 ;;
    vllm-mtp3|vllm)
      draft=$([[ $job == vllm-mtp3 ]] && echo 3 || echo 0)
      cd ~/models/sparkling
      cmd=$(python3 claude-runs/reference/serve.py --mode a16 --model-dir ~/models/sparkling/3a78e58506316b5b9b7d06037910c3f4abdd291f \
        --draft-tokens $draft --max-model-len 40960 --served-model-name ling-3.2-air-atlas --print-command | tail -1)
      cmd=${cmd/docker run --rm/docker run -d --name claude-vllm}
      docker rm -f claude-vllm >/dev/null 2>&1; echo "$cmd" > "$OUT/$job.cmd"
      eval "$cmd" >/dev/null || { echo "VLLM START FAILED $job"; continue; }
      wait_up || { echo "VLLM NOT UP $job"; docker logs --tail 30 claude-vllm; docker rm -f claude-vllm >/dev/null; continue; }
      rig "$job" ling-3.2-air-atlas "ling-3.2-air"
      docker logs claude-vllm > "$OUT/$job.server.log" 2>&1; docker rm -f claude-vllm >/dev/null 2>&1 ;;
  esac
done
echo RIG-DONE
