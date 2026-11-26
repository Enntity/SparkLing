#!/usr/bin/env bash
# usage: rigcap.sh LABEL IMAGE MAXSEQS   RigMark code C1/2/4/8 and prose C1/4/8 concurrency cells on product Ling (sl-up bypass).
set -u
cd ~/models/sparkling
label=$1 image=$2 seqs=$3; OUT=~/models/sparkling/claude-runs/rigcap; mkdir -p $OUT
M=$HOME/models/sparkling/claude-runs/rig013r/metadata-sparkling-ling.json
IMAGE=$image claude-runs/sl-up.sh ling-3.2-air spark mtp 3a78e58506316b5b9b7d06037910c3f4abdd291f ATLAS_MTP_MAX_SEQS=$seqs >/dev/null || exit 1
cd ~/qual-20261110/rigmark
EB="{\"chat_template_kwargs\":{\"enable_thinking\":false}}"
./rigmark run --base-url http://127.0.0.1:8897 --model ling-3.2-air-atlas --metadata $M --comparison-id ling-3.2-air --runs 2 --skip-prefill \
  --concurrency 1,2,4,8 --concurrency-runs 2 --extra-body "$EB" --label "$label-code" --output $OUT/$label-code.json > $OUT/$label.log 2>&1
./rigmark run --base-url http://127.0.0.1:8897 --model ling-3.2-air-atlas --metadata $M --comparison-id ling-3.2-air --runs 2 --skip-prefill \
  --concurrency 1,4,8 --concurrency-runs 2 --concurrency-workload prose --extra-body "$EB" --label "$label-prose" --output $OUT/$label-prose.json >> $OUT/$label.log 2>&1
docker rm -f claude-product >/dev/null
for w in code prose; do ./rigmark report $OUT/$label-$w.json | grep AGGREGATE; done
