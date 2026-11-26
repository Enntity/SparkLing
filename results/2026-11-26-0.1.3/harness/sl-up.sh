#!/usr/bin/env bash
# usage: sl-up.sh MODEL MODE DRAFTER MODEL_DIR [KEY=VAL ...]
# Serve with SparkLing serve.py's argv and env (claude-sl at the release tag) from IMAGE (default 0.1.1).
# BIN=claude-bin/<name> mounts a dev engine binary over the image's; extra ATLAS_* KEY=VAL go straight to the engine.
set -euo pipefail
cd ~/models/sparkling
model=$1 mode=$2 drafter=$3 dir=$4; shift 4
name=claude-product
docker rm -f "$name" >/dev/null 2>&1 || true
launch=(); extra=()
for kv in "$@"; do [[ $kv == ATLAS_* || $kv == CUDA_* ]] && extra+=(-e "$kv") || launch+=("$kv"); done
python3 claude-runs/product_launch.py "$model" "$mode" "$drafter" "${launch[@]}" > claude-runs/product-launch.json
mapfile -t args < <(python3 -c 'import json; [print(a) for a in json.load(open("claude-runs/product-launch.json"))["argv"]]')
envs=()
while IFS= read -r kv; do envs+=(-e "$kv"); done < <(python3 -c 'import json; [print(k + "=" + v) for k, v in json.load(open("claude-runs/product-launch.json"))["env"].items()]')
mount=(); [[ -n ${BIN:-} ]] && mount=(-v "$PWD/$BIN:/usr/local/bin/spark:ro")
docker run -d --name "$name" --label io.enntity.owner=SparkLing --gpus device=0 --ipc host --network host --memory 114g \
  -v "$PWD/$dir:/model:ro" "${mount[@]}" -v "$PWD/cuda-cache:/atlas-cuda-cache" \
  -v /run/lock/sparkglm:/run/lock/sparkglm "${envs[@]}" "${extra[@]}" --entrypoint /usr/local/bin/spark \
  "${IMAGE:-ghcr.io/enntity/atlas-sparkling:0.1.1}" "${args[@]}" >/dev/null
for i in $(seq 1 900); do
  curl -fsS --max-time 2 localhost:8897/health >/dev/null 2>&1 && { echo "up after $((i * 2)) s"; exit 0; }
  if [[ $(docker inspect -f '{{.State.Running}}' "$name") != true ]]; then
    docker logs --tail 15 "$name" 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | cut -c 1-300; exit 1
  fi
  sleep 2
done
exit 1
