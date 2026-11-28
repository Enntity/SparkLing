<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# One DGX Spark, November 27, 2026: SparkLing 0.1.5

Every Ling-3.2-air run used one clean GB10 (`ennspark04`, 111 GiB free, no co-tenants) with the default 262,144-token Spark profile.
- **Engine pin:** Atlas `ling/3.2-air` at `f9d0ebf95` (Enntity/atlas#48).
- **Launcher changes:** native `mtp` now launches with `--num-drafts=2`, `ATLAS_MTP_K_LADDER=1:2,4:1,8:1` and `ATLAS_MTP_MAX_SEQS=8` (`ling-mtp` stays at `--num-drafts=1` with `ATLAS_MTP_MAX_SEQS=8`); `SPARKLING_GPU_MEMORY_UTILIZATION` accepts up to `0.95` to match `profiles/max.json`; NVFP4 prefill raises any `--max-prefill-tokens` value below `8192` instead of matching only `2048`.

## What changed

1. **Speculative decoding stays active inside `<think>` blocks.** Atlas gates speculation during reasoning on `verify_bit_exact` and `batch_verify_bit_exact`. Ling's verify already used serial decode's arithmetic, but did not declare those flags, so every thinking token fell back to plain decode. Declaring them immediately unlocked drafting across all reasoning workloads.
2. **Two-draft chained MTP at C1, stepping down to one draft at C2–C8.** Atlas previously rejected `--num-drafts > 1` on Ling and capped batched drafting at 4 requests. Ling now chains up to 3 drafts (feeding the predictor's post-norm residual into the next step), supports uniform and ragged `ks` batched KDA/MLA verify in `2..=4` rows/seq (eliminating serial fallbacks on ragged batches), captures K=3 single-sequence and batched K=2 CUDA graphs, and reports K=3 accept/reject counters to Prometheus. On GB10, `num_drafts=2` with `ATLAS_MTP_K_LADDER=1:2,4:1,8:1` was fastest (64% accept-2 and 24% accept-1 on C1 = 2.52 tokens/step); `num_drafts=3` was slower (~56.8 tok/s) because third-draft acceptance did not cover the extra routed-expert reads.
3. **Kernel dispatch and ABI fixes.** Restored 9–32-row NVFP4 decode/verify tiers (keeping cuBLASLt BF16 GEMM above 8 rows), lowered `grouped_a16_prefill` from 128 to 33 rows to remove the 33–127-row MoE dead zone, and fixed a 7-arg vs. 8-arg ABI mismatch in batched MTP `w4a16_gemv_batch2`/`batch3` dispatch.

## SparkModelBench (Ling-3.2-air, thinking on)

Measured on `ennspark04` with the same `293a44f` suite and 180-second task budget used for 0.1.4 and vLLM:

| Workload | SparkLing 0.1.4 | SparkLing 0.1.5 | vLLM, MTP ×3 |
|---|---:|---:|---:|
| Generation · code, tok/s | 49.80 | **66.15** | 42.47 |
| Generation · prose, tok/s | 49.02 | **57.10** | 37.70 |
| Generation · structured, tok/s | 54.28 | **67.14** | 41.87 |
| Generation gates (code / prose / structured) | 5/5 · 5/5 · 5/5 | **5/5 · 5/5 · 5/5** | 2/5 · 3/5 · 5/5 |
| Concurrency C1 / C2 / C4 / C8 aggregate, tok/s | 41.9 / 64.7 / 97.1 / 140.6 | **56.5 / 84.4 / 125.8** / 141.5 | 41.5 / 73.1 / 112.2 / **174.3** |
| Staggered C4 wall (4×16K, 400 tok, thinking off) | 36.89 s | **36.71 s** | 73.30 s |
| Cold prefill 8K / 32K / 64K / 128K, tok/s | 3,670 / 3,449 / 3,021 / 2,386 | **3,730 / 3,476 / 3,042 / 2,408** | 3,082 / 2,768 / 2,391 / 1,842 |
| RigMark Quality `python-expiry` / `payment-recovery` / `evidence-revisions` | 44.3 / 20.5 / 10.1 s | **36.9 / 17.6 / 7.9 s** | 31.8 / 16.9 / 7.1 s |

`go-transfer-ledger` still timed out at 180 s (elapsed 195.3 s, 9,452 output tokens across 5 steps: it wrote both `transfer.go` and `transfer_test.go`, ran `run_tests`, and ran out of time fixing a 1-line `int` vs `int64` assertion in its test helper). `bench/sparkmodelbench` now pins `2b9ce8c` (`task_seconds: 300`) so future runs give multi-step tasks room to finish.

vLLM still leads at eight concurrent requests (174.3 vs 141.5 tok/s) because Atlas prefills the eight short prompts serially (1.38 s vs 0.53 s median TTFT) and uses an unfused N=16 `ling_expert_mma` kernel at 16–32 rows instead of a fused pipelined grouped W4A16 MoE kernel.

## Functional checks

- **Ling-3.2-air:**
  - `bench/draft_decode.py --min-count-accept 0.95`: passed (`count` 100.0% accept at 73.1 tok/s, `code` 95.2% at 73.6 tok/s, `prose` 68.8% at 50.3 tok/s) — [ling-spark-draft-check.jsonl](release/ling-spark-draft-check.jsonl)
  - `bench/task_probe.py`: 30/30 arithmetic, 10/10 tool calls — [ling-spark-task.json](release/ling-spark-task.json)
  - Eight-probe A/B sweep (thinking off / on): 62.54 / 60.46 tok/s mean (0.1.4 on the same host: 61.21 / 47.91 tok/s) — [ling-spark-ab.json](release/ling-spark-ab.json)
- **LingSante-3.1-air-VL** (measured on `ghcr.io/enntity/atlas-sparkling:0.1.5`, November 28, 2026):
  - `bench/draft_decode.py --model lingsante-3.1-air-vl-atlas --min-count-accept 0.95`: passed (`count` 100.0% accept at 63.2 tok/s, `code` 96.9% at 61.8 tok/s, `prose` 55.0% at 50.2 tok/s) — [sante-spark-draft-check.jsonl](release/sante-spark-draft-check.jsonl)
  - `bench/task_probe.py`: 30/30 arithmetic, 10/10 tool calls — [sante-spark-task.json](release/sante-spark-task.json)
  - SparkModelBench (`2b9ce8c`, 300 s quality budget): generation **60.78 / 56.77 / 60.32 tok/s** (code 5/5, prose 3/5, structured 5/5; up from 45.93 / 44.59 / 53.15 on 0.1.4); concurrency **53.4 / 79.5 / 104.3 / 129.4 tok/s** at C1/C2/C4/C8 (up from 41.2 / 61.6 / 86.9 / 122.8); cold prefill **3,712 / 3,468 / 3,042 tok/s** at 8K/32K/64K; staggered C4 **36.61 s**; RigMark Quality `python-expiry` 48.0 s, `payment-recovery` 19.2 s, `evidence-revisions` 12.8 s (full scorecard in [v0.1.5 CARD.md](../sparkmodelbench-v0.1.5/CARD.md)).
