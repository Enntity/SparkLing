<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# One DGX Spark, November 25, 2026: SparkLing 0.1.0

Every run used one GB10, one engine at a time, with nothing else using the GPU. The same client sent the same request bodies to every engine. [`harness/probe.py`](harness/probe.py) sends eight greedy prompts (temperature 0, seed 31, thinking off, 256 tokens), and its decode rate is measured after the first token. [`harness/conc.py`](harness/conc.py) sends 1, 2, 4 and 8 simultaneous requests, and its aggregate is total generated tokens over wall-clock time.

## Release image

The published image `ghcr.io/enntity/atlas-sparkling:0.1.0` (digest `sha256:7f8c9351…`, install tree `a66a1e6464f4`, Atlas `dc0035de5`) ran 8,827 engine tests in its build, with 0 failures. [`harness/release-check.sh`](harness/release-check.sh) launched it through `./start.sh up`, using the default profile, the 131,072-token window and default drafting.

| | Ling-3.2-air | LingSante-3.1-air-VL |
| --- | ---: | ---: |
| Single stream, mean of eight prompts, tok/s | 55.2 | 53.9 |
| Drafted text equal to plain decode | 8 of 8 | 8 of 8 |
| Aggregate, 1 / 2 / 4 / 8 clients, tok/s | 54.6 / 61.1 / 77.3 / 104.0 | 48.0 / 62.3 / 79.0 / 105.2 |
| Median time to first token, 8 clients | 1.03 s | 1.06 s |
| Arithmetic, 30 word problems with thinking on | 29 | 30 |
| Single-tool calls, right tool and argument | 10 of 10 | 10 of 10 |
| Media: red-to-blue clip, counting clip (GIF and MP4), 90 s 720p clip, invoice, grid | all read correctly | all read correctly |

On Ling, the red-to-blue answers were `Red Blue`. The media script marks them failed because it matches lowercase only; the answers themselves are right. [Ling](release/ling-spark-probe.jsonl) · [Ling concurrency](release/ling-spark-conc.jsonl) · [Ling media](release/ling-spark-media.jsonl) · [Ling tasks](release/ling-spark-task.json) · [Air-VL](release/sante-spark-probe.jsonl) · [Air-VL concurrency](release/sante-spark-conc.jsonl) · [Air-VL media](release/sante-spark-media.jsonl) · [Air-VL tasks](release/sante-spark-task.json)

## Against vLLM and llama.cpp

SparkLing's column is the release image above. The decision runs below used a development binary of the same engine commit, with the default profile's settings but an 8,192-token window; they are within 3% of the release image.

| Ling-3.2-air, tok/s | SparkLing | vLLM, MTP ×3 | vLLM | llama.cpp, MTP | llama.cpp |
| --- | ---: | ---: | ---: | ---: | ---: |
| Counting | 56.9 | 46.8 | 21.8 | **58.4** | 38.0 |
| Prose | **55.4** | 30.8 | 21.6 | 43.7 | 36.4 |
| Python | 54.2 | 46.3 | 21.8 | **57.0** | 36.7 |
| Story | **56.6** | 30.8 | 21.8 | 39.6 | 36.8 |
| Explanation | **57.2** | 40.0 | 21.8 | 47.6 | 37.2 |
| JSON | 45.5 | 46.4 | 21.8 | **58.5** | 38.0 |
| Rust | **58.6** | 44.2 | 21.8 | 58.0 | 37.7 |
| Essay | **57.1** | 35.8 | 21.8 | 38.6 | 37.4 |
| Mean | **55.2** | 40.2 | 21.8 | 50.2 | 37.3 |
| Aggregate, 1 / 2 / 4 / 8 clients | 54.6 / 61.1 / **77.3** / 104.0 | 44.6 / 59.2 / 68.8 / **109.2** | 21.6 / 40.2 / 62.4 / 96.4 | **56.5** / **65.1** / 62.7 / 78.8 | 37.4 / 48.0 / 67.3 / 69.5 |

