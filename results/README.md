<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# Results

## One DGX Spark, November 23, 2026

The stock vLLM reference ran both SparkLing RigMark suites on Primitive AI's
NVFP4A16 checkpoint. The table reports medians. Decode counts generated
tokens, including reasoning. The two code runs each used all 4,096 tokens
without producing a visible answer. Both prose and both structured responses
passed RigMark's basic completion check.

| Reference workload | Tokens/s |
| --- | ---: |
| Single-stream code decode | 21.53 |
| Single-stream prose decode | 21.56 |
| Cold prefill, 8K / 32K prompt | 2,839 / 2,533 |
| Warm prefix replay, 8K / 32K prompt | 34,123 / 118,405 |
| Concurrent code, 1 / 2 / 4 / 8 requests | 21.3 / 45.9 / 79.9 / 134.3 |
| Concurrent prose, 1 / 4 / 8 requests | 21.3 / 78.8 / 123.2 |

The context limit was 40,960, KV storage was BF16 and speculation was off.
The concurrency rows give aggregate end-to-end throughput across requests.
The reference image digest, checkpoint revision and hashed physical device
ID are in the receipts. A paired Atlas result is pending.

[Code receipt](2026-11-23/reference-a16-code.json) ·
[Prose receipt](2026-11-23/reference-a16-prose.json) ·
[Machine and engine metadata](2026-11-23/reference-a16-metadata.json) ·
[Checksums](2026-11-23/SHA256SUMS)

The [strict serving checks](gb10-strict-serving.json) use inclusionAI's
original FP8 checkpoint. The [CUDA operator measurements](gb10-operators.json)
report individual kernels.
