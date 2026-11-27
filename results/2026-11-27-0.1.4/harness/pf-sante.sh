#!/usr/bin/env bash
# usage: pf-sante.sh LABEL BIN|release   LingSante through 0.1.3's start.sh launch (args captured by shim/docker),
# optional engine binary over /usr/local/bin/spark: greedy probes + long-prompt identity -> pf-ab/LABEL-*.jsonl
set -euo pipefail
runs=~/models/sparkling/claude-runs; label=$1; bin=$2; name=claude-pfab; out=$runs/pf-ab; mkdir -p "$out"
docker rm -f $name >/dev/null 2>&1 || true
rm -f $runs/shim/run-args
(cd ~/models/sparkling/claude-rel013 && PATH=$runs/shim:$PATH CONTAINER_NAME=$name MODEL_ROOT=~/models/sparkling PULL=0 \
  IMAGE=ghcr.io/enntity/atlas-sparkling:7a1f9d22997d PREFIX_CACHE_DIR=~/models/sparkling/claude-pc timeout 30 ./start.sh --model lingsante-3.1-air-vl up >/dev/null 2>&1 || true)
args=$(sed 's/SPARKLING_PREFIX_CACHE_GB=[^ ]*/SPARKLING_PREFIX_CACHE_GB=0/' $runs/shim/run-args)
mount=""; [[ $bin != release ]] && mount="-v $HOME/models/sparkling/$bin:/usr/local/bin/spark:ro"
eval "docker ${args/run -d/run -d $mount}" >/dev/null
trap "docker logs $name > $out/$label-server.log 2>&1; docker rm -f $name >/dev/null" EXIT
for i in $(seq 1 450); do curl -fsS --max-time 2 localhost:8897/health >/dev/null 2>&1 && break; sleep 2; done
cd $runs
python3 probe.py 8897 256 lingsante-3.1-air-vl-atlas > "$out/$label-probe.jsonl"
MODEL=lingsante-3.1-air-vl-atlas python3 long_id.py 20000 50000 > "$out/$label-long.jsonl"
python3 note_replay.py > "$out/$label-note.txt"; python3 note_replay.py cold >> "$out/$label-note.txt"
