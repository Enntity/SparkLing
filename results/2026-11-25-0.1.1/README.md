<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# One DGX Spark, November 25, 2026: SparkLing 0.1.1

Every run used one GB10, with no other model server using the GPU, unless a section says otherwise. The release image is `ghcr.io/enntity/atlas-sparkling:0.1.1` (index digest `sha256:d86608d1…a495`, install tree `753fe2b286a6`, Atlas `ling/3.2-air` at `965128de1`). Its build ran 8,827 engine tests, with 0 failures. [`harness/rel11.sh`](harness/rel11.sh) launched it through `./start.sh up` with the default profile and default drafting, then ran the probes. The disk prefix cache used a 16 GiB budget because this Spark's disk was nearly full.

## Release image

| | Ling-3.2-air | LingSante-3.1-air-VL |
| --- | ---: | ---: |
| Context window, tokens | 262,144 | 131,072 |
| Shared KV pool, tokens | 2,200,304 | 2,377,344 |
| Single stream, mean of eight prompts, tok/s | 54.8 | 54.2 |
| Drafted text equal to plain decode | 8 of 8 | 8 of 8 |
| Plain decode, mean of eight prompts, tok/s | 44.6 | 44.1 |
| Aggregate, 1 / 2 / 4 / 8 clients, tok/s | 54.6 / 65.7 / 81.1 / 104.4 | 51.2 / 61.6 / 79.4 / 104.0 |
| Median time to first token, 8 clients | 1.04 s | 1.06 s |
| Arithmetic, 30 word problems with thinking on | 30 | 30 |
| Single-tool calls, right tool and argument | 10 of 10 | 10 of 10 |
| Media: red-to-blue clip, counting clip (GIF and MP4), 90 s 720p clip, invoice, grid | all read correctly | all read correctly |

[Ling](release/ling-spark-probe.jsonl) · [Ling plain](release/ling-spark-plain.jsonl) · [Ling concurrency](release/ling-spark-conc.jsonl) · [Ling media](release/ling-spark-media.jsonl) · [Ling tasks](release/ling-spark-task.json) · [Ling cache log](release/ling-spark-server-kv.log) · [Air-VL](release/sante-spark-probe.jsonl) · [Air-VL plain](release/sante-spark-plain.jsonl) · [Air-VL concurrency](release/sante-spark-conc.jsonl) · [Air-VL media](release/sante-spark-media.jsonl) · [Air-VL tasks](release/sante-spark-task.json) · [Air-VL cache log](release/sante-spark-server-kv.log)

The vLLM and llama.cpp comparison runs are unchanged from 0.1.0. [0.1.0 results](../2026-11-25/README.md)

## Long context

| Ling-3.2-air, drafting on | 2K | 32K | 128K | 262K |
| --- | ---: | ---: | ---: | ---: |
| Decode after the prompt, tok/s | 44.4 | 40.6 | 34.9 | 27.9 |

Each prompt continued a repetitive weather-station log, on which drafting accepts few proposals. The 128K and 262K runs reused the shorter prompt's cached prefix. Their first tokens took 94.9 s for 98,314 new prompt tokens and 259.4 s for 131,082. [Depth runs](release/ling-spark-depth.jsonl) · [`harness/deep_decode.py`](harness/deep_decode.py)

- **Eight full windows at once.** Eight prompts of 262,132 tokens, distinct from the first token, were sent together, each with its own key word to recall. All eight answered correctly. The 2,097,056 prompt tokens took 2,694 seconds. [Results](release/r11-long-8x256k.jsonl) · [`harness/conc_long.py`](harness/conc_long.py)
- **Eight 64K prompts at once.** Eight prompts of 65,524 tokens took 279 seconds, and all eight answered correctly. [Results](release/r11-long-8x64k.jsonl)

## Decisions

