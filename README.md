<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# SparkLing

SparkLing serves Ling-3.2-air on one NVIDIA DGX Spark using Atlas. Strict
mode serves inclusionAI’s original FP8 checkpoint. The preferred fast profile
uses Primitive AI’s NVFP4A16 checkpoint, Atlas-quantized attention weights
and the original BF16 vocabulary head.

On the stock RigMark prose suite, the fast profile generated 43.70 tokens/s
against 21.60 for vLLM. Both finished both prose prompts. The answers took
38.3 and 30.5 s on Atlas, against 65.8 and 64.3 s on vLLM. Eight-client
prose throughput was lower at 115.35 versus 123.22 aggregate tokens/s.
Both engines exhausted the standard code budget. With thinking disabled,
both returned visible code and Atlas decoded at 42.85 versus 21.55 tokens/s.
[One-Spark benchmark receipts](results/README.md) ·
[Strict serving result](results/gb10-strict-serving.json) · [GB10 kernel checks](results/gb10-operators.json)

| Mode | Checkpoint | Weight storage |
| --- | --- | --- |
| `strict` (default) | inclusionAI/Ling-3.2-air | Original dynamic FP8, with BF16 and FP32 exceptions. The 13 shards total 120.4 GiB. |
| `spark` | primitive-ai/Ling-3.2-air-NVFP4A16 | NVFP4 routed experts with BF16 activations. The weights occupy about 72.5 GiB. |

Ling-3.2-air is a mixture-of-experts model with 124B parameters and 5.5B
active per token. The first two layers use dense feed-forward networks. Each
of the other 40 layers selects eight of 512 routed experts per token and
also runs one shared expert. Both checkpoints use this architecture.

One Spark shares memory between the GPU and the OS. Strict therefore needs
disk-backed expert residency. Keeping cold experts on disk preserves the
published weights and leaves memory for attention and requests. The
strict profile reserves a shared BF16 KV pool for one full-length context.
Shorter concurrent requests share that pool, leaving the rest of unified
memory available to cache expert pages. Strict also enables Atlas reference
mode so the checkpoint supplies the chat template and sampling defaults.

## Prepare a checkpoint

```sh
./start.sh --version
./start.sh --mode strict download
./start.sh --mode strict verify
# Optional, separate snapshot for Spark mode
./start.sh --mode spark download
```

Each mode uses its own immutable revision below `MODEL_ROOT` (default
`~/models/sparkling`). The verifier checks every inference file, including
the processor, chat template, tensor index and each shard. Download both
modes only if the disk has room for both snapshots.

## Serving and qualification

The distribution follows SparkInkling's `start.sh`, install-tree image tags,
profiles and RigMark suites. The default Atlas endpoint is
`http://127.0.0.1:8897/v1` and the served model name is `ling-3.2-air-atlas`.
The launcher includes build, status, logs and stop commands. Settings are
listed in `.env.example`. Default, saver and max profiles are development
settings pending measurements on GB10. The bundled next-token prediction
layer still needs a Ling-specific speculative path.

For experimental faster prompt processing on one Spark, run
`PREFILL_PRECISION=nvfp4 ./start.sh --mode spark up`. This uses Primitive AI’s
checkpoint, quantizes the routed expert activations to NVFP4 for large prompt
batches, and uses an 8,192-token prompt chunk in the bundled profiles.
Single-token decode keeps BF16 activations. The default
`PREFILL_PRECISION=checkpoint` follows the activation precision of the selected
checkpoint. Disk prefix caches use a separate directory for each precision.

The experimental `DECODE_PRECISION=nvfp4` option asks Atlas to quantize the
large BF16 attention projections in Primitive AI’s checkpoint at load time.
It uses those copies for forward passes of up to eight rows, including short
prompt tails. Larger passes continue using the published BF16 weights. This
option can be combined with `PREFILL_PRECISION=nvfp4` in Spark mode.

The preferred fast profile keeps the vocabulary head in BF16. Run
`PREFILL_PRECISION=nvfp4 DECODE_PRECISION=nvfp4 ./start.sh --mode spark up`.
It completed both standard prose prompts in 38.3 s and 30.5 s.

For the experimental quantized output head, run
`PREFILL_PRECISION=nvfp4 DECODE_PRECISION=nvfp4-head ./start.sh --mode spark up`.
Atlas also quantizes the BF16 vocabulary output matrix from Primitive AI’s
checkpoint. Small batches use tensor cores for attention and routed experts.
This profile has a distinct disk-cache directory.

Compare strict to the original FP8 weights and Spark to the same NVFP4A16
weights in the reference engine. The results directory includes raw one-Spark
RigMark receipts and the engine and model revisions used for each run.

[Original model](https://huggingface.co/inclusionAI/Ling-3.2-air) ·
[Spark-mode checkpoint](https://huggingface.co/primitive-ai/Ling-3.2-air-NVFP4A16) ·
[Atlas branch](https://github.com/Enntity/atlas/tree/ling/3.2-air) ·
[Benchmark instructions](bench/README.md)
