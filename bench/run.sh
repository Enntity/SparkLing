#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# Run the pinned SparkModelBench suite against the server ./start.sh started.
# SERVED_MODEL_NAME picks the model (lingsante-3.1-air-vl-atlas for LingSante).
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
suite="$root/bench/sparkmodelbench"
if [[ ! -f "$suite/run.py" || ! -f "$suite/upstream/rigmark/bench.py" || ! -f "$suite/upstream/rigmark-quality/rigmark" ]]; then
  git -C "$root" submodule update --init --recursive -- bench/sparkmodelbench
fi
pin=$(git -C "$root" rev-parse HEAD:bench/sparkmodelbench)
if [[ $(git -C "$suite" rev-parse HEAD) != "$pin" ]]; then
  echo "Benchmark pin differs. Run git submodule update --init --recursive." >&2
  exit 1
fi
exec python3 "$suite/run.py" --base-url "http://127.0.0.1:${SPARKLING_PORT:-8897}" \
  --model "${SERVED_MODEL_NAME:-ling-3.2-air-atlas}" "$@"
