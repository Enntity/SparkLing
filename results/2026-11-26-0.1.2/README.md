<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# One DGX Spark, November 26, 2026: SparkLing 0.1.2

Every run used one GB10, with no other model server using the GPU. The release image is `ghcr.io/enntity/atlas-sparkling:0.1.2` (index digest `sha256:a86632ff…581f`, install tree `2b64f3eb9763`, Atlas `ling/3.2-air` at `18dec2347`). Its build ran 8,827 engine tests, with 0 failures. [`harness/rel12.sh`](harness/rel12.sh) launched it through `./start.sh up` with the default profile and drafting, then ran the probes. `DRAFTER=none` gave the plain runs. The disk prefix cache used a 16 GiB budget because this Spark's disk was nearly full.

## Release image

| | Ling-3.2-air | LingSante-3.1-air-VL |
| --- | ---: | ---: |
| Context window, tokens | 262,144 | 131,072 |
| Shared KV pool, tokens | 2,221,344 | 2,370,704 |
| Single stream, mean of eight prompts, tok/s | 61.0 | 57.5 |
| Plain decode, mean of eight prompts, tok/s | 44.8 | 44.3 |
| Drafted text equal to plain decode | 8 of 8 | 8 of 8 |
| First drafts accepted, counting | 100% | 100% |
| Aggregate, 1 / 2 / 4 / 8 clients, tok/s | 60.1 / 65.6 / 81.2 / 104.5 | 59.1 / 64.0 / 80.8 / 104.2 |
| Median time to first token, 8 clients | 1.04 s | 1.05 s |
| Arithmetic, 30 word problems with thinking on | 30 | 30 |
| Single-tool calls, right tool and argument | 10 of 10 | 10 of 10 |
| Media: red-to-blue clip, counting clip (GIF and MP4), 90 s 720p clip, invoice, grid | all read correctly | all read correctly |
| `bench/draft_decode.py --min-count-accept 0.95` | passed | passed |

[Ling](release/ling-spark-probe.jsonl) · [Ling plain](release/ling-spark-plain.jsonl) · [Ling concurrency](release/ling-spark-conc.jsonl) · [Ling media](release/ling-spark-media.jsonl) · [Ling tasks](release/ling-spark-task.json) · [Ling draft check](release/ling-spark-draft-check.jsonl) · [Ling cache log](release/ling-spark-server-kv.log) · [Air-VL](release/sante-spark-probe.jsonl) · [Air-VL plain](release/sante-spark-plain.jsonl) · [Air-VL concurrency](release/sante-spark-conc.jsonl) · [Air-VL media](release/sante-spark-media.jsonl) · [Air-VL tasks](release/sante-spark-task.json) · [Air-VL draft check](release/sante-spark-draft-check.jsonl) · [Air-VL cache log](release/sante-spark-server-kv.log)

The acceptance shares come from the engine's `atlas_spec_decode_verify_total` counters, read around each request (the `spec` field of each probe record). The vLLM and llama.cpp comparison runs are unchanged from 0.1.0. [0.1.0 results](../2026-11-25/README.md)

LingSante is now served as `lingsante-3.1-air-vl-atlas` by `./start.sh` as well as by LLooM; 0.1.1's `./start.sh` served it as `lingsante-air-vl`.

## What changed: the predictor's input

0.1.1's drafted streams were faster than plain decoding on every prompt, but counting, prose and code all ran at about the same speed. A one-token drafter should run near its ceiling on counting, where the next word is nearly certain. Atlas's per-request telemetry (`ATLAS_MTP_ACCEPT_DEBUG=1`) showed why: the first draft was accepted 65–74% of the time on every prompt, including counting (73.5%) and Python (65.2%). vLLM, serving the same NVFP4A16 checkpoint with the same predictor layer, accepted 100% of its first drafts on both.

Ling's predictor combines the next token's embedding with the target model's last hidden state. The reference implementation hands it that state after the target's final RMSNorm (`model.norm`), and the predictor then applies its own `hnorm`. Atlas passed the raw residual stream instead. Verify still checked every draft against the full model, so the output stayed exact and only the speed suffered. Atlas 18dec2347 applies `model.norm` before `hnorm`, for drafted tokens and for the prompt and catch-up rows that fill the predictor's cache.

A second defect turned up on the way: after an accepted draft, the predictor's private cache misses the row for that draft's position (the K=2 verify has no counterpart of the K=3 re-feed). Filling it moved acceptance by 0–3 points and left speed unchanged, so 0.1.2 does not include it.

`bench/draft_decode.py --min-count-accept 0.95` now fails a run whose counting stream accepts fewer than 95% of drafts.

| First draft accepted, then tok/s | 0.1.1 | 0.1.2 | vLLM, same predictor |
| --- | --- | --- | --- |
| Ling, counting | 73.5%, 56.7 | 99.2%, 66.0 | 100.0% |
| Ling, Python | 65.2%, 53.1 | 96.6%, 63.9 | 100.0% |
| Ling, Rust | 71.1%, 57.0 | 93.9%, 64.6 | 94.4% |
| Ling, JSON | 42.7%, 46.4 | 84.3%, 61.3 | 89.5% |
| Ling, explanation | 71.9%, 56.6 | 83.8%, 60.4 | 80.2% |
| Ling, essay | 68.2%, 56.1 | 71.6%, 57.2 | 79.5% |
| Ling, story | 70.0%, 57.1 | 72.3%, 57.9 | 67.7% |
| Ling, prose | 67.0%, 55.3 | 71.8%, 57.0 | 65.1% |
| Ling, mean of eight, tok/s | 54.8 | 61.1 | |
| LingSante, counting | 70.0%, 55.0 | 99.2%, 64.3 | |
| LingSante, mean of eight, tok/s | 54.1 | 57.1 | |

These are development runs of the engine binary inside the 0.1.1 image with 0.1.1's launch arguments, read from `ATLAS_MTP_ACCEPT_DEBUG`, so their numbers differ slightly from the release table above. vLLM's column is its first-position acceptance with three drafts, from the 0.1.0 comparison run's `vllm:spec_decode_num_accepted_tokens_per_pos_total` counters. [0.1.1 Ling](raw/acc-ling-base-accept.log) · [0.1.2 Ling](raw/acc-ling-fix-accept.log) · [0.1.1 LingSante](raw/acc-sante-base-accept.log) · [0.1.2 LingSante](raw/acc-sante-fix-accept.log) · [vLLM](../2026-11-25/raw/v-mtp3.jsonl) · [`harness/acc2.sh`](harness/acc2.sh) · [`harness/sl-up.sh`](harness/sl-up.sh)

## Long context and quality

Not rerun. 0.1.2 changes only the draft predictor's input, and drafting is off from two active requests, so 0.1.1's eight-window recall and its quality checks against vLLM and BF16 hold. 0.1.1's decode-at-depth runs used a repetitive log on which drafting accepted few proposals. [0.1.1 results](../2026-11-25-0.1.1/README.md)
