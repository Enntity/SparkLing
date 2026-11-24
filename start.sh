#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ ${1:-} == --version ]]; then exec python3 install/serve.py --version; fi
if [[ -f .env ]]; then set -a; source ./.env; set +a; fi
mode=${MODE:-spark}
model_id=${MODEL:-ling-3.2-air}
quant=${QUANT:-}
while [[ ${1:-} == --mode || ${1:-} == --model || ${1:-} == --quant ]]; do
  [[ $# -ge 2 ]] || { echo "$1 requires a value" >&2; exit 2; }
  case "$1" in
    --mode) mode=$2 ;;
    --model) model_id=$2 ;;
    --quant) quant=$2 ;;
  esac
  shift 2
done
case "$model_id" in
  ling-3.2-air) manifest=install/checkpoint.json ;;
  sante-air-vl) manifest=install/checkpoint-sante-air-vl.json ;;
  *) echo "unknown SparkLing model: $model_id" >&2; exit 2 ;;
esac
if [[ -z $quant ]]; then
  quant=publisher
  if [[ $model_id == sante-air-vl && $mode == spark ]]; then quant=nvfp4; fi
fi
if [[ $quant != publisher && ( $quant != nvfp4 || $model_id != sante-air-vl || $mode != spark ) ]]; then
  echo '--quant nvfp4 requires --model sante-air-vl --mode spark' >&2
  exit 2
fi
cmd=${1:-up}
[[ $# -le 1 ]] || { echo 'expected one command' >&2; exit 2; }
name=${CONTAINER_NAME:-atlas-sparkling}
[[ $name =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]*$ ]] || { echo "invalid CONTAINER_NAME" >&2; exit 2; }
case "$cmd" in
  stop) exec docker stop "$name" ;;
  logs) exec docker logs -f --tail 100 "$name" ;;
  status) exec docker ps -a --filter "name=^/${name}$" ;;
  build) exec install/build.sh ;;
  --help|-h) echo './start.sh [--model ling-3.2-air|sante-air-vl] [--mode spark|strict] [--quant publisher|nvfp4] [download|verify|build|up|stop|logs|status]'; exit ;;
  up|verify|download) ;;
  *) echo "unknown command: $cmd" >&2; exit 2 ;;
