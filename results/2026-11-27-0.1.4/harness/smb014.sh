#!/usr/bin/env bash
# SparkModelBench for SparkLing 0.1.4 and the vLLM reference, one Spark.
# usage: smb.sh up ling|sante|vllm
#        [SMB=checkout] smb.sh bench ling|sante|vllm EFFORT [lanes...]
#        smb.sh down ling|sante|vllm   save the server log and remove the container
set -u
S=${SMB:-$HOME/models/sparkling/claude-rel014/bench/sparkmodelbench}
OUT=~/models/sparkling/claude-runs/smb014; mkdir -p "$OUT"
act=$1; job=$2
model=$([[ $job == sante ]] && echo lingsante-3.1-air-vl || echo ling-3.2-air)
served=$([[ $job == sante ]] && echo lingsante-3.1-air-vl-atlas || echo ling-3.2-air-atlas)
name=$([[ $job == vllm ]] && echo claude-vllm || echo claude-release)
wait_up() { for _ in $(seq 1 900); do curl -fsS --max-time 2 localhost:8897/health >/dev/null 2>&1 && return 0; sleep 2; done; return 1; }
case $act in
  up)
    docker rm -f claude-release claude-vllm >/dev/null 2>&1
    if [[ $job == vllm ]]; then
      # 0.1.2's reference command (results/2026-11-26-0.1.2/rigmark/vllm-mtp3.cmd), window raised to Ling's 262,144.
      docker run -d --name claude-vllm --platform linux/arm64 --gpus device=0 --label io.enntity.owner=SparkLing --label io.enntity.job=reference \
        --ipc=host --shm-size=32g --publish 127.0.0.1:8897:8000 \
        --volume ~/models/sparkling/3a78e58506316b5b9b7d06037910c3f4abdd291f:/models/model:ro --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 \
        24541db891c5 --model /models/model --trust-remote-code --tensor-parallel-size 1 --host 0.0.0.0 --port 8000 \
        --served-model-name ling-3.2-air-atlas --max-model-len 262144 --max-num-seqs 8 --gpu-memory-utilization 0.92 \
        --reasoning-parser ling3 --enable-auto-tool-choice --tool-call-parser ling3 --enable-prefix-caching --mamba-cache-mode align \
        --speculative-config '{"method":"mtp","num_speculative_tokens":3}' > "$OUT/vllm.cid"
      wait_up || { echo "VLLM START FAILED"; docker logs --tail 30 claude-vllm; exit 1; }
      echo vllm up
    else
      cd ~/models/sparkling/claude-rel014
      export CONTAINER_NAME=claude-release MODEL_ROOT=~/models/sparkling PULL=0 IMAGE=ghcr.io/enntity/atlas-sparkling:c523fbc3852c
      export PREFIX_CACHE_DIR=~/models/sparkling/claude-pc
      ./start.sh --model "$model" up > "$OUT/sparkling-$job.start.log" 2>&1 || { echo "START FAILED"; tail -5 "$OUT/sparkling-$job.start.log"; exit 1; }
      tail -1 "$OUT/sparkling-$job.start.log" | cut -c1-200
    fi ;;
  bench)
    effort=$3; shift 3
    lanes=(); tag=full; [[ $# -gt 0 ]] && { lanes=(--lanes "$@"); tag=$(IFS=-; echo "$*"); }
    label=$([[ $job == vllm ]] && echo vllm-mtp3 || echo "sparkling-$job")
    cd "$S"
    python3 run.py --base-url http://127.0.0.1:8897 --model "$served" --metadata "$OUT/metadata-$job.json" \
      --comparison-id sparkling-0.1.4 --effort "$effort" --out "$OUT/$label-$tag-$(date -u +%m%dT%H%M)" "${lanes[@]}" ;;
  down)
    label=$([[ $job == vllm ]] && echo vllm-mtp3 || echo "sparkling-$job")
    docker logs "$name" > "$OUT/$label.server.log" 2>&1
    docker rm -f "$name" >/dev/null 2>&1; echo down ;;
esac
