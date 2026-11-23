<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# SparkLing

Ling-3.2-air on one NVIDIA DGX Spark, with engine development in Atlas. This is
a development checkout. The GB10 grouped-router kernel passes its operator
test. The full Atlas forward pass and the one-Spark performance comparison
are pending.

| Mode | Checkpoint | Weight storage |
| --- | --- | --- |
| `strict` (default) | inclusionAI/Ling-3.2-air | Original dynamic FP8, with BF16 and FP32 exceptions. The 13 shards total 120.4 GiB. |
| `spark` | primitive-ai/Ling-3.2-air-NVFP4A16 | NVFP4 routed experts with BF16 activations. The weights occupy about 72.5 GiB. |

One Spark shares memory between the GPU and the OS. Strict therefore needs
disk-backed expert residency. The model activates eight of 512 routed experts
per token in each MoE layer. Keeping cold experts on disk can preserve the
published weights and still leave memory for attention and requests.

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
profiles and RigMark suites. The intended Atlas endpoint is
`http://127.0.0.1:8897/v1` and the served model name is `ling-3.2-air-atlas`.
The launcher includes build, status, logs and stop commands. Settings are
listed in `.env.example`. Default, saver and max profiles are development
settings pending measurements on GB10. The bundled next-token prediction
layer still needs a Ling-specific speculative path.

Compare strict to the original FP8 weights and Spark to the same NVFP4A16
weights in the reference engine. Published results for other accelerators
are recorded by their respective authors. SparkLing will publish its own
one-Spark measurements with the raw RigMark receipts.

[Original model](https://huggingface.co/inclusionAI/Ling-3.2-air) ·
[Spark-mode checkpoint](https://huggingface.co/primitive-ai/Ling-3.2-air-NVFP4A16) ·
[Atlas branch](https://github.com/Enntity/atlas/tree/ling/3.2-air) ·
[Benchmark instructions](bench/README.md)