- **Latent cache.** Ling's MLA layers cached 32 heads of expanded keys and padded values, 16.6 KB per token per layer, so one 262,144-token window needed 28.4 GiB. In 0.1.0's own release run the weights left 6.1 GB for the pool: 3,522 blocks, or 56,352 tokens, and the engine reported that the pool fit no request at the advertised 131,072 tokens. Atlas now caches one 576-value BF16 row per token per layer: the normalized 512-channel latent and the rotated 64-channel RoPE key. Keys and values share the row, so it costs 1.15 KB. [0.1.0 cache log](raw/010-ling-spark-kv.log)
- **Absorbed decode.** Decode, batched decode and the drafting verify absorb the query through `kv_b_proj`'s key half, attend the latent with tensor cores, and apply the value half afterwards. Each row's arithmetic depends only on that row and its sequence length, so drafted text stays equal to plain decode. Prompts rebuild per-head keys and values from the latent 8,192 tokens at a time and merge the tiles by their softmax state.
- **Speed.** The first 0.1.1 image drafted at 53.4 tok/s against 0.1.0's 55.2. An Nsight Systems profile of the same drafted requests put the attention path at 77 µs per layer per step against 0.1.0's ~40. 0.1.0 read `kv_b_proj` once per token as NVFP4, about 2 MB per layer. The absorbed form read both halves as BF16 on every step, about 8 MB per layer, through latency-bound kernels. A 256-key minimum decode split also left short contexts to one or two thread blocks. The release quantizes both halves to NVFP4 under NVFP4 decode precision, with faster kernels, and lowers the minimum split to 64 keys. The path now takes 38.8 µs per layer per step. In alternating runs, drafted decode measured 54.1–54.9 tok/s against 0.1.0's 54.4. [Kernel profiles](profile/) · [`harness/prof.sh`](harness/prof.sh) · [`harness/ab.sh`](harness/ab.sh)

  | µs per call, drafted Ling | 0.1.0 | first 0.1.1 image | release |
  | --- | ---: | ---: | ---: |
  | Query absorption | — | 27.7 | 11.6 |
  | Value projection | — | 25.1 | 11.3 |
  | Attention | 19.3 | 19.3 | 11.1 |
  | Cache write, assembly and merge | 13.4 | 5.1 | 4.8 |
  | `kv_b_proj` for the new token | ~7.7 | — | — |

- **NVFP4 or BF16 absorption.** A first comparison of about 100 decode positions per engine, together with GSM8K, pointed against NVFP4. A run of about 775 positions per engine showed no difference against vLLM: NVFP4 absorption, BF16 absorption and 0.1.0 agree within error. Strict and checkpoint precision keep BF16, with the same faster kernel layout.
- **Simultaneous long prompts.** Batched prefill passed each MLA prompt as one chunk unless the model reported paged-history prefill, but it checked only whether the model used MLA. Two long prompts arriving together then reached Ling as 49K- and 245K-token chunks and failed. Both batched paths now use the same check as single-request prefill. 0.1.0 had the same fault; its concurrency runs used short prompts.
- **Memory.** At 0.80 utilization, the latent pool held 750,800 tokens with drafting on. At 0.88 it held 7.8 windows, and at 0.89 it holds 8.4. The display carveout holds whole per-layer buffers, and each of Ling's seven buffers is 2.4 GiB at this size, so the default pool cannot use it. Ling's model card turns its loop watchdog off, so the plain-decode rollback ring that only the watchdog reads is turned off too, which frees 5.1 GB without drafting. Atlas's load check now uses Ling's measured device-to-disk ratio, 1.02 with a margin to 1.05, instead of the generic 1.3, which projected 94.3 GB for 72.5 GB of weights.

## Quality

### GSM8K

The first 200 test problems of `openai/gsm8k` at revision `e53f0488`, run greedy with thinking off, eight requests at a time. Each run's score is the last number in its reply, after `Answer:` when present. 0.1.0 ran from its own image and launcher. [`harness/gsm8k_eval.py`](harness/gsm8k_eval.py) · [`harness/quality.sh`](harness/quality.sh)

