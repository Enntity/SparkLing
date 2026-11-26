<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# SparkLing v0.1.3 · SparkModelBench

Measured November 26, 2026 on one DGX Spark (GB10, 128 GB), one model server at a time. RigMark protocol 1.3.0, RigMark Quality v0.0.2, `reasoning_effort: low`, which leaves Ling's thinking on. [SparkModelBench f2784ff](https://github.com/enntity/sparkmodelbench/tree/f2784ffd7e85fbaf2cb4fa8632b125af0af3ef28) for the four default lanes, [ebc29c4](https://github.com/enntity/sparkmodelbench/tree/ebc29c4) for the optional concurrency lane.

Serving measurements and quality tasks by **Alex Ellis, OpenFaaS Ltd**. [RigMark](https://github.com/alexellis/rigmark) · [RigMark Quality](https://github.com/alexellis/rigmark-quality). Enntity adds the staggered four-request field guide.

| Contender | Engine and image | Drafter | Context |
|---|---|---|---:|
| Ling-3.2-air · SparkLing | SparkLing 0.1.3 (Atlas, Enntity/atlas ling/3.2-air @ 46ed1a1f3); ghcr.io/enntity/atlas-sparkling:0.1.3 (= :7a1f9d22997d, index sha256:a8565646...71cfbd), the release image, via ./start.sh up | Ling-3.2-air's native MTP layer, one draft per step for up to four active requests, verified in one batched forward; plain decoding from five | 262,144 |
| LingSante-3.1-air-VL · SparkLing | SparkLing 0.1.3 (Atlas, Enntity/atlas ling/3.2-air @ 46ed1a1f3); ghcr.io/enntity/atlas-sparkling:0.1.3 (= :7a1f9d22997d, index sha256:a8565646...71cfbd), the release image, via ./start.sh up | Ling-3.2-air's MTP layer (borrowed), one draft per step for up to four active requests, verified in one batched forward; plain decoding from five | 131,072 |
| Ling-3.2-air · vLLM, MTP ×3 | vLLM nightly a2bcb5657 (SparkLing reference command, as in 0.1.2); vllm/vllm-openai:cu134-nightly-a2bcb5657 @ sha256:24541db891c590e3a4022c7206c3ebb00e4be35442f54c20f2edf12eddfef4bf | native MTP, num_speculative_tokens 3 | 262,144 |

Receipts: [ling.json](ling.json) · [ling-concurrency.json](ling-concurrency.json) · [lingsante.json](lingsante.json) · [lingsante-concurrency.json](lingsante-concurrency.json) · [vllm-mtp3.json](vllm-mtp3.json) · [vllm-mtp3-concurrency.json](vllm-mtp3-concurrency.json)

## RigMark Quality · task completion

| Contender | Task | Checks passed | Finished | Seconds | Output tokens |
|---|---|---|---|---:|---:|
| Ling-3.2-air · SparkLing | `python-expiry` | Passed | Finished | 45.1 | 1,801 |
| Ling-3.2-air · SparkLing | `go-transfer-ledger` | Failed | TimeoutError: timed out | 196.1 | 171 |
| Ling-3.2-air · SparkLing | `payment-recovery` | Passed | Finished | 21.5 | 840 |
| Ling-3.2-air · SparkLing | `evidence-revisions` | Passed | Finished | 10.2 | 395 |
| LingSante-3.1-air-VL · SparkLing | `python-expiry` | Passed | Finished | 73.4 | 2,986 |
| LingSante-3.1-air-VL · SparkLing | `go-transfer-ledger` | Failed | TimeoutError: timed out | 195.7 | 7,729 |
| LingSante-3.1-air-VL · SparkLing | `payment-recovery` | Passed | Finished | 21.1 | 824 |
| LingSante-3.1-air-VL · SparkLing | `evidence-revisions` | Passed | Finished | 11.1 | 428 |
| Ling-3.2-air · vLLM, MTP ×3 | `python-expiry` | Passed | Finished | 31.8 | 1,064 |
| Ling-3.2-air · vLLM, MTP ×3 | `go-transfer-ledger` | Failed | TimeoutError: timed out | 195.6 | 5,949 |
| Ling-3.2-air · vLLM, MTP ×3 | `payment-recovery` | Passed | Finished | 16.9 | 624 |
| Ling-3.2-air · vLLM, MTP ×3 | `evidence-revisions` | Passed | Finished | 7.1 | 250 |

## RigMark · generation, median

| Contender | Workload | Tok/s | Last output (s) | Output tokens | Gates |
|---|---|---:|---:|---:|---:|
| Ling-3.2-air · SparkLing | code | 49.04 | 115.42 | 5,645 | 5/5 |
| Ling-3.2-air · SparkLing | prose | 49.02 | 35.73 | 1,708 | 5/5 |
| Ling-3.2-air · SparkLing | structured | 54.13 | 18.98 | 1,008 | 5/5 |
| LingSante-3.1-air-VL · SparkLing | code | 49.07 | 87.23 | 4,272 | 4/5 |
| LingSante-3.1-air-VL · SparkLing | prose | 43.27 | 189.80 | 8,192 | 2/5 |
| LingSante-3.1-air-VL · SparkLing | structured | 53.09 | 20.02 | 1,038 | 5/5 |
| Ling-3.2-air · vLLM, MTP ×3 | code | 42.47 | 193.21 | 8,192 | 2/5 |
| Ling-3.2-air · vLLM, MTP ×3 | prose | 37.70 | 59.44 | 2,148 | 3/5 |
| Ling-3.2-air · vLLM, MTP ×3 | structured | 41.87 | 24.27 | 1,006 | 5/5 |

Output tokens is the median of five runs; a run that reaches the 8,192-token cap fails its gate.

## SparkLing · staggered C4

Four ~16K-token prompts, one second apart, 400 output tokens each, thinking off. Stream TTFT is measured from each request's own send.

| Contender | Round | Wall (s) | Stream TTFT (s) | Longest visible gap (s) | Full streams |
|---|---|---:|---|---:|---|
| Ling-3.2-air · SparkLing | warmup | 40.86 | 21.63, 21.71, 22.64, 21.64 | 1.90 | True |
| Ling-3.2-air · SparkLing | 1 | 40.84 | 21.63, 21.72, 22.62, 21.62 | 1.88 | True |
| Ling-3.2-air · SparkLing | 2 | 40.58 | 21.64, 21.72, 22.63, 21.63 | 1.88 | True |
| Ling-3.2-air · SparkLing | 3 | 40.61 | 21.64, 21.73, 22.65, 21.65 | 1.90 | True |
| LingSante-3.1-air-VL · SparkLing | warmup | 40.58 | 21.58, 21.68, 22.62, 21.62 | 1.91 | True |
| LingSante-3.1-air-VL · SparkLing | 1 | 40.53 | 21.65, 21.74, 22.67, 21.67 | 1.90 | True |
| LingSante-3.1-air-VL · SparkLing | 2 | 40.66 | 21.60, 21.71, 22.64, 21.64 | 1.90 | True |
| LingSante-3.1-air-VL · SparkLing | 3 | 40.77 | 21.64, 21.74, 22.67, 21.67 | 1.90 | True |
| Ling-3.2-air · vLLM, MTP ×3 | warmup | 73.05 | 6.92, 24.69, 40.86, 57.74 | 0.39 | True |
| Ling-3.2-air · vLLM, MTP ×3 | 1 | 73.30 | 6.49, 24.05, 40.76, 57.78 | 0.39 | True |
| Ling-3.2-air · vLLM, MTP ×3 | 2 | 72.63 | 6.47, 24.17, 40.25, 57.20 | 0.39 | True |
| Ling-3.2-air · vLLM, MTP ×3 | 3 | 73.31 | 6.46, 24.51, 40.89, 57.88 | 0.40 | True |

- Ling-3.2-air · SparkLing: median measured wall **40.61 s**
- LingSante-3.1-air-VL · SparkLing: median measured wall **40.66 s**
- Ling-3.2-air · vLLM, MTP ×3: median measured wall **73.30 s**

## RigMark · prefill

| Contender | Prompt tokens | First TTFT (s) | First tok/s | Replay TTFT (s) | Replay tok/s | First cached tokens |
|---|---:|---:|---:|---:|---:|---|
| Ling-3.2-air · SparkLing | 8,192 | 2.41 | 3,404 | 0.013 | 630,105 | 0, 0, 0 |
| Ling-3.2-air · SparkLing | 32,768 | 12.70 | 2,581 | 0.015 | 2,120,220 | 0, 0, 0 |
| Ling-3.2-air · SparkLing | 65,536 | 34.63 | 1,893 | 0.018 | 3,582,573 | 0, 0, 0 |
| Ling-3.2-air · SparkLing | 131,072 | 107.01 | 1,225 | 0.031 | 4,238,657 | 0, 0, 0 |
| Ling-3.2-air · SparkLing | 262,144 | — | — | — | — | not run: context limit including output reserve |
| LingSante-3.1-air-VL · SparkLing | 8,192 | 2.40 | 3,411 | 0.014 | 585,812 | 0, 0, 0 |
| LingSante-3.1-air-VL · SparkLing | 32,768 | 12.69 | 2,582 | 0.017 | 1,927,756 | 0, 0, 0 |
| LingSante-3.1-air-VL · SparkLing | 65,536 | 34.67 | 1,890 | 0.020 | 3,297,077 | 0, 0, 0 |
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
| Ling-3.2-air · SparkLing | 1 | 41.91 | 44.06 | 0.33 |
| Ling-3.2-air · SparkLing | 2 | 64.45 | 34.57 | 0.49 |
| Ling-3.2-air · SparkLing | 4 | 96.01 | 26.06 | 0.83 |
| Ling-3.2-air · SparkLing | 8 | 137.28 | 19.19 | 1.46 |
| LingSante-3.1-air-VL · SparkLing | 1 | 41.52 | 43.81 | 0.34 |
| LingSante-3.1-air-VL · SparkLing | 2 | 61.55 | 33.12 | 0.49 |
| LingSante-3.1-air-VL · SparkLing | 4 | 91.43 | 24.14 | 0.84 |
| LingSante-3.1-air-VL · SparkLing | 8 | 124.36 | 16.95 | 1.50 |
| Ling-3.2-air · vLLM, MTP ×3 | 1 | 41.48 | 43.18 | 0.27 |
| Ling-3.2-air · vLLM, MTP ×3 | 2 | 73.08 | 38.95 | 0.32 |
| Ling-3.2-air · vLLM, MTP ×3 | 4 | 112.21 | 30.50 | 0.54 |
| Ling-3.2-air · vLLM, MTP ×3 | 8 | 174.35 | 24.77 | 0.53 |
