<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# One DGX Spark, November 27, 2026: SparkLing 0.1.4

Every run used one GB10, with no other model server using the GPU.
- **Release image:** `ghcr.io/enntity/atlas-sparkling:0.1.4`, install tree `c523fbc3852c`, Atlas `ling/3.2-air` at `469d1649b` (Enntity/atlas#46 and #47).
- **Build:** 8,830 engine tests, 0 failures.
- **Launch:** [`harness/rel014.sh`](harness/rel014.sh) started it through `./start.sh up` with the default profile and drafting, then ran the probes. `DRAFTER=none` gave the plain runs. [`harness/queue014.sh`](harness/queue014.sh) ran them, then SparkModelBench.
- **Prefix cache:** the disk tier used a 16 GiB budget, because this Spark's disk was nearly full.

## What changed: long prompts prefill about twice as fast

Up to 0.1.3, SparkLing prefilled a first 8K prompt faster than vLLM, and vLLM led from 32K. An Nsight Systems profile of a 64K prompt showed the time going to attention over the earlier prompt:
- **The kernel.** Ling attended with the engine's shared 64-row prefill kernel at head width 192. In it, half the warps sat idle while the others multiplied queries by keys, scores went through shared memory with two barriers per 32-key tile, and values were padded from 128 to 192 wide. It ran at about 27 TFLOP/s against the GB10's measured 77.5.
- **Re-expansion.** Ling caches a compressed 576-value latent per token. To attend a prompt, Atlas expands that latent back into per-head keys and values. It did so again for every 2,048-row slice of the prompt, so each 8,192-token chunk expanded everything before it four times.

0.1.4 changes both:
- **A 128-row kernel.** Ling's prefill attention is now a port of the FlashAttention-2 layout SparkQwen uses: every warp owns 16 query rows end to end, scores stay in registers, there is one barrier per key tile, and values are multiplied at their true width of 128. On one 8,192-row tile it runs at 62.5 TFLOP/s, 3.5 times the old kernel. Per row it computes the old kernel's bytes exactly (`tests/ling/mla_prefill.cu` in the engine).
- **One expansion per chunk.** Each 8,192-token chunk now attends as one tile, so every layer expands the earlier prompt once per chunk.

SparkModelBench first-request prefill on Ling-3.2-air, tokens per second (thinking on, same Spark; vLLM from 0.1.3's run):

| Prompt | SparkLing 0.1.3 | SparkLing 0.1.4 | vLLM, MTP ×3 |
|---|---:|---:|---:|
| 8K | 3,404 | **3,670** | 3,082 |
| 32K | 2,581 | **3,449** | 2,768 |
| 64K | 1,893 | **3,021** | 2,391 |
| 128K | 1,225 | **2,386** | 1,842 |

A first 128K prompt now waits 54.9 s for its first token instead of 107.0 s; vLLM takes 71.2 s. LingSante-3.1-air-VL prefills within 0.6% of Ling-3.2-air up to its 131,072-token window. On the staggered four-request test, each stream's first token comes at about 18.3 s instead of 21.6 s, and a round ends after 36.9 s instead of 40.6 s.

During development, the kernel alone (keeping 2,048-row slices) measured 62.5 s at 128K and the chunk-wide tile took it to 55.1 s, on the 0.1.3 image with the engine binary swapped ([`prefill-ab`](prefill-ab/), [`harness/pf-ab.sh`](harness/pf-ab.sh)).

## Output

Decode and verify use other kernels, so drafted text still equals plain decoding. Prefill is exact against 0.1.3 up to one chunk, and moves at rounding level beyond it:
- **Up to one 8,200-token chunk:** byte-identical to 0.1.3, logprobs included. Checked on the sixteen probe prompts, Ling prompts of 1,000, 2,634, 4,000 and 8,000 tokens, and LingSante's forced-tool encounter note from the demo.
- **Longer prompts:** 0.1.3 expanded the same key differently for different slices of a chunk, because its projection GEMM rounds by the number of rows it is given. 0.1.4 expands each key once. On fixed 20,000- and 50,000-token prompts the greedy text is unchanged for both models, and the logprobs move slightly. Measured against vLLM's logprobs on the same Ling prompts, the mean difference is 0.0014 for 0.1.4 against 0.0018 for 0.1.3 at 20K, and 0.0019 against 0.0015 at 50K: both builds are as close to vLLM as each other.

The demo caught one regression on the way. The first chunk-wide build also changed how a short prompt was split between projection GEMMs (2,560 + 74 rows instead of 0.1.3's 2,048 + 586). That rounding change was enough to flip LingSante's forced-tool encounter note into an 800-token call the tool guard blocked. Enntity/atlas#47 keeps 0.1.3's projection row counts exactly, and the note is again 0.1.3's 517 tokens, byte for byte ([`prefill-ab/spf3-note.txt`](prefill-ab/spf3-note.txt), [`harness/note_replay.py`](harness/note_replay.py)).

## Release image

| | Ling-3.2-air | LingSante-3.1-air-VL |
| --- | ---: | ---: |
| Context window, tokens | 262,144 | 131,072 |
| Shared KV pool, tokens | 2,157,936 | 2,330,720 |
| Single stream, mean of eight prompts, tok/s | 60.9 | 56.9 |
| Plain decode, mean of eight prompts, tok/s | 44.6 | 43.8 |
| Drafted text equal to plain decode | 8 of 8 | 8 of 8 |
| Drafted text equal to 0.1.3 | 8 of 8 | 8 of 8 |
| First drafts accepted, counting | 100% | 100% |
| Aggregate, 1 / 2 / 4 / 8 clients, tok/s | 60.0 / 77.1 / 82.9 / 104.0 | 58.5 / 73.5 / 78.8 / 102.8 |
| Arithmetic, 30 word problems with thinking on | 30 | 30 |
| Single-tool calls, right tool and argument | 10 of 10 | 10 of 10 |
| Media: red-to-blue clip, counting clip (GIF and MP4), 90 s 720p clip, invoice, grid | all read correctly | all read correctly |
| `bench/draft_decode.py --min-count-accept 0.95` | passed | passed |

The aggregate row is our own probe: eight 256-token prompts, one round. Its numbers vary from run to run with output length. SparkModelBench is the measurement to compare. Ling's pool still holds eight full 262,144-token windows (2,097,152).

[Ling](release/ling-spark-probe.jsonl) · [Ling plain](release/ling-spark-plain.jsonl) · [Ling concurrency](release/ling-spark-conc.jsonl) · [Ling media](release/ling-spark-media.jsonl) · [Ling tasks](release/ling-spark-task.json) · [Ling draft check](release/ling-spark-draft-check.jsonl) · [Ling cache log](release/ling-spark-server-kv.log) · [Air-VL](release/sante-spark-probe.jsonl) · [Air-VL plain](release/sante-spark-plain.jsonl) · [Air-VL concurrency](release/sante-spark-conc.jsonl) · [Air-VL media](release/sante-spark-media.jsonl) · [Air-VL tasks](release/sante-spark-task.json) · [Air-VL draft check](release/sante-spark-draft-check.jsonl) · [Air-VL cache log](release/sante-spark-server-kv.log)

## SparkModelBench

The [v0.1.4 scorecard](../sparkmodelbench-v0.1.4/CARD.md) has every lane for both models, with vLLM's November 26 run on the same Spark. Outside prefill and the staggered four-request test, the numbers match 0.1.3 within run-to-run variance:
- **Generation.** Ling-3.2-air: 49.8 / 49.0 / 54.3 tok/s code / prose / structured (0.1.3: 49.0 / 49.0 / 54.1). LingSante's code median fell from 49.1 to 45.9 because its runs were longer: RigMark decodes greedily, but its five runs of one workload already ranged from 2,170 tokens to the 8,192 cap on 0.1.3, and decode slows as the context deepens.
- **Concurrency.** Ling-3.2-air: 41.9 / 64.7 / 97.1 / 140.6 tok/s at 1 / 2 / 4 / 8 requests (0.1.3: 41.9 / 64.5 / 96.0 / 137.3).
- **Quality.** The same three of four tasks pass for both models; `go-transfer-ledger` times out on every engine.

## LingSante demo

[`demo/lingsante`](../../demo/lingsante/README.md) was recorded again on this image. The 51,349-token chart review now waits 17.4 s for its first token (25.4 s on 0.1.3).
