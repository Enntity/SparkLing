#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# Run the RigMark suites used for the one-Spark comparison against the
# server ./start.sh started, in the mode it is serving. Nothing else should be
# using the Spark. See docs/REPRODUCE.md.
#
#   RIGMARK=/path/to/rigmark bench/rigmark.sh LABEL METADATA.json [OUTDIR]
#
# LABEL names the run (for example "strict"); METADATA.json describes it
# (hardware, image tag, drafter, competing traffic); OUTDIR defaults to the
# current directory. Writes LABEL-code.json and LABEL-prose.json there.
set -euo pipefail
[[ $# -ge 2 && $# -le 3 ]] || { sed -n '3,12p' "$0" >&2; exit 2; }
label=$1
metadata=$(realpath "$2")
mkdir -p "${3:-.}"
out=$(realpath "${3:-.}")
: "${RIGMARK:?set RIGMARK to a RigMark checkout}"
url=${SPARKLING_URL:-http://127.0.0.1:${SPARKLING_PORT:-8897}}
model=${SERVED_MODEL_NAME:-ling-3.2-air-atlas}
comparison_id=${SPARKLING_COMPARISON_ID:-sparkling-atlas}
extra='{"chat_template_kwargs":{"enable_thinking":true}}'
curl -sf "$url/health" >/dev/null || { echo "no server at $url; run ./start.sh first" >&2; exit 1; }
cd "$RIGMARK"
# code suite: decode, cold and replayed prefill, 1/2/4/8 concurrent requests
./rigmark run --base-url "$url" --model "$model" --metadata "$metadata" --comparison-id "$comparison_id" \
  --runs 2 --prefill-runs 2 --prefill-depths 8192,32768 --concurrency 1,2,4,8 --concurrency-runs 2 \
  --extra-body "$extra" --label "sparkling-$label-code" --output "$out/$label-code.json"
# prose suite: decode again, 1/4/8 concurrent prose requests
./rigmark run --base-url "$url" --model "$model" --metadata "$metadata" --comparison-id "$comparison_id" \
  --runs 2 --concurrency 1,4,8 --concurrency-runs 2 --concurrency-workload prose --skip-prefill \
  --extra-body "$extra" --label "sparkling-$label-prose" --output "$out/$label-prose.json"
echo "wrote $out/$label-code.json and $out/$label-prose.json"
