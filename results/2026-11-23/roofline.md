# One-Spark roofline for Ling-3.2-air

| NVFP4A16 workload | vLLM parity | 2× target | Preliminary Atlas |
| --- | ---: | ---: | ---: |
| Initial RigMark code decode | 21.53 tokens/s | 43.07 tokens/s | 26.56 tokens/s |
| Matched single-stream 64-token decode | 21.61 tokens/s | 43.22 tokens/s | 45.01 tokens/s (Atlas NVFP4 attention) |
| Cold 8,192-token prefill | 2,839 tokens/s | 5,678 tokens/s | 3,407 tokens/s (opt-in NVFP4 activations) |

Both engines exceeded the code completion budget on both runs. Their decode
rates count generated tokens. The 8K baseline is the median of two runs. On the first identical 8K token
sequence, Atlas at `052091fda` took 36.07 seconds versus 3.17 seconds on
vLLM (227 versus 2,583 tokens/s). The first Atlas implementation failed this
probe because the scheduler forced the remaining tokens into one oversized
chunk. The measured revision keeps the 2,048-token chunk limit and attends
to preceding chunks. Text, vision, the Paris tool argument and short decode
also passed on this revision. [8K result](decision-8k.json) ·
[Tool and vision responses](decision-modal.jsonl) · [Decode](decision-short.jsonl)

## Decode

For one request generating one token at a time, the text trunk reads
5.627 GB of non-routed weights, 1.062 GB of packed routed weights and scales
(8/512 of 67.948 GB), and a 0.805 GB vocabulary head. Only one 5,120-byte
input embedding row is needed. These counts exclude the vision tower,
projector and optional next-token prediction layer. All sizes here use decimal
GB. The counts come from the safetensors headers at the pinned revision.

