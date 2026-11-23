<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# SparkLing reference

This directory runs the published Ling-3.2-air reference through vLLM with
tensor parallelism fixed at one. The default `a16` path is the one-Spark
baseline: Primitive's `Ling-3.2-air-NVFP4A16` checkpoint is 77.88 GB and its
card reports measurements on one 96 GB RTX PRO 6000 Blackwell.

The checkpoint and container pins live in [`manifest.json`](manifest.json).
`serve.py` does not download weights. It checks the local checkpoint's
architecture, quantization format, index, and every indexed shard before
starting Docker. The container is given the model directory read-only and
offline Hugging Face settings, so an accidental fallback to another revision
cannot pass as a reference run.

## One-Spark reference

Download the exact model revision, then start the server on the same port used
by SparkLing's benchmark drivers:

```sh
MODEL_DIR="$PWD/models/Ling-3.2-air-NVFP4A16"
hf download primitive-ai/Ling-3.2-air-NVFP4A16 \
  --revision 741cdea2fde8a8e5f1b1bda209bc0fef4d60a18a \
  --local-dir "$MODEL_DIR"

python3 reference/serve.py \
  --mode a16 \
  --model-dir "$MODEL_DIR"
```

The generated Docker invocation uses TP=1, GPU 0, port `8897`, a 40,960-token context,
and `--gpu-memory-utilization 0.92`. On an ARM64 Spark it selects the pinned
ARM64 image manifest automatically. Use `--platform linux/amd64` only when
reproducing on an x86 host.

To inspect the command without starting Docker:

```sh
python3 reference/serve.py \
  --mode a16 \
  --model-dir "$MODEL_DIR" \
  --print-command
```

## Strict FP8 diagnostic

The publisher runs the original 129.28 GB FP8 checkpoint on four GPUs. This
command tests the stock TP=1 allocation on the same device as Atlas.

```sh
STRICT_DIR="$PWD/models/Ling-3.2-air"
hf download inclusionAI/Ling-3.2-air \
  --revision 1613b1a4dcc6aa0d8f346606628cd9a92061a525 \
  --local-dir "$STRICT_DIR"

python3 reference/serve.py \
  --mode strict \
  --model-dir "$STRICT_DIR"
```

The command enables the publisher's prefix cache, aligned Mamba cache and
three-token MTP. Record any allocation failure with the device's available
memory. A file-backed reference run must identify its placement changes in
the benchmark metadata.

## Image pin

The A16 card names the vLLM commit tag
`nightly-a2bcb5657a881a002e79d0adab3c6b5e39436121`. Docker Hub currently
exposes the active CUDA 13.4 multi-architecture tag with the same commit:

```text
docker.io/vllm/vllm-openai:cu134-nightly-a2bcb5657a881a002e79d0adab3c6b5e39436121
index  sha256:76a533475156ffdb3656ccc389d0c71f5cec16897c0f490ac43e4f379c4b4f0d
arm64  sha256:24541db891c590e3a4022c7206c3ebb00e4be35442f54c20f2edf12eddfef4bf
amd64  sha256:a7192cc1adb903c9052ae91d197ef37d13b2e94e6a5d06687e8a29eecad486db
```

The per-platform digest is used in the Docker reference. The registry record
is [Docker Hub's tag API](https://hub.docker.com/v2/repositories/vllm/vllm-openai/tags/cu134-nightly-a2bcb5657a881a002e79d0adab3c6b5e39436121).
The checkpoint cards are [Primitive's A16 card](https://huggingface.co/primitive-ai/Ling-3.2-air-NVFP4A16)
and [InclusionAI's FP8 card](https://huggingface.co/inclusionAI/Ling-3.2-air).

## Paired benchmark

Stop the candidate server before loading this one. Run the same RigMark
metadata, prompt revision, context limit, sampling settings, and concurrency
matrix for both servers:

```sh
SPARKLING_URL=http://127.0.0.1:8897 \
SERVED_MODEL_NAME=ling-3.2-air-reference \
RIGMARK=/path/to/rigmark \
  bench/rigmark.sh reference metadata-reference.json out/reference
```

The Primitive card's throughput and quality numbers are a useful sanity check,
not a SparkLing result. A claim that SparkLing beats this reference needs the
paired run on the same Spark, with no second model resident during timing.
