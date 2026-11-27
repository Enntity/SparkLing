<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# SparkLing v0.1.4 · SparkModelBench

Measured November 27, 2026 on one DGX Spark (GB10, 128 GB), one model server at a time. RigMark protocol 1.3.0, RigMark Quality v0.0.2, `reasoning_effort: low`, which leaves Ling's thinking on. [SparkModelBench 293a44f](https://github.com/enntity/sparkmodelbench/tree/293a44f82dd977af8aeeee31df7ba70da9f4545d) for every lane. The vLLM rows are its November 26 run on the same Spark ([v0.1.3 scorecard](../sparkmodelbench-v0.1.3/CARD.md)); vLLM did not change.

Serving measurements and quality tasks by **Alex Ellis, OpenFaaS Ltd**. [RigMark](https://github.com/alexellis/rigmark) · [RigMark Quality](https://github.com/alexellis/rigmark-quality). Enntity adds the staggered four-request field guide.

| Contender | Engine and image | Drafter | Context |
|---|---|---|---:|
| Ling-3.2-air · SparkLing | SparkLing 0.1.4 (Atlas, Enntity/atlas ling/3.2-air @ 469d1649b); ghcr.io/enntity/atlas-sparkling:0.1.4 (= :c523fbc3852c), the release image, via ./start.sh up | Ling-3.2-air's native MTP layer, one draft per step for up to four active requests, verified in one batched forward; plain decoding from five | 262,144 |
| LingSante-3.1-air-VL · SparkLing | SparkLing 0.1.4 (Atlas, Enntity/atlas ling/3.2-air @ 469d1649b); ghcr.io/enntity/atlas-sparkling:0.1.4 (= :c523fbc3852c), the release image, via ./start.sh up | Ling-3.2-air's MTP layer (borrowed), one draft per step for up to four active requests, verified in one batched forward; plain decoding from five | 131,072 |
| Ling-3.2-air · vLLM, MTP ×3 | vLLM nightly a2bcb5657 (SparkLing reference command, as in 0.1.2); vllm/vllm-openai:cu134-nightly-a2bcb5657 @ sha256:24541db891c590e3a4022c7206c3ebb00e4be35442f54c20f2edf12eddfef4bf | native MTP, num_speculative_tokens 3 | 262,144 |

Receipts: [ling.json](ling.json) · [ling-concurrency.json](ling-concurrency.json) · [lingsante.json](lingsante.json) · [lingsante-concurrency.json](lingsante-concurrency.json) · [vllm-mtp3.json](vllm-mtp3.json) · [vllm-mtp3-concurrency.json](vllm-mtp3-concurrency.json)

## RigMark Quality · task completion

| Contender | Task | Checks passed | Finished | Seconds | Output tokens |
|---|---|---|---|---:|---:|
| Ling-3.2-air · SparkLing | `python-expiry` | Passed | Finished | 44.3 | 1,801 |
| Ling-3.2-air · SparkLing | `go-transfer-ledger` | Failed | TimeoutError: timed out | 196.9 | 171 |
| Ling-3.2-air · SparkLing | `payment-recovery` | Passed | Finished | 20.5 | 840 |
| Ling-3.2-air · SparkLing | `evidence-revisions` | Passed | Finished | 10.1 | 395 |
| LingSante-3.1-air-VL · SparkLing | `python-expiry` | Passed | Finished | 74.1 | 2,986 |
| LingSante-3.1-air-VL · SparkLing | `go-transfer-ledger` | Failed | TimeoutError: timed out | 196.0 | 135 |
| LingSante-3.1-air-VL · SparkLing | `payment-recovery` | Passed | Finished | 21.8 | 824 |
| LingSante-3.1-air-VL · SparkLing | `evidence-revisions` | Passed | Finished | 11.3 | 428 |
| Ling-3.2-air · vLLM, MTP ×3 | `python-expiry` | Passed | Finished | 31.8 | 1,064 |
| Ling-3.2-air · vLLM, MTP ×3 | `go-transfer-ledger` | Failed | TimeoutError: timed out | 195.6 | 5,949 |
| Ling-3.2-air · vLLM, MTP ×3 | `payment-recovery` | Passed | Finished | 16.9 | 624 |
| Ling-3.2-air · vLLM, MTP ×3 | `evidence-revisions` | Passed | Finished | 7.1 | 250 |

## RigMark · generation, median

| Contender | Workload | Tok/s | Last output (s) | Output tokens | Gates |
|---|---|---:|---:|---:|---:|
| Ling-3.2-air · SparkLing | code | 49.80 | 93.15 | 4,624 | 5/5 |
| Ling-3.2-air · SparkLing | prose | 49.02 | 35.50 | 1,717 | 5/5 |
| Ling-3.2-air · SparkLing | structured | 54.28 | 18.92 | 1,008 | 5/5 |
| LingSante-3.1-air-VL · SparkLing | code | 45.93 | 174.35 | 7,994 | 3/5 |
| LingSante-3.1-air-VL · SparkLing | prose | 44.59 | 162.54 | 7,226 | 3/5 |
| LingSante-3.1-air-VL · SparkLing | structured | 53.15 | 20.29 | 1,055 | 5/5 |
| Ling-3.2-air · vLLM, MTP ×3 | code | 42.47 | 193.21 | 8,192 | 2/5 |
| Ling-3.2-air · vLLM, MTP ×3 | prose | 37.70 | 59.44 | 2,148 | 3/5 |
| Ling-3.2-air · vLLM, MTP ×3 | structured | 41.87 | 24.27 | 1,006 | 5/5 |

Output tokens is the median of five runs; a run that reaches the 8,192-token cap fails its gate.

## SparkLing · staggered C4

Four ~16K-token prompts, one second apart, 400 output tokens each, thinking off. Stream TTFT is measured from each request's own send.

| Contender | Round | Wall (s) | Stream TTFT (s) | Longest visible gap (s) | Full streams |
|---|---|---:|---|---:|---|
| Ling-3.2-air · SparkLing | warmup | 36.83 | 18.36, 18.29, 18.92, 17.92 | 1.60 | True |
| Ling-3.2-air · SparkLing | 1 | 36.82 | 18.39, 18.32, 18.94, 17.94 | 1.59 | True |
| Ling-3.2-air · SparkLing | 2 | 36.91 | 18.33, 18.25, 18.88, 17.88 | 1.60 | True |
| Ling-3.2-air · SparkLing | 3 | 36.89 | 18.37, 18.30, 18.92, 17.92 | 1.59 | True |
| LingSante-3.1-air-VL · SparkLing | warmup | 36.90 | 18.43, 18.36, 18.97, 17.97 | 1.58 | True |
| LingSante-3.1-air-VL · SparkLing | 1 | 36.48 | 18.40, 18.34, 18.94, 17.94 | 1.57 | True |
| LingSante-3.1-air-VL · SparkLing | 2 | 36.74 | 18.39, 18.32, 18.92, 17.92 | 1.57 | True |
| LingSante-3.1-air-VL · SparkLing | 3 | 36.89 | 18.42, 18.37, 18.98, 17.99 | 1.59 | True |
| Ling-3.2-air · vLLM, MTP ×3 | warmup | 73.05 | 6.92, 24.69, 40.86, 57.74 | 0.39 | True |
| Ling-3.2-air · vLLM, MTP ×3 | 1 | 73.30 | 6.49, 24.05, 40.76, 57.78 | 0.39 | True |
| Ling-3.2-air · vLLM, MTP ×3 | 2 | 72.63 | 6.47, 24.17, 40.25, 57.20 | 0.39 | True |
| Ling-3.2-air · vLLM, MTP ×3 | 3 | 73.31 | 6.46, 24.51, 40.89, 57.88 | 0.40 | True |

- Ling-3.2-air · SparkLing: median measured wall **36.89 s**
- LingSante-3.1-air-VL · SparkLing: median measured wall **36.74 s**
- Ling-3.2-air · vLLM, MTP ×3: median measured wall **73.30 s**

## RigMark · prefill

| Contender | Prompt tokens | First TTFT (s) | First tok/s | Replay TTFT (s) | Replay tok/s | First cached tokens |
|---|---:|---:|---:|---:|---:|---|
| Ling-3.2-air · SparkLing | 8,192 | 2.23 | 3,670 | 0.013 | 617,891 | 0, 0, 0 |
| Ling-3.2-air · SparkLing | 32,768 | 9.50 | 3,449 | 0.016 | 2,030,990 | 0, 0, 0 |
| Ling-3.2-air · SparkLing | 65,536 | 21.69 | 3,021 | 0.021 | 3,123,737 | 0, 0, 0 |
| Ling-3.2-air · SparkLing | 131,072 | 54.94 | 2,386 | 0.028 | 4,744,688 | 0, 0, 0 |
| Ling-3.2-air · SparkLing | 262,144 | — | — | — | — | not run: context limit including output reserve |
| LingSante-3.1-air-VL · SparkLing | 8,192 | 2.22 | 3,688 | 0.013 | 634,399 | 0, 0, 0 |
| LingSante-3.1-air-VL · SparkLing | 32,768 | 9.51 | 3,446 | 0.016 | 2,039,206 | 0, 0, 0 |
| LingSante-3.1-air-VL · SparkLing | 65,536 | 21.74 | 3,015 | 0.020 | 3,313,246 | 0, 0, 0 |
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
| Ling-3.2-air · SparkLing | 1 | 41.86 | 44.13 | 0.33 |
| Ling-3.2-air · SparkLing | 2 | 64.72 | 34.41 | 0.49 |
| Ling-3.2-air · SparkLing | 4 | 97.10 | 26.11 | 0.82 |
| Ling-3.2-air · SparkLing | 8 | 140.56 | 19.50 | 1.48 |
| LingSante-3.1-air-VL · SparkLing | 1 | 41.17 | 43.58 | 0.34 |
| LingSante-3.1-air-VL · SparkLing | 2 | 61.55 | 32.75 | 0.50 |
| LingSante-3.1-air-VL · SparkLing | 4 | 86.93 | 23.40 | 0.82 |
| LingSante-3.1-air-VL · SparkLing | 8 | 122.77 | 16.79 | 1.50 |
| Ling-3.2-air · vLLM, MTP ×3 | 1 | 41.48 | 43.18 | 0.27 |
| Ling-3.2-air · vLLM, MTP ×3 | 2 | 73.08 | 38.95 | 0.32 |
| Ling-3.2-air · vLLM, MTP ×3 | 4 | 112.21 | 30.50 | 0.54 |
| Ling-3.2-air · vLLM, MTP ×3 | 8 | 174.35 | 24.77 | 0.53 |