| Build | Ling-3.2-air | LingSante-3.1-air-VL |
| --- | ---: | ---: |
| 0.1.0 | [196](quality/gsm8k-ling-010.jsonl) | [193](quality/gsm8k-sante-010.jsonl) |
| 0.1.1, NVFP4 absorption | [192](quality/gsm8k-ling-011.jsonl) | [192](quality/gsm8k-sante-011.jsonl) |
| 0.1.1, BF16 absorption | [193](quality/gsm8k-ling-bf.jsonl) | [189](quality/gsm8k-sante-bf.jsonl) |

Builds that differ only in rounding moved by up to four problems. Some misses are grading artifacts, for example a reply that reached 95 minutes and then wrote `Answer: 1 hour and 35 minutes`. The NVFP4 rows used the first NVFP4 kernels, which have the release's quantized weights and a different summation order.

### Next-token distributions against vLLM

vLLM served Primitive AI's NVFP4A16 checkpoint with the reference launcher, without speculation. Each engine returned the top five tokens at every position. Total variation compares the reference's top five plus one bin for everything else. [`harness/dist_ling.py`](harness/dist_ling.py) · [`harness/dist_decode2.py`](harness/dist_decode2.py) · [`harness/dist_score.py`](harness/dist_score.py) · [`harness/dist_decode_score.py`](harness/dist_decode_score.py) · [`harness/dist3.sh`](harness/dist3.sh)

| Decode: 220 contexts, six greedy tokens each, compared while the texts agree | Positions | Top-1 agreement | Mean total variation |
| --- | ---: | ---: | ---: |
| 0.1.0 | 772 | 94.2% ± 0.8 | 0.049 ± 0.002 |
| 0.1.1, NVFP4 absorption | 780 | 95.0% ± 0.8 | 0.050 ± 0.002 |
| 0.1.1, BF16 absorption | 770 | 94.3% ± 0.8 | 0.050 ± 0.002 |

| Prompt: eight passages forced through the engine | Positions | Top-1 agreement | Mean total variation | Perplexity |
| --- | ---: | ---: | ---: | ---: |
| vLLM | 1,183 | — | — | 3.613 |
| 0.1.0 | 1,183 | 97.4% | 0.036 | 3.598 |
| 0.1.1 | 1,183 | 97.0% | 0.036 | 3.598 |

[Decode runs](quality/) (`de-*.jsonl`) · [Prompt runs](quality/) (`dist-*.jsonl`) · [Contexts](quality/gsm8k-questions.json)

### LingSante-3.1-air-VL against its original BF16

`bench/sante_distributions.py` ran on 0.1.0 and on 0.1.1 with BF16 absorption, and was scored with `bench/score_sante.py` against the BF16 receipts from November 24. Both agreed with BF16 on all five free continuations and on the top token at 56 of 68 forced positions, with mean coarsened total variation 0.090. [0.1.0](quality/sante-010-quality.jsonl) · [0.1.1](quality/sante-bf-quality.jsonl) · [BF16 receipts](../2026-11-24/air-vl-quant/)

## Strict mode

Strict streams its experts from disk. Uncapped, the latent pool took 68.1 GB, and Strict decoded at 0.3 tok/s with a 94 s first token. Capped at eight windows, 15.8 GB at 262K, it decoded at 1.9 tok/s. That run was on another Spark with about 23 GB of other GPU work resident. [Strict probe](raw/strict-l3.jsonl)

## Development runs

These runs measured the latent build on another Spark beside about 23 GB of other GPU work. `l2-off` and `b-new` are plain decode at 262K and 8K windows, which returned the same text. `l3-off` is the tensor-core decode kernel. `av-l3-*` are Air-VL plain decode and media. `x-*` and `r11-*` are the first 0.1.1 image on the release Spark. [Raw](raw/)
