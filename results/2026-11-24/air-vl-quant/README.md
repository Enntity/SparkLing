# LingSante Air-VL on one GB10

SparkLing converted inclusionAI’s original BF16 routed experts to NVFP4 and compared them with inclusionAI’s MXFP4 release. The two weight formats use different groups and scales. NVFP4 uses E2M1 values in groups of 16 with E4M3 group scales and a global scale for each matrix. The published MXFP4 uses groups of 32 with E8M0 scales. The NVFP4 checkpoint preserves the original vision tower, router, shared experts, vocabulary head, tokenizer and processor. The optional fast profiles quantize additional projections in memory.

The derived files occupy 70.88 GiB. The manifest records the size and SHA-256 of each inference file. Run `./start.sh --model sante-air-vl --mode spark --quant nvfp4 verify` to check a staged copy. [Checkpoint manifest](../../../install/checkpoint-sante-nvfp4.json) · [Conversion](../../../install/quantize_sante.py)

## Decode

Each run used one client, 4,096 tokens of context, BF16 KV, thinking disabled, temperature zero, and the same 64-token counting request. The client measures the 63 token intervals after the first token. Rates on different checkpoints include the effects of both the engine and the precision selection.

| Engine and weights | First run, tok/s | Second run, tok/s |
| --- | ---: | ---: |
| SGLang, publisher MXFP4, original comparison | 28.37 | 27.59 |
| SGLang, publisher MXFP4, fresh run | 29.22 | 30.12 |
| Atlas, publisher MXFP4, original comparison | 10.47 | 10.48 |
| Atlas, publisher MXFP4, vectorized expert kernel | 30.26 | 30.31 |
| Atlas, BF16-derived NVFP4 routed experts only | 27.20 | 27.20 |
| Atlas, derived NVFP4 with fast attention and BF16 vocabulary head | 43.94 | 43.98 |
| Atlas, derived NVFP4 with fast attention, MLPs and NVFP4 vocabulary head | 54.07 | 54.98 |
| Same MLPs with FP8 vocabulary head | 52.62 | 52.70 |

The publisher-weight speedup came from the routed expert GEMV. It occupied 78% of profiled kernel time before vectorization. The NVFP4 weight format by itself measured slower than optimized MXFP4. The additional gains came from reducing the bytes read by attention, shared and dense MLPs, and the vocabulary head. All four Atlas configurations returned `391` for 17 × 23 and `Blue` for the image.

[Original reference streams](../sante-ref-speed.jsonl) · [MXFP4 kernel profile](mx-baseline-kernels.csv) · [Kernel check](mx-kernel-check.log) · [MXFP4 streams](mx-speed.jsonl) · [NVFP4 weight-only streams](nv-speed.jsonl) · [BF16-head streams](nv-fast-speed.jsonl) · [NVFP4-head streams](mlp4-speed.jsonl)

## Accuracy against original BF16

The offline expert probe compared the stored matrices, with 32 seeded Gaussian activation vectors for each of 15 experts in five layers. The energy-weighted relative output error was **0.1652 for NVFP4** and **0.2002 for MXFP4**. All 15 experts favored NVFP4. The test also checked that the shipped quantizer reproduced the packed values, group scales and global scale of a stored matrix byte for byte. [Expert samples](stored-expert-errors.json) · [Reproduction check](recipe-parity.json)

The serving check compares one-token completions on five synthetic prompts and 68 teacher-forced positions in a synthetic accession log. The BF16-head fast NVFP4 profile agreed with BF16 on all five free choices and 56/68 passage positions. Published MXFP4 agreed on four and 56/68. The fast NVFP4-head profile agreed on five and 57/68. Distribution distance uses only top-five tokens common to all compared profiles at each position and one bin for the remaining probability. It is a lower bound on full-vocabulary total variation. These probes measure numerical fidelity on the supplied inputs. Clinical accuracy requires a separate evaluation. [BF16 completions](bf16-quality.jsonl) · [BF16 passage](bf16-teacher.jsonl) · [Scoring program](../../../bench/score_sante.py)

## Roofline

The fixed decode target was twice the original publisher-MXFP4 SGLang mean, **55.96 tok/s**. At this Spark’s measured 244.8 GB/s streaming bandwidth, that allows about **4.37 GB per token**. The original MXFP4 active weight estimate is 4.72 GB, before KV and state traffic. For the derived checkpoint, active routed weights are 8/512 of 67.95 GB. Adding non-routed weights and the target head gives about 7.49 GB per token for weight-only NVFP4, 4.01 GB with fast attention, and 2.96 GB with the fast MLP and head profile. Their idealized streaming ceilings are about **32.7, 61.1 and 82.8 tok/s**. They exclude cache hits, extra weight reads, state traffic, arithmetic and launch overhead.

For 2,048 prompt tokens, the active projections require roughly 9.40 GFLOP/token. A dense BF16 multiply on this Spark sustained 77.55 TFLOP/s, giving a projection-only ceiling near 8,250 tok/s. Touching all experts once in a chunk would read about 73.6 GB, or close to 6,810 tok/s at the measured copy bandwidth. The actual fast NVFP4-head runs took 0.835 and 0.829 seconds to return one token from cold 2,048-token prompts, about **2,460 input tok/s** end to end. [Checkpoint bytes](weight-bytes.json) · [Cold prompts](mlp4-prefill.jsonl) · [Hardware measurements](../../2026-11-23/roofline.md)


A fresh SGLang MXFP4 run on the identical counting request averaged **29.67 tok/s**, moving the 2× bar to **59.35 tok/s**. The same two distinct, uncached 2,048-token inputs took SGLang **32.98 s and 0.671 s**. Using the second shape-warm, content-cold result as the reference gives **3,052 input tok/s** and a 2× prefill target of roughly **6,104 tok/s**. It fits the projection and idealized streaming ceilings, with limited bandwidth headroom. Atlas reached roughly **0.81×** SGLang on that second prompt. The first SGLang observation is included separately because averaging the two would hide the startup cost. [Fresh SGLang streams](sglang-speed.jsonl) · [Fresh SGLang cold prompts](sglang-prefill.jsonl)

Across all five Atlas profiles on the same probability bins, the mean coarsened total variation from BF16 was 0.1026 for publisher MXFP4, 0.0876 for weight-only NVFP4, 0.0862 for the fast BF16 head and 0.0911 for the fastest NVFP4 head. The FP8-head variant scored 0.0841 and matched 55/68 passage choices and 4/5 free choices. [Distribution summary](distribution-summary.json)