Assuming the active weights are read once from DRAM, 7.494 GB/token gives
36.4 tokens/s at NVIDIA's 273 GB/s peak. A device-to-device copy on the test
Spark sustained 244.8 GB/s counting reads and writes, equivalent to 32.7
tokens/s at that bandwidth. Copy throughput is an estimate for streaming
weights. State, attention cache, temporary buffers and kernel overhead
consume additional time. [NVIDIA hardware specifications](https://www.nvidia.com/en-us/products/workstations/dgx-spark/)

43.07 tokens/s would require about 323 GB/s under these assumptions. At the
measured copy bandwidth it requires at most 5.68 GB per output token, before
other traffic. The next decode experiments should reduce the active BF16
weight footprint or amortize the weight reads over accepted speculative
tokens. Keep the original FP8 checkpoint and sampling behavior in strict mode.

### First decode experiment

Replacing only the 238 BF16 attention projections with inclusionAI's original
FP8 tensors and scales saved 2.425 GB per output token. The remaining
matrix traffic is about 5.07 GB/token. On the fixed 64-token probe, this
experimental mix reached 30.29 and 30.31 tokens/s. Both outputs matched vLLM
and unmodified Atlas byte for byte. It also answered the arithmetic smoke test
correctly. The comparison is across different precision profiles. These two
checks establish a speed signal and narrow correctness coverage.

[Changed tensor counts](experimental-fp8-attention-build.json) ·
[Decode streams](hybrid-short.jsonl) · [Arithmetic check](hybrid-math.json)

## Prefill

The active trunk contains about 2.811B non-routed matrix elements and 1.887B
routed matrix elements per token. Two FLOPs per multiply-add gives about
9.40 GFLOP per prompt token for those projections. This excludes attention
score/value products, recurrent state updates and the final vocabulary
projection. The test Spark sustained 77.55 TFLOP/s on a dense 4096³ BF16
matrix multiply. That gives a projection-only estimate of 8,252 tokens/s.

If a 2,048-token chunk touches every routed expert and each matrix is fetched
once, it reads about 73.6 GB of weights. At 244.8 GB/s the bandwidth estimate
is 6,814 tokens/s. Under that routing and reuse assumption the lower of the
two estimates is bandwidth. The 5,678 target would consume about 204 GB/s
and 53.4 TFLOP/s in projections alone. It fits both first-order ceilings
with limited headroom for other work. Actual routing skew, grouped matrix
sizes and rereads determine how close the implementation can get.

A CUDA profile of one approximately 2K-token text request assigned 78.4% of GPU
kernel time to dense BF16 matrix multiplication, 15.1% to grouped NVFP4
expert multiplication, 2.0% to the KDA recurrence and 0.6% to the tiled MLA
prompt kernel. [Nsight kernel timings](prefill-profile.json)

Switching dense prompt projections and shared-expert matrix multiplies to
Atlas's tuned BF16 matrix multiply (`a83891fdb`) reduced cold time to first token on that
same 8K prompt from 36.07 to 9.26 seconds (227 to 885 tokens/s, 3.90×).
The matched vLLM sample took 3.17 seconds. Short decode remained 27.6–27.7
tokens/s. The arithmetic, vision and forced-tool probes passed. This closes
part of the prefill gap and leaves the model in development.
[8K result](blas-8k.json) · [Decode](blas-short.jsonl) ·
[Vision and tools](blas-modal.jsonl)

### NVFP4 prompt activations and larger tiles

In Spark mode, `PREFILL_PRECISION=nvfp4` uses the same Primitive AI weights
with dynamically quantized expert activations for large prompt batches.
Atlas commit `098118206` also uses longer chunks, batched dense
projections, a register-resident KDA recurrence, and 64-row attention tiles
scheduled to reuse KV pages across adjacent queries. The reference ran
vLLM with its checkpoint-default activations.

| Cold prompt | Atlas time to first token | vLLM time to first token | Atlas / vLLM median throughput |
| --- | --- | --- | --- |
| 8,192 tokens | 2.485 s, 2.406 s | 3.172 s, 2.646 s | 1.18× |
| 32,768 tokens | 12.050 s, 12.005 s | 14.660 s, 11.578 s | 1.08× |

All four eight-token continuations matched the reference byte for byte. The
fixed 64-token decode ran at 27.56 tokens/s against the reference median
of 21.61. A single eight-client code round reached 40.53 aggregate tokens/s
against 130.73 on the corresponding reference round. The development
candidate passed the image, tool-call, arithmetic and retrieval checks.
[Matched decision receipts](nvfp4-prefill-decision.json)

Atlas commit `423b7f0e0` switched concurrent decode to batched BF16 matrix-vector
products and enabled CUDA graph replay keyed by the ordered recurrent-state slots.
The same eight-client code round improved from 40.53 to 87.40 aggregate tokens/s.
The reference reached 130.73. Two independent requests produced the same
outputs serially and concurrently. [Batch decode receipt](batch-decode-decision.json)

### Attention requantization and eight-client decode

Atlas `6ff4a609a` can quantize 238 BF16 attention matrices in the Primitive AI
checkpoint to NVFP4 at load time. The packed matrices, including scales,
occupy 1.364 GB in place of 4.850 GB of reads per decoded token. That brings
estimated weight traffic to 4.008 GB/token. At the measured 244.8 GB/s,
the streaming estimate rises from 32.7 to 61.1 tokens/s. The original
matrices remain available for larger prompt batches.

| Matched decision probe | Atlas | vLLM | Atlas / vLLM |
| --- | ---: | ---: | ---: |
| Fixed 64-token response, single-stream decode | 45.01 tokens/s | 21.61 tokens/s | 2.08× |
| Cold 8K prompt, median prefill | 3,407 tokens/s | 2,839 tokens/s | 1.20× |
| Cold 32K prompt, median prefill | 2,735 tokens/s | 2,533 tokens/s | 1.08× |
| Eight clients, 256 tokens each, aggregate | 114.87 tokens/s | 130.73 tokens/s | 0.88× |

Both 8K continuations and both 32K continuations matched vLLM byte for byte,
as did the 64-token response. Each prefill median uses two requests. vLLM
was faster on the second 32K request (11.58 s versus 11.99 s). The 64-token
and eight-client rows use expert-weight reuse across requests. The long-prompt
probes preceded that switch. The eight-client round improved from 87.40 to
102.03 tokens/s with batched recurrence and routing, to 110.81 with quantized
attention, and to 114.87 with expert-weight reuse. All eight streams ran to
their reasoning-token cap in the final probe. This measures serving throughput.

In four additional greedy tests with thinking disabled, stock vLLM, Atlas
with checkpoint-precision decode and Atlas with quantized attention gave
the same four answers. All returned 11 for a Python expression whose value
is 15. All answered the other arithmetic question and both retrieval questions
correctly. The quantized candidate also passed image recognition and the forced
weather tool call. These probes give limited quality coverage.

[Decode, prefill, concurrency and quality receipts](nvfp4-decode-decision.json)

### Output head, routed tensor cores and prefix reuse

Atlas `50e6bd5d9` adds `DECODE_PRECISION=nvfp4-head` in Spark mode.
Requantizing the vocabulary head as well as the attention matrices brings
estimated weight reads down to 3.43 GB/token. That corresponds to 71.4
tokens/s at the measured streaming bandwidth. Single-stream decode reached
49.01 tokens/s on the matched 64-token response, against vLLM’s 21.61.
Eight clients reached 138.07 aggregate tokens/s in one 2,048-token round,
against 130.73 on the corresponding reference round.

The Ling attention kernel reads historical keys and values from the paged
cache. The candidate restores the recurrent state and final hidden row on an
exact hit. Cold and repeated 8K prompts took 2.372 s and 0.0094 s. At 32K
they took 11.970 s and 0.0127 s. All four continuations matched the reference.
Three requests with a shared prefix and different lookup questions returned
the expected answers. All eight concurrent lookup responses matched serial
execution. [Candidate decision probes](nvfp4-head-decision.json)

## Decision probes

Use one cold 8K RigMark prompt and a short warm single-stream decode to test a
candidate. Check the answer and any affected tool or vision path. Run the
complete release suites after the short checks justify qualification.

[Reference receipt](reference-a16-code.json) ·
[Atlas decode receipt](atlas-a16-initial-decode.json) ·
[GB10 microbenchmark](gb10-roof-gpu.json) ·
[Weight byte and element counts](a16-roof-bytes.json)
