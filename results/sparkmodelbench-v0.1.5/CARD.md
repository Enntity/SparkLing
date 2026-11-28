<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# SparkLing v0.1.5 · SparkModelBench

Measured November 27–28, 2026 on one DGX Spark (GB10, 128 GB), one model server at a time. RigMark protocol 1.3.0, RigMark Quality v0.0.2, `reasoning_effort: low`, which leaves Ling's thinking on. Ling-3.2-air ran [SparkModelBench 293a44f](https://github.com/enntity/sparkmodelbench/tree/293a44f82dd977af8aeeee31df7ba70da9f4545d) (180-second quality task budget) and LingSante-3.1-air-VL ran [SparkModelBench 2b9ce8c](https://github.com/enntity/sparkmodelbench/tree/2b9ce8ce5ec1ddb495dc94b8b31ec610ef044d80) (300-second quality task budget) on the published `0.1.5` image. The vLLM rows are its November 26 run on the same Spark ([v0.1.3 scorecard](../sparkmodelbench-v0.1.3/CARD.md)); vLLM did not change.

Serving measurements and quality tasks by **Alex Ellis, OpenFaaS Ltd**. [RigMark](https://github.com/alexellis/rigmark) · [RigMark Quality](https://github.com/alexellis/rigmark-quality). Enntity adds the staggered four-request field guide.

| Contender | Engine and image | Drafter | Context |
|---|---|---|---:|
| Ling-3.2-air · SparkLing | SparkLing 0.1.5 (Atlas, Enntity/atlas ling/3.2-air @ f9d0ebf95); ghcr.io/enntity/atlas-sparkling:0.1.5 (= :cacf8ea89389) | Ling-3.2-air's native MTP layer, 2 chained drafts at C1 and 1 draft at C2–C8 (`ATLAS_MTP_K_LADDER=1:2,4:1,8:1`, `ATLAS_MTP_MAX_SEQS=8`), active inside `<think>` | 262,144 |
| LingSante-3.1-air-VL · SparkLing | SparkLing 0.1.5 (Atlas, Enntity/atlas ling/3.2-air @ f9d0ebf95); ghcr.io/enntity/atlas-sparkling:0.1.5 (= :cacf8ea89389), via ./start.sh --model lingsante-3.1-air-vl up | Ling-3.2-air's MTP layer (borrowed), 1 draft up to 8 active requests (`ATLAS_MTP_MAX_SEQS=8`), active inside `<think>` | 131,072 |
| Ling-3.2-air · vLLM, MTP ×3 | vLLM nightly a2bcb5657 (SparkLing reference command, as in 0.1.2); vllm/vllm-openai:cu134-nightly-a2bcb5657 @ sha256:24541db891c590e3a4022c7206c3ebb00e4be35442f54c20f2edf12eddfef4bf | native MTP, num_speculative_tokens 3 | 262,144 |

Receipts: [ling.json](ling.json) · [ling-concurrency.json](ling-concurrency.json) · [lingsante.json](lingsante.json) · [lingsante-concurrency.json](lingsante-concurrency.json) · [vllm-mtp3.json](vllm-mtp3.json) · [vllm-mtp3-concurrency.json](vllm-mtp3-concurrency.json)

## RigMark Quality · task completion

| Contender | Task | Checks passed | Finished | Seconds | Output tokens |
|---|---|---|---|---:|---:|
| Ling-3.2-air · SparkLing | `python-expiry` | Passed | Finished | 36.9 | 1,408 |
| Ling-3.2-air · SparkLing | `go-transfer-ledger` | Failed | TimeoutError: timed out (180 s budget) | 195.3 | 9,452 |
| Ling-3.2-air · SparkLing | `payment-recovery` | Passed | Finished | 17.6 | 770 |
| Ling-3.2-air · SparkLing | `evidence-revisions` | Passed | Finished | 7.9 | 364 |
| LingSante-3.1-air-VL · SparkLing | `python-expiry` | Passed | Finished | 48.0 | 2,155 |
| LingSante-3.1-air-VL · SparkLing | `go-transfer-ledger` | Failed | model exhausted output token cap | 173.1 | 8,389 |
| LingSante-3.1-air-VL · SparkLing | `payment-recovery` | Passed | Finished | 19.2 | 810 |
| LingSante-3.1-air-VL · SparkLing | `evidence-revisions` | Passed | Finished | 12.8 | 598 |
| Ling-3.2-air · vLLM, MTP ×3 | `python-expiry` | Passed | Finished | 31.8 | 1,064 |
| Ling-3.2-air · vLLM, MTP ×3 | `go-transfer-ledger` | Failed | TimeoutError: timed out (180 s budget) | 195.6 | 5,949 |
| Ling-3.2-air · vLLM, MTP ×3 | `payment-recovery` | Passed | Finished | 16.9 | 624 |
| Ling-3.2-air · vLLM, MTP ×3 | `evidence-revisions` | Passed | Finished | 7.1 | 250 |

## RigMark · generation, median

| Contender | Workload | Tok/s | Last output (s) | Output tokens | Gates |
|---|---|---:|---:|---:|---:|
| Ling-3.2-air · SparkLing | code | 66.15 | 70.93 | 4,673 | 5/5 |
| Ling-3.2-air · SparkLing | prose | 57.10 | 45.26 | 2,666 | 5/5 |
| Ling-3.2-air · SparkLing | structured | 67.14 | 15.30 | 1,007 | 5/5 |
| LingSante-3.1-air-VL · SparkLing | code | 60.78 | 78.43 | 4,737 | 5/5 |
| LingSante-3.1-air-VL · SparkLing | prose | 56.77 | 101.64 | 5,747 | 3/5 |
| LingSante-3.1-air-VL · SparkLing | structured | 60.32 | 17.95 | 1,064 | 5/5 |
| Ling-3.2-air · vLLM, MTP ×3 | code | 42.47 | 193.21 | 8,192 | 2/5 |
| Ling-3.2-air · vLLM, MTP ×3 | prose | 37.70 | 59.44 | 2,148 | 3/5 |
| Ling-3.2-air · vLLM, MTP ×3 | structured | 41.87 | 24.27 | 1,006 | 5/5 |

Output tokens is the median of five runs; a run that reaches the 8,192-token cap fails its gate.

## SparkLing · staggered C4

Four ~16K-token prompts, one second apart, 400 output tokens each, thinking off. Stream TTFT is measured from each request's own send.

| Contender | Round | Wall (s) | Stream TTFT (s) | Longest visible gap (s) | Full streams |
|---|---|---:|---|---:|---|
| Ling-3.2-air · SparkLing | warmup | 36.78 | 18.21, 18.13, 18.71, 17.71 | 1.55 | True |
| Ling-3.2-air · SparkLing | 1 | 36.94 | 18.22, 18.12, 18.69, 17.69 | 1.54 | True |
| Ling-3.2-air · SparkLing | 2 | 36.71 | 18.20, 18.11, 18.68, 17.68 | 1.54 | True |
| Ling-3.2-air · SparkLing | 3 | 36.50 | 18.19, 18.10, 18.68, 17.68 | 1.55 | True |
| LingSante-3.1-air-VL · SparkLing | warmup | 37.42 | 18.42, 18.35, 18.98, 17.98 | 1.58 | True |
| LingSante-3.1-air-VL · SparkLing | 1 | 36.61 | 18.28, 18.21, 18.81, 17.81 | 1.56 | True |
| LingSante-3.1-air-VL · SparkLing | 2 | 36.84 | 18.24, 18.15, 18.74, 17.74 | 1.57 | True |
| LingSante-3.1-air-VL · SparkLing | 3 | 36.55 | 18.27, 18.18, 18.77, 17.77 | 1.56 | True |
| Ling-3.2-air · vLLM, MTP ×3 | warmup | 73.05 | 6.92, 24.69, 40.86, 57.74 | 0.39 | True |
| Ling-3.2-air · vLLM, MTP ×3 | 1 | 73.30 | 6.49, 24.05, 40.76, 57.78 | 0.39 | True |
| Ling-3.2-air · vLLM, MTP ×3 | 2 | 72.63 | 6.47, 24.17, 40.25, 57.20 | 0.39 | True |
| Ling-3.2-air · vLLM, MTP ×3 | 3 | 73.31 | 6.46, 24.51, 40.89, 57.88 | 0.40 | True |

- Ling-3.2-air · SparkLing: median measured wall **36.71 s**
- LingSante-3.1-air-VL · SparkLing: median measured wall **36.61 s**
- Ling-3.2-air · vLLM, MTP ×3: median measured wall **73.30 s**

## RigMark · prefill

| Contender | Prompt tokens | First TTFT (s) | First tok/s | Replay TTFT (s) | Replay tok/s | First cached tokens |
|---|---:|---:|---:|---:|---:|---|
| Ling-3.2-air · SparkLing | 8,192 | 2.20 | 3,730 | 0.014 | 593,107 | 0, 0, 0 |
| Ling-3.2-air · SparkLing | 32,768 | 9.43 | 3,476 | 0.017 | 1,907,001 | 0, 0, 0 |
| Ling-3.2-air · SparkLing | 65,536 | 21.55 | 3,042 | 0.020 | 3,330,758 | 0, 0, 0 |
| Ling-3.2-air · SparkLing | 131,072 | 54.43 | 2,408 | 0.027 | 4,917,720 | 0, 0, 0 |
| Ling-3.2-air · SparkLing | 262,144 | — | — | — | — | not run: context limit including output reserve |
| LingSante-3.1-air-VL · SparkLing | 8,192 | 2.21 | 3,712 | 0.014 | 565,043 | 0, 0, 0 |
| LingSante-3.1-air-VL · SparkLing | 32,768 | 9.45 | 3,468 | 0.016 | 1,989,557 | 0, 0, 0 |
| LingSante-3.1-air-VL · SparkLing | 65,536 | 21.55 | 3,042 | 0.020 | 3,345,551 | 0, 0, 0 |
| LingSante-3.1-air-VL · SparkLing | 131,072 | — | — | — | — | not run: context limit including output reserve |
| LingSante-3.1-air-VL · SparkLing | 262,144 | — | — | — | — | not run: context limit including output reserve |
| Ling-3.2-air · vLLM, MTP ×3 | 8,192 | 2.66 | 3,082 | 0.721 | 11,369 | not reported |
| Ling-3.2-air · vLLM, MTP ×3 | 32,768 | 11.84 | 2,768 | 1.103 | 29,711 | not reported |
| Ling-3.2-air · vLLM, MTP ×3 | 65,536 | 27.41 | 2,391 | 1.138 | 57,565 | not reported |
| Ling-3.2-air · vLLM, MTP ×3 | 131,072 | 71.16 | 1,842 | 1.594 | 82,211 | not reported |
| Ling-3.2-air · vLLM, MTP ×3 | 262,144 | — | — | — | — | not run: context limit including output reserve |

## RigMark · concurrency

RigMark's own sweep: short code prompts, 256 output tokens, three rounds per level. Every output was thinking.

| Contender | Requests | Aggregate tok/s | Per-stream tok/s | Per-stream TTFT (s) |
|---|---:|---:|---:|---:|
| Ling-3.2-air · SparkLing | 1 | 56.52 | 60.65 | 0.30 |
| Ling-3.2-air · SparkLing | 2 | 84.42 | 45.59 | 0.46 |
| Ling-3.2-air · SparkLing | 4 | 125.80 | 34.25 | 0.77 |
| Ling-3.2-air · SparkLing | 8 | 141.50 | 19.81 | 1.38 |
| LingSante-3.1-air-VL · SparkLing | 1 | 53.44 | 57.01 | 0.31 |
| LingSante-3.1-air-VL · SparkLing | 2 | 79.46 | 43.42 | 0.47 |
| LingSante-3.1-air-VL · SparkLing | 4 | 104.27 | 29.15 | 0.80 |
| LingSante-3.1-air-VL · SparkLing | 8 | 129.35 | 17.92 | 1.42 |
| Ling-3.2-air · vLLM, MTP ×3 | 1 | 41.48 | 43.18 | 0.27 |
| Ling-3.2-air · vLLM, MTP ×3 | 2 | 73.08 | 38.95 | 0.32 |
| Ling-3.2-air · vLLM, MTP ×3 | 4 | 112.21 | 30.50 | 0.54 |
| Ling-3.2-air · vLLM, MTP ×3 | 8 | 174.35 | 24.77 | 0.53 |
