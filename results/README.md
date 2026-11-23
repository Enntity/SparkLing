<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# Results

## One DGX Spark, November 23, 2026

### Matched 64-token decode

Atlas at `bf60d05c9` and stock vLLM ran the same 39-token counting prompt
three times each, sequentially on the same physical Spark. All six runs
returned the same 64 tokens. The table gives medians with thinking off.

| Engine | Decode tokens/s | Time to first token |
| --- | ---: | ---: |
| Atlas | 27.63 | 0.448 s |
| vLLM | 21.61 | 0.141 s |

Atlas decoded 28% faster on this prompt. vLLM returned the first token
0.307 s sooner. Both recognized a solid red image, and each reproduced its
two serial responses when the requests ran concurrently. On a forced weather
call, vLLM returned the city `Paris`. This Atlas revision returned
`<arg_value>Paris`.

Run `python3 bench/short_decode.py PORT` against each endpoint to reproduce
the probe. The request digest, response text, timings and token counts are in
the [Atlas streams](2026-11-23/atlas-a16-initial-short.jsonl) and
[vLLM streams](2026-11-23/reference-a16-short.jsonl). The
[Atlas metadata](2026-11-23/atlas-a16-initial-metadata.json) identifies the
binary and device.

### RigMark single-stream generation

The same preliminary Atlas binary ran the single-stream section with thinking
enabled, the standard 4,096-token cap, two requests per workload and the same
RigMark comparison ID as vLLM. Both engines passed both prose and both
structured checks. Both failed both code checks. Atlas produced a partial
visible answer on its second code run before the token limit.

| Workload | Atlas decode tokens/s | vLLM decode tokens/s | Atlas / vLLM |
| --- | ---: | ---: | ---: |
| Code | 26.56 | 21.53 | 1.23× |
| Prose | 26.92 | 21.56 | 1.25× |
| Structured | 27.51 | 21.30 | 1.29× |

The structured responses took about 37.5 s on Atlas and 47.5 s on vLLM.
Atlas generated longer responses on prose and took 104–110 s compared with
57–88 s on vLLM. [Atlas decode receipt](2026-11-23/atlas-a16-initial-decode.json) ·
[vLLM code-suite receipt](2026-11-23/reference-a16-code.json)

### RigMark reference under load

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
ID are in the receipts. The full paired RigMark result is pending.

[Code receipt](2026-11-23/reference-a16-code.json) ·
[Prose receipt](2026-11-23/reference-a16-prose.json) ·
[Machine and engine metadata](2026-11-23/reference-a16-metadata.json) ·
[Checksums](2026-11-23/SHA256SUMS)

The [strict serving checks](gb10-strict-serving.json) use inclusionAI's
original FP8 checkpoint. The [CUDA operator measurements](gb10-operators.json)
report individual kernels.
