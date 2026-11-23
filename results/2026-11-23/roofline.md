# One-Spark roofline for Ling-3.2-air

| NVFP4A16 workload | vLLM parity | 2× target | Preliminary Atlas |
| --- | ---: | ---: | ---: |
| Single-stream code decode | 21.53 tokens/s | 43.07 tokens/s | 26.56 tokens/s |
| Cold 8,192-token prefill | 2,839 tokens/s | 5,678 tokens/s | 227 tokens/s (one matched prompt) |

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

## Decision probes

Use one cold 8K RigMark prompt and a short warm single-stream decode to test a
candidate. Check the answer and any affected tool or vision path. Run the
complete release suites after the short checks justify qualification.

[Reference receipt](reference-a16-code.json) ·
[Atlas decode receipt](atlas-a16-initial-decode.json) ·
[GB10 microbenchmark](gb10-roof-gpu.json) ·
[Weight byte and element counts](a16-roof-bytes.json)