esac
[[ $mode == strict || $mode == spark ]] || { echo 'MODE must be strict or spark' >&2; exit 2; }
drafter=${DRAFTER:-none}
case "$model_id/$quant/$drafter" in
  */*/none|ling-3.2-air/publisher/mtp|sante-air-vl/nvfp4/ling-mtp) ;;
  *) echo 'Use DRAFTER=mtp for Ling, or DRAFTER=ling-mtp for BF16-derived Air-VL NVFP4.' >&2; exit 2 ;;
esac
if [[ $quant == nvfp4 ]]; then
  manifest=install/checkpoint-sante-nvfp4.json
fi
read -r repo revision served cache_dir < <(python3 -c '
import json, sys
pin = json.load(open(sys.argv[2]))
snapshot = pin[sys.argv[1]]
print(snapshot["repository"], snapshot["revision"], pin["served_model_name"],
      snapshot.get("cache_directory", snapshot["revision"]))
' "$mode" "$manifest")
MODEL_ROOT=${MODEL_ROOT:-$HOME/models/sparkling}
mkdir -p "$MODEL_ROOT"
MODEL_ROOT=$(realpath "$MODEL_ROOT")
model=$MODEL_ROOT/$cache_dir
# shellcheck source=install/common.sh
source install/common.sh
if [[ $cmd != verify && ( ! -f $model/.sparkling-verified || ( $cmd == download && $quant == publisher ) ) ]]; then
  hf_download "$repo" "$revision" "$model"
  python3 install/check_files.py "$mode" "$model" --manifest "$manifest"
  touch "$model/.sparkling-verified"
fi
if [[ $drafter == ling-mtp ]]; then
  read -r donor_repo donor_rev < <(python3 -c 'import json; p=json.load(open("install/checkpoint.json"))["spark"]; print(p["repository"],p["revision"])')
  donor=$MODEL_ROOT/$donor_rev
  donor_files=(config.json model.safetensors.index.json experts-layer42.safetensors rest-001.safetensors)
  for file in "${donor_files[@]}"; do
    if [[ ! -f $donor/$file ]]; then
      [[ $cmd != verify ]] || { echo "missing donor file: $donor/$file" >&2; exit 1; }
      hf_download "$donor_repo" "$donor_rev" "$donor" "${donor_files[@]}"
      break
    fi
  done
  view="$(realpath "$model")-ling-mtp-${donor_rev:0:12}"
  flags=()
  if [[ $cmd == verify ]]; then
    python3 install/check_files.py "$mode" "$model" --manifest "$manifest"
    flags+=(--verify)
  fi
  python3 install/prepare_sante_draft.py "$model" "$donor" "$view" "${flags[@]}"
  model=$view
  [[ $cmd != verify ]] || exit 0
fi
[[ $cmd != download ]] || exit 0
if [[ $cmd == verify ]]; then exec python3 install/check_files.py "$mode" "$model" --manifest "$manifest"; fi
profile=${PROFILE:-default}
mounts=(--mount "type=bind,src=$model,dst=/model,readonly")
if [[ -f $profile ]]; then
  mounts+=(--mount "type=bind,src=$(realpath "$profile"),dst=/opt/atlas/profiles/custom.json,readonly")
  profile=custom
elif [[ ! -f install/profiles/$profile.json ]]; then
  echo "unknown profile: $profile" >&2; exit 2
fi
fast=$(python3 -c 'import sys; sys.path.insert(0,"install"); import serve; print(serve.default_precision(*sys.argv[1:]))' "$mode" "$model_id")
precision=${PREFILL_PRECISION:-$fast}
decode_precision=${DECODE_PRECISION:-$fast}
cache_namespace=$(python3 -c 'import sys; sys.path.insert(0,"install"); import serve; print(serve.precision_cache_namespace(*sys.argv[1:]))' "$mode" "$precision" "$decode_precision" "$model_id" "$quant")
if [[ $drafter != none ]]; then cache_namespace+="-${drafter}1"; fi
if [[ -n ${PREFIX_CACHE_DIR:-} || -n ${PREFIX_CACHE_GB:-} ]]; then
  [[ ${PREFIX_CACHE_DIR:-} == /* ]] || { echo 'PREFIX_CACHE_DIR must be absolute' >&2; exit 2; }
  export PREFIX_CACHE_GB=${PREFIX_CACHE_GB:-48}
  python3 -c 'import os,sys; sys.path.insert(0,"install"); import serve; serve.disk_prefix_cache(os.environ["PREFIX_CACHE_GB"],sys.argv[1])' "$mode"
  mkdir -p "$PREFIX_CACHE_DIR/$cache_namespace/kv"
  mounts+=(--mount "type=bind,src=$(realpath "$PREFIX_CACHE_DIR"),dst=/prefix-cache")
fi
image=${IMAGE:-$(install/build.sh --tag)}
if ! docker image inspect "$image" >/dev/null 2>&1; then
  if [[ ${PULL:-1} != 1 ]] || ! docker pull "$image"; then
    [[ -z ${IMAGE:-} ]] || { echo "custom image unavailable: $image" >&2; exit 1; }
    image=$(install/build.sh)
  fi
fi
if docker container inspect "$name" >/dev/null 2>&1; then docker rm -f "$name"; fi
docker run -d --name "$name" --memory 114g --gpus device=0 --ipc host --network host \
  --label io.enntity.owner=SparkLing --label io.enntity.job=serve --security-opt no-new-privileges=true \
  "${mounts[@]}" -e MODEL_PATH=/model -e SERVED_MODEL_NAME="$served" \
  -e SPARKLING_MODEL="$model_id" -e SPARKLING_DRAFTER="$drafter" -e SPARKLING_QUANT="$quant" -e SPARKLING_MODE="$mode" -e SPARKLING_DECODE_PRECISION="$decode_precision" -e SPARKLING_PREFILL_PRECISION="$precision" -e SPARKLING_PROFILE="$profile" \
  -e SPARKLING_GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-}" \
  -e SPARKLING_PREFIX_CACHE_GB="${PREFIX_CACHE_GB:-}" -e SPARKLING_TOOL_GUARD="${TOOL_GUARD:-stream}" \
  -e SPARKLING_TOOL_GUARD_ALLOW_HOSTS="${TOOL_GUARD_ALLOW_HOSTS:-}" -e SPARKLING_TOOL_GUARD_DENY_HOSTS="${TOOL_GUARD_DENY_HOSTS:-}" \
  -e SPARKLING_TOOL_GUARD_MAX_BYTES="${TOOL_GUARD_MAX_BYTES:-1048576}" "$image"
for ((i=0; i<90; i++)); do
  if [[ $(docker inspect -f '{{.State.Running}}' "$name") != true ]]; then docker logs --tail 40 "$name"; exit 1; fi
  if curl -fsS http://127.0.0.1:8897/health >/dev/null 2>&1; then
    curl -fsS --max-time 300 http://127.0.0.1:8897/v1/chat/completions -H 'Content-Type: application/json' \
      -d "{\"model\":\"$served\",\"messages\":[{\"role\":\"user\",\"content\":\"What is 17*23? Answer with the number.\"}],\"temperature\":0,\"max_tokens\":128,\"chat_template_kwargs\":{\"enable_thinking\":false}}" | python3 install/smoke.py
    exit 0
  fi
  sleep 10
done
echo 'startup timed out; inspect ./start.sh logs' >&2; exit 1
