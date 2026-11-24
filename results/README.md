<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# Results

## One DGX Spark, November 24, 2026

[256K retrieval, original FP8 capacity, and LingSante Air-VL parity and speed](2026-11-24/README.md)

## One DGX Spark, November 23, 2026

The [decode and prefill rooflines](2026-11-23/roofline.md) compare the parity
and 2× targets with the active weight traffic and measured GB10 compute rate.

### Preferred profile with the BF16 output head

`PREFILL_PRECISION=nvfp4 DECODE_PRECISION=nvfp4` keeps the BF16 vocabulary
head from Primitive AI’s checkpoint. This profile ran from the pinned product
image on the same Spark as vLLM. It passed both prose and both structured
completions in the stock prose suite. Both engines exhausted the 4,096-token
budget on the two thinking-enabled code prompts.

| Workload | Atlas | vLLM |
| --- | ---: | ---: |
| Prose decode, tokens/s | 43.70 | 21.60 |
| Prose completion times, seconds | 38.30 / 30.48 | 65.80 / 64.30 |
| Structured decode, tokens/s | 44.09 | 21.61 |
| Same Go coding task, thinking off, tokens/s | 42.85 | 21.55 |
| Four-client prose, aggregate tokens/s | 83.78 | 78.80 |
| Eight-client prose, aggregate tokens/s | 115.35 | 123.22 |
| Eight-client code, aggregate tokens/s | 132.54 | 134.33 |
| 8K cold / exact replay, first matched pair in seconds | 2.378 / 0.0117 | 3.172 / 0.2478 |
| 32K cold / exact replay, first matched pair in seconds | 11.998 / 0.0135 | 14.660 / 0.2875 |

Both engines returned visible code in the thinking-disabled control. All eight
concurrent lookup responses matched serial execution. Atlas answered three
shared-prefix questions correctly, recognized the red image and called the
weather tool with Paris. Both cold and both cached completions matched vLLM.
The eight-client code, cache and thinking-disabled rows are focused comparisons
alongside the stock prose suite. [Preferred-profile measurements](2026-11-23/bf16-head-qualification.json)

### Full paired RigMark qualification with the experimental NVFP4 output head

Atlas `50e6bd5d9` ran the unmodified Spark-family code and prose suites on the
same DGX Spark as stock vLLM. Both used Primitive AI's NVFP4A16 checkpoint.
The Atlas candidate additionally quantized the attention and vocabulary head
weights and the large-prompt expert activations. The candidate image was
built by `./start.sh build` and served by the normal launcher.

Atlas led 23 of RigMark's 24 throughput comparisons. The comparator rejected
the run on completion quality. Both engines exhausted 4,096 tokens on both
standard code prompts. Atlas also exhausted the budget on one prose prompt
without producing a visible answer. vLLM completed both prose prompts. Both
engines passed both structured-output checks.

| Workload | Atlas tokens/s | vLLM tokens/s | Ratio |
| --- | ---: | ---: | ---: |
| Single-stream code decode | 46.09 | 21.53 | 2.14× |
| Single-stream prose decode, prose suite | 46.87 | 21.60 | 2.17× |
| Cold 8K / 32K prefill | 3,447 / 2,732 | 2,839 / 2,533 | 1.21× / 1.08× |
| Repeated 8K / 32K prompt | 843,134 / 2,589,143 | 34,123 / 118,405 | 24.71× / 21.87× |
| Eight-client code, aggregate | 141.97 | 134.33 | 1.06× |
| Eight-client prose, aggregate | 118.44 | 123.22 | 0.96× |

Replay throughput counts previously processed prompt tokens. On eight-client
prose, median per-stream decode was 16.91 tokens/s on Atlas and 15.90 on
vLLM. Median first-token latency was 2.20 s on Atlas and 0.61 s on vLLM.

In a separate control, both engines received the first Go coding prompt
with thinking disabled and the same token cap. Both returned visible code
and passed RigMark's basic completion check. Atlas decoded at 47.59 tokens/s
and vLLM at 21.55. The check scores completion; it does not compile the Go.
[Qualification measurements](2026-11-23/one-spark-qualification.json) ·
[Rooflines and decision probes](2026-11-23/roofline.md)

### Initial matched 64-token decode

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
ID are in the receipts. The paired candidate result appears above.

[Code receipt](2026-11-23/reference-a16-code.json) ·
[Prose receipt](2026-11-23/reference-a16-prose.json) ·
[Machine and engine metadata](2026-11-23/reference-a16-metadata.json) ·
[Checksums](2026-11-23/SHA256SUMS)

The [strict serving checks](gb10-strict-serving.json) use inclusionAI's
original FP8 checkpoint. The [CUDA operator measurements](gb10-operators.json)
report individual kernels.
