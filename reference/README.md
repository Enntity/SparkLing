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
  --revision 3a78e58506316b5b9b7d06037910c3f4abdd291f \
  --local-dir "$MODEL_DIR"

python3 reference/serve.py \
  --mode a16 \
  --model-dir "$MODEL_DIR"
```

The generated Docker invocation uses TP=1, GPU 0, port `8897`, a 40,960-token context, eight concurrent sequences,
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
  --revision ff099487f6f57165e6fa9386ad61fddfafc78b76 \
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
matrix for both servers. Start the reference with
`--served-model-name ling-3.2-air-atlas` so the request bodies also match.

```sh
SPARKLING_URL=http://127.0.0.1:8897 \
SERVED_MODEL_NAME=ling-3.2-air-atlas \
RIGMARK=/path/to/rigmark \
  bench/rigmark.sh reference metadata-reference.json out/reference
```

The Primitive card's throughput and quality numbers are a useful sanity check,
not a SparkLing result. A claim that SparkLing beats this reference needs the
paired run on the same Spark, with no second model resident during timing.

## File-backed SGLang on GB10

The original FP8 model also runs through SGLang on one Spark. The launcher
places the two routed FP8 weight arrays per layer in temporary NVMe-backed
mappings and passes their coherent GB10 addresses to Triton. SGLang still
loads the original tensors, runs the model kernels and schedules requests.
On the arithmetic probe it generated `391` and stopped on token 156895.

Allow 120 GiB of free NVMe space for temporary weights in addition to the
verified checkpoint. The mappings are released when the server exits. From
the SparkLing checkout, with `STRICT_DIR` set to the original checkpoint:

```sh
SCRATCH="$HOME/models/sparkling-sglang-scratch"
mkdir -p "$SCRATCH"
docker run --rm --gpus device=0 --ipc=host \
  -p 127.0.0.1:11897:11897 \
  -v "$STRICT_DIR:/model:ro" -v "$PWD/reference:/reference:ro" \
  -v "$SCRATCH:/expert-disk" -e LING_EXPERT_DISK=/expert-disk -e HF_HUB_OFFLINE=1 \
  --entrypoint python3 \
  lmsysorg/sglang@sha256:7d0d06441b8220e537ae6bb287294cab26f3c877ded3bc6803a148c294b2cce6 \
  /reference/strict_sglang.py --model-path /model --tp 1 --trust-remote-code \
  --served-model-name ling-3.2-air-atlas --host 0.0.0.0 --port 11897 \
  --attention-backend triton --moe-runner-backend triton --cuda-graph-max-bs-decode 8 \
  --context-length 40960 --max-total-tokens 40960 --max-running-requests 8 \
  --mem-fraction-static 0.82
```

## LingSante Air-VL MXFP4 on GB10

Download the publisher checkpoint with `./start.sh --model sante-air-vl --mode spark --quant publisher download`. Run SGLang on the same Spark separately from Atlas. The ARM64 manifest below belongs to the publisher-recommended `lmsysorg/sglang:dev-Ling-3.0-flash-VL` image. The short comparison uses one GPU, a 4,096-token reference window and the native FlashInfer MXFP4 MoE backend.

```sh
rev=be6dd27338cdb9677e11418ec62b349dfb48fb2d
docker run --rm --gpus device=0 --network host --ipc host \
  -v "${MODEL_ROOT:-$HOME/models/sparkling}/$rev:/model:ro" \
  -e HF_HUB_OFFLINE=1 -e OMP_NUM_THREADS=1 -e MKL_NUM_THREADS=1 \
  --entrypoint python3 lmsysorg/sglang@sha256:7d0d06441b8220e537ae6bb287294cab26f3c877ded3bc6803a148c294b2cce6 \
  -m sglang.launch_server --model-path /model --served-model-name lingsante-air-vl \
  --host 127.0.0.1 --port 8898 --tp-size 1 --trust-remote-code --context-length 4096 \
  --dtype bfloat16 --mem-fraction-static 0.85 --max-running-requests 1 \
  --attention-backend flashinfer --mm-attention-backend triton_attn \
  --moe-runner-backend flashinfer_mxfp4 --disable-shared-experts-fusion \
  --reasoning-parser ling3 --disable-cuda-graph
```

For the short Ling-3.2-air drafting comparison on one Spark, use the A16 checkpoint with `--draft-tokens 3 --max-model-len 4096 --max-num-seqs 1 --served-model-name ling-3.2-air-atlas`. The launcher enables aligned Mamba caching and the requested MTP lookahead. The published 40K A16 RigMark baseline defaults to zero draft tokens.
