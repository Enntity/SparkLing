#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail
cd ${LLAMA_DIR:-$HOME/llama-cpp-ling}/llama.cpp
docker run --rm --name claude-llama-build --cpus=16 --memory 24g -v "$PWD:/src" -w /src \
  -e LIBRARY_PATH=/usr/local/cuda/lib64/stubs atlas-release-builder:1.93.1 bash -c '
  cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=121 -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release >/dev/null &&
  cmake --build build -j 16 --target llama-server llama-bench 2>&1 | tail -3'
ls -la build/bin/llama-server