- **vLLM.** The reference launcher's pinned `vllm-openai:cu134-nightly-a2bcb5657` arm64 image, serving Primitive AI's NVFP4A16 at revision `3a78e58` with TP 1 and an 8,192-token window. One run used the publisher's `{"method":"mtp","num_speculative_tokens":3}`, one ran without speculation. vLLM uses Marlin weight-only FP4 on GB10. Its mean MTP acceptance length was 2.19. [`harness/comp-vllm.sh`](harness/comp-vllm.sh)
- **llama.cpp.** Release `b12600`, built for CUDA sm_121, serving bartowski's `Ling-3.2-air-Q4_K_M` (80.4 GB) with all layers on the GPU, flash attention, the Jinja template and 8 slots. One run used `--spec-type draft-mtp`, one ran without. It drafts several tokens per step (mean length about 2.8). [`harness/llama-build.sh`](harness/llama-build.sh) · [`harness/comp-llama.sh`](harness/comp-llama.sh)
- **SparkLing.** Drafts one token per step for one active request, and plain-decodes from two active requests. [`harness/serve-probe.sh`](harness/serve-probe.sh)
- **SGLang.** The publisher-recommended image (`7d0d0644`) was killed for running out of memory while loading Primitive AI's NVFP4A16 at a memory fraction of 0.85. [`harness/comp-sglang.sh`](harness/comp-sglang.sh)

Raw streams: [SparkLing drafted](raw/b6-mtp.jsonl) · [SparkLing plain](raw/b6-off.jsonl) · [SparkLing concurrency](raw/c8-mtp-cap1.jsonl) · [vLLM MTP](raw/v-mtp3.jsonl) · [vLLM MTP concurrency](raw/v-mtp3-conc.jsonl) · [vLLM](raw/v-off.jsonl) · [vLLM concurrency](raw/v-off-conc.jsonl) · [llama.cpp MTP](raw/l-mtp.jsonl) · [llama.cpp MTP concurrency](raw/l-mtp-conc.jsonl) · [llama.cpp](raw/l-off.jsonl) · [llama.cpp concurrency](raw/l-off-conc.jsonl)

## Decisions

- **Exact drafting.** With Atlas `ling/3.2-air` at `144e10776`, drafted text diverged from plain decode on 6 of 8 prompts. Running only the verify's FFN one row at a time made every prompt match; batched KDA, MLA and the vocabulary head already matched. The single-token FFN rounded the routed sum to BF16 before adding the shared expert, while the batched blend added it in FP32. Serial decode now runs its FFN as one row of the batched path. [Before](raw/b1-mtp.jsonl) · [Serial FFN](raw/b2-sffn.jsonl) · [After](raw/b6-mtp.jsonl)
- **One draft per step.** A two-token draft also stayed exact. Its second draft was accepted only 18–25% of the time after an accepted first, and a three-row verify cost about 44 ms against 30 ms for two rows, so it ran at 42.2 tok/s. [Two drafts](raw/b9-d2.jsonl)
- **Drafting for one active request.** Ling layers have no multi-sequence verify. Verifying two or more requests in turn was slower than batched plain decode (55.6 / 68.5 tok/s against 60.3 / 74.9 at 2 / 4 clients), so the launcher sets `ATLAS_MTP_MAX_SEQS=1`. [Per-request verify](raw/c8-mtp-perseq.jsonl) · [One drafting request](raw/c8-mtp-cap1.jsonl)
- **The 131,072-token default.** At 262,144 tokens the BF16 KV pool (28.4 GiB) and the weights do not fit together. One stream decoded 11.4 tok/s at 0.80 GPU memory utilization and 6.2 at 0.88. At 131,072 tokens it decoded 54.9 with the same text. [256K at 0.80](raw/l256-0.80.jsonl) · [256K at 0.88](raw/l256-0.88.jsonl) · [128K](raw/l128.jsonl)
- **Air-VL drafting.** With Ling's borrowed predictor, drafted text matched plain decode 8 of 8, at 53.7 tok/s against 43.1 (NVFP4 prefill and attention decode). At checkpoint precision it ran at 37.3 against 26.7. [Fast plain](raw/avf-off.jsonl) · [Fast drafted](raw/avf-mtp.jsonl) · [Checkpoint plain](raw/av-off.jsonl) · [Checkpoint drafted](raw/av-mtp.jsonl)
- **Video.** Ling's template wraps a clip in `video_start` and `video_end`, which the expander did not match, so every GIF was refused. A 32-frame 720p clip also exceeded the vision encoder's 4,096-row window, so encoding now runs in passes. [Media checks](raw/video3.jsonl) · [`harness/video_probe.py`](harness/video_probe.py) · [`harness/make_videos.sh`](harness/make_videos.sh)
