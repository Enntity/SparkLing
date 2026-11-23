#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ ${1:-} == --version ]]; then exec python3 install/serve.py --version; fi
if [[ -f .env ]]; then set -a; source ./.env; set +a; fi
mode=${MODE:-strict}
if [[ ${1:-} == --mode ]]; then
  [[ $# -ge 2 ]] || { echo '--mode requires strict or spark' >&2; exit 2; }
  mode=$2; shift 2
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
  --help|-h) echo './start.sh [--mode strict|spark] [download|verify|build|up|stop|logs|status]'; exit ;;
  up|verify|download) ;;
  *) echo "unknown command: $cmd" >&2; exit 2 ;;
esac
[[ $mode == strict || $mode == spark ]] || { echo 'MODE must be strict or spark' >&2; exit 2; }
read -r repo revision served < <(python3 -c 'import json,sys; p=json.load(open("install/checkpoint.json")); m=p[sys.argv[1]]; print(m["repository"],m["revision"],p["served_model_name"])' "$mode")
MODEL_ROOT=${MODEL_ROOT:-$HOME/models/sparkling}
mkdir -p "$MODEL_ROOT"
MODEL_ROOT=$(realpath "$MODEL_ROOT")
model=$MODEL_ROOT/$revision
# shellcheck source=install/common.sh
source install/common.sh
if [[ $cmd == download || ( $cmd == up && ! -f $model/.sparkling-verified ) ]]; then
  hf_download "$repo" "$revision" "$model"
  python3 install/check_files.py "$mode" "$model"
  touch "$model/.sparkling-verified"
fi
[[ $cmd != download ]] || exit 0
if [[ $cmd == verify ]]; then exec python3 install/check_files.py "$mode" "$model"; fi
[[ ${DRAFTER:-none} == none ]] || { echo 'The Ling MTP drafter requires an Atlas implementation' >&2; exit 2; }
profile=${PROFILE:-default}
mounts=(--mount "type=bind,src=$model,dst=/model,readonly")
if [[ -f $profile ]]; then
  mounts+=(--mount "type=bind,src=$(realpath "$profile"),dst=/opt/atlas/profiles/custom.json,readonly")
  profile=custom
elif [[ ! -f install/profiles/$profile.json ]]; then
  echo "unknown profile: $profile" >&2; exit 2
fi
if [[ -n ${PREFIX_CACHE_DIR:-} || -n ${PREFIX_CACHE_GB:-} ]]; then
  [[ ${PREFIX_CACHE_DIR:-} == /* ]] || { echo 'PREFIX_CACHE_DIR must be absolute' >&2; exit 2; }
  export PREFIX_CACHE_GB=${PREFIX_CACHE_GB:-48}
  python3 -c 'import os,sys; sys.path.insert(0,"install"); import serve; serve.disk_prefix_cache(os.environ["PREFIX_CACHE_GB"],sys.argv[1])' "$mode"
  mkdir -p "$PREFIX_CACHE_DIR/$mode/kv"
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
  -e SPARKLING_MODE="$mode" -e SPARKLING_PROFILE="$profile" \
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
