<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<p align="center">
  <img src="docs/assets/banner.png" alt="SparkLing 0.1.3 on one DGX Spark, SparkModelBench with thinking on, tokens per second. Ling-3.2-air: code 49.0, structured 54.1, eight requests 137.3. LingSante-3.1-air-VL: code 49.1, structured 53.1, eight requests 124.4." width="100%">
</p>

# SparkLing

**SparkLing 0.1.3** serves inclusionAI’s **Ling-3.2-air** and **LingSante-3.1-air-VL** on one NVIDIA DGX Spark, each at its full native context: 262,144 tokens for Ling-3.2-air and 131,072 for LingSante-3.1-air-VL, eight requests at a time from one shared cache. The Atlas engine provides an OpenAI-compatible API for text, images, video and tool calls. In its default Spark mode, SparkLing drafts with each model’s native next-token predictor, for up to four requests at once. Every draft is verified with the same arithmetic as plain decoding, so one request’s greedy output is byte-for-byte identical with drafting on or off.

```sh
git clone https://github.com/Enntity/SparkLing.git
cd SparkLing
./start.sh up                                # Ling-3.2-air, Spark mode
./start.sh --model lingsante-3.1-air-vl up   # LingSante-3.1-air-VL, Spark mode
```

The endpoint is `http://127.0.0.1:8897/v1`. The first start downloads and verifies the pinned checkpoint, then pulls the pinned image `ghcr.io/enntity/atlas-sparkling`.

[LLooM](https://github.com/Enntity/lloom) installs either model as a managed runtime behind its gateway, from the same pinned image and weights:

```sh
lloom setup --recipe linux-nvidia-dgx-spark-ling32-air-atlas --additive --apply --yes
lloom setup --recipe linux-nvidia-dgx-spark-lingsante-air-vl-atlas --additive --apply --yes
lloom resume lingsante-3.1-air-vl-atlas --apply --yes   # start it
```

Both recipes were installed and started this way on a DGX Spark on November 25, 2026. The models serve as `ling-3.2-air-atlas` and `lingsante-3.1-air-vl-atlas`. Only one runs at a time, because each needs most of the Spark’s memory.

## LingSante demo

[demo/lingsante](demo/lingsante/README.md) is a one-page demo that calls LingSante live; every patient in it is synthetic. In the run recorded on SparkLing 0.1.3, on one Spark:

- **Chart review.** It read a six-year chart of 51,349 tokens in 25.4 s and named all four planted problems, including a lung nodule never followed up and metformin continued at eGFR 27. A follow-up question about the same chart started answering after 1.9 s, because the chart was still in the cache.
- **Film and labs.** It described a chest radiograph in 3.5 s. Given the radiograph and a lab report together, it filed a structured encounter note as a tool call in 11.7 s.
- **Triage.** It triaged eight emergency patients sent at once, all within 6.8 s.

It is a research demonstration, not medical advice.

> **0.1.3 drafts for several requests at once.** Up to 0.1.2, SparkLing drafted only while a single request was running. 0.1.3 verifies up to four requests’ drafts in one batched pass and drafts them in one predictor pass. On RigMark, short code runs 28% faster at two requests and 24% faster at four for Ling-3.2-air, and 29% and 22% faster for LingSante-3.1-air-VL. One request’s output is byte-identical to 0.1.2. [What changed](results/2026-11-26-0.1.3/README.md#what-changed-several-requests-draft-together)

> **0.1.2 fixes drafting.** In 0.1.1 the drafter got the wrong input: Ling's predictor layer expects the model's last hidden state after its final normalization, and Atlas passed it before. Verify kept the output exact, but only about 70% of drafts were accepted on every prompt, even counting, where vLLM with the same predictor accepts all of them. 0.1.2 accepts 100% on counting, and single-stream decode rises from 54.8 to 61.0 tok/s for Ling-3.2-air and from 54.2 to 57.5 for LingSante-3.1-air-VL. Output is byte-identical to 0.1.1. [What changed](results/2026-11-26-0.1.2/README.md#what-changed-the-predictors-input)

> **Correction to 0.1.0.** SparkLing 0.1.0 advertised a 131,072-token default shared by eight requests. Its KV pool held 56,352 tokens in total, so it could not serve even one 131,072-token request. Atlas cached Ling’s attention as expanded per-head keys and values, 16.6 KB per token per layer. 0.1.1 caches the model’s 576-value compressed latent instead, 1.15 KB per token per layer, and now holds the full window for every request. [0.1.0’s own cache log](results/2026-11-25-0.1.1/raw/010-ling-spark-kv.log)

## Performance

### SparkModelBench scorecard · v0.1.3 on one Spark

We ran the 0.1.3 release image through `./start.sh up` on one DGX Spark on November 26, 2026, with the default profile and drafter, and the pinned vLLM nightly with its MTP drafter (three tokens) on the same Spark, serving the same Ling-3.2-air NVFP4A16 checkpoint with the full 262,144-token window. SparkModelBench pins Alex Ellis’s RigMark and RigMark Quality and selects the workloads and settings. Alex Ellis and OpenFaaS Ltd publish both under the MIT license. Enntity adds the staggered four-request test. [SparkModelBench](https://github.com/enntity/sparkmodelbench) · [RigMark](https://github.com/alexellis/rigmark) · [RigMark Quality](https://github.com/alexellis/rigmark-quality)

SparkModelBench asks for `reasoning_effort: low`. Ling’s template has no effort levels, so its thinking stays on: most of these tokens are thinking.

| RigMark generation, median tok/s | Ling-3.2-air | LingSante-3.1-air-VL | vLLM, MTP ×3 |
|---|---:|---:|---:|
| Code | **49.04** | 49.07 | 42.47 |
| Prose | **49.02** | 43.27 | 37.70 |
| Structured | **54.13** | 53.09 | 41.87 |
| Completion gates, code / prose / structured | 5/5 · 5/5 · 5/5 | 4/5 · 2/5 · 5/5 | 2/5 · 3/5 · 5/5 |

Generation figures are medians of five runs per workload, up to 8,192 tokens each. A run that reaches the cap fails its gate: vLLM reached it on three code runs and two prose runs, and LingSante on one code run and three prose runs.

| RigMark Quality task | Ling-3.2-air | LingSante-3.1-air-VL | vLLM, MTP ×3 |
|---|---|---|---|
| `python-expiry` | Passed, 45.1 s | Passed, 73.4 s | Passed, 31.8 s |
| `go-transfer-ledger` | Timed out at 180 s | Timed out | Timed out |
| `payment-recovery` | Passed, 21.5 s | Passed, 21.1 s | Passed, 16.9 s |
| `evidence-revisions` | Passed, 10.2 s | Passed, 11.1 s | Passed, 7.1 s |

Each quality task ran once. Time includes grading.

**Staggered C4.** Four roughly 16K-token prompts arrived one second apart, thinking off. All streams on both engines reached 400 output tokens. The median time from the first request to the end of a round was **40.61 seconds** for Ling-3.2-air (40.66 for LingSante-3.1-air-VL) against 73.30 for vLLM, 1.80x faster. SparkLing prefills all four prompts before it decodes any of them, so each stream’s first token came about 21.6 s after its request. vLLM answered the first request in 6.5 s and the fourth after 57.8 s.

![SparkLing v0.1.3 and vLLM with MTP on one Spark, Ling-3.2-air. First-request prefill: SparkLing 3,404 tokens/s at 8K, 2,581 at 32K, 1,893 at 64K and 1,225 at 128K; vLLM 3,082, 2,768, 2,391 and 1,842.](results/sparkmodelbench-v0.1.3/prefill.png)

SparkLing prefills a first 8K prompt 1.10x faster than vLLM. From 32K vLLM leads, by 1.07x at 32K, 1.26x at 64K and 1.50x at 128K. LingSante-3.1-air-VL prefills within 0.2% of Ling-3.2-air up to its 131,072-token window. 256K is not run, because the sweep’s 262,144-token prompt plus its output does not fit the window. A prompt sent again starts in 0.013–0.031 s on SparkLing, against 0.7–1.6 s on vLLM.

| RigMark concurrency, short code, aggregate tok/s | 1 | 2 | 4 | 8 |
|---|---:|---:|---:|---:|
| Ling-3.2-air | **41.9** | 64.5 | 96.0 | 137.3 |
| LingSante-3.1-air-VL | 41.5 | 61.6 | 91.4 | 124.4 |
| vLLM, MTP ×3 | 41.5 | **73.1** | **112.2** | **174.3** |

Every one of these 256-token outputs is thinking. SparkLing does not draft inside thinking: Atlas speculates there only for a model whose verify is declared bit-exact, and Ling’s is not yet. vLLM drafts throughout, so it leads from two requests, by 1.13x, 1.17x and 1.27x. The same gap lowers SparkLing’s thinking-on generation figures above. With thinking off (below), SparkLing leads at one, two and four requests.

[Full scorecard](results/sparkmodelbench-v0.1.3/CARD.md) · [result files](results/sparkmodelbench-v0.1.3/)

### RigMark 1.1.0, thinking off

Measured on the 0.1.3 image with [RigMark](https://github.com/alexellis/rigmark) `40fabcaf6e96`, protocol 1.1.0, thinking off (Ling's template has no effort levels), on one Spark with the default profile and drafter, against the pinned vLLM image with and without its MTP drafter on the same Spark: [the result, with every receipt](results/2026-11-26-0.1.3/README.md#rigmark).

| | Ling-3.2-air | LingSante-3.1-air-VL | vLLM, MTP ×3 | vLLM |
|---|---:|---:|---:|---:|
| Code decode, tok/s | **63.0** | 62.4 | 45.4 | 21.6 |
| Prose decode | **54.7** | 49.8 | 32.9 | 21.7 |
| Structured decode | **64.7** | 63.4 | 44.9 | 21.7 |
| 32K cold prefill, tok/s | **2,577** | 2,576 | 2,474 | 2,120 |
| 8K cold prefill | 3,404 | **3,405** | 2,908 | 2,355 |
| Short code, C1 / C2 / C4 / C8 aggregate | **58.1** / 84.9 / **122.6** / 145.2 | 56.0 / **86.0** / 117.8 / 139.6 | 37.3 / 67.3 / 112.4 / **167.5** | 20.9 / 45.2 / 79.7 / 129.4 |
| Short prose, C1 / C4 / C8 aggregate | **50.5 / 95.9** / 114.9 | 47.0 / 91.1 / 115.5 | 29.2 / 82.2 / **125.8** | 21.3 / 75.7 / 119.6 |
| 32K prompt sent again, time to first token | **0.02 s** | 0.02 s | 1.15 s | 0.89 s |
| Longest request | 262,144 | 131,072 | 40,960 as configured | 40,960 as configured |
| Basic output gates | 6/6 | 6/6 | 6/6 | 6/6 |

On Ling-3.2-air, SparkLing leads vLLM with its drafter on:
- code (1.39x), prose (1.66x) and structured output (1.44x);
- cold prefill (1.04x at 32K, 1.17x at 8K);
- one, two and four short-code requests (1.56x, 1.26x, 1.09x);
- four prose requests (1.17x);
- a repeated 32K prompt.

vLLM leads at eight requests: 1.15x on code and 1.09x on prose. SparkLing drafts for up to four live requests and decodes from five plainly. Ling routes each token to 8 of 512 experts, so a verify of eight requests reads nearly twice the expert weights of a plain step for about 1.8 tokens per request, which does not pay on a GB10. The vLLM columns are 0.1.2's runs on the same Spark, serving the same NVFP4A16 checkpoint with a 40,960-token window.

### Eight short prompts, with llama.cpp

SparkLing’s own probe adds llama.cpp and shows each prompt. This table was measured on 0.1.2. 0.1.3 decodes one request with byte-identical text, and on its release run the same probe measured 60.4 tok/s single stream and 60.0 / 78.0 / 85.6 / 104.2 tok/s at 1 / 2 / 4 / 8 clients. All engines ran on the same GB10, one at a time, with nothing else using the GPU. SparkLing’s column is the published `0.1.2` image launched by `./start.sh up` with its 262,144-token window. The other engines ran with an 8,192-token window. The client sent the same request bodies to each engine: eight greedy prompts of 256 tokens each, with thinking off. Decode rate is measured after the first token.

| One GB10 · Ling-3.2-air | SparkLing 0.1.2 | vLLM, MTP ×3 | vLLM | llama.cpp, MTP | llama.cpp |
| --- | ---: | ---: | ---: | ---: | ---: |
| Single stream, mean of eight prompts, tok/s | **61.0** | 40.2 | 21.8 | 50.2 | 37.3 |
| Prompts on which the engine is fastest | **8 of 8** | 0 | 0 | 0 | 0 |
| Aggregate, 1 client, tok/s | **60.1** | 44.6 | 21.6 | 56.5 | 37.4 |
| Aggregate, 2 clients, tok/s | **65.6** | 59.2 | 40.2 | 65.1 | 48.0 |
| Aggregate, 4 clients, tok/s | **81.2** | 68.8 | 62.4 | 62.7 | 67.3 |
| Aggregate, 8 clients, tok/s | 104.5 | **109.2** | 96.4 | 78.8 | 69.5 |

SparkLing ran on November 26, 2026; the other engines on November 25, on the same Spark with the same client. SparkLing and vLLM both served Primitive AI’s NVFP4A16 checkpoint. llama.cpp `b12600` served bartowski’s Q4_K_M GGUF, a different quantization, with all layers on the GPU. The aggregate rows count total generated tokens over wall-clock time, starting from the first request, so they include time to first token. The concurrency rows send the counting prompt with a different suffix to each client.

SparkLing is fastest on all eight prompts, including the predictable ones where llama.cpp drafts several tokens per step: counting, code, JSON and Rust at 66.1, 64.2, 60.9 and 64.7 tok/s against llama.cpp’s 58.4, 57.0, 58.5 and 58.0.

On this probe too, vLLM with MTP leads at eight concurrent requests, by 4%. Atlas also prefills simultaneous prompts one after another rather than in one batch: at eight clients its median time to first token was 1.04 s, against vLLM’s 0.69 s.

[Measurements, commands and raw streams](results/2026-11-26-0.1.2/README.md) · [0.1.3 release run](results/2026-11-26-0.1.3/README.md#release-image) · [0.1.0 comparison runs](results/2026-11-25/README.md)

## Full context, eight at a time

| Default profile, Spark mode | Ling-3.2-air | LingSante-3.1-air-VL |
| --- | ---: | ---: |
| Context window, tokens | 262,144 | 131,072 |
| Shared KV pool, tokens | 2,148,608 (8.2 windows) | 2,374,592 (18 windows) |

- **Eight full windows.** Eight simultaneous 262,132-token prompts, each with different content and its own key word to recall, all returned the right word. They held 2,097,056 prompt tokens together and finished in 45 minutes. Eight 65,524-token prompts took 279 seconds. [8 × 256K](results/2026-11-25-0.1.1/release/r11-long-8x256k.jsonl) · [8 × 64K](results/2026-11-25-0.1.1/release/r11-long-8x64k.jsonl)
- **Decode at depth.** Measured on 0.1.1 with drafting on, 256 tokens after a prompt of 2K, 32K, 128K and 262K tokens decoded at 44.4, 40.6, 34.9 and 27.9 tok/s. 0.1.0 decoded at 3.2 tok/s at 256K, because the old cache forced it to read some experts from disk. [Depth runs](results/2026-11-25-0.1.1/release/ling-spark-depth.jsonl)

Every Spark* memory lever SparkGLM and SparkQwen use is on by default:

- **Compressed cache.** Each token stores one 576-value latent row per attention layer, and keys and values share it.
- **Memory share.** The default profile uses 0.89 of the GB10’s memory, which holds eight full windows with drafting on and leaves the host about 9 GB. `GPU_MEMORY_UTILIZATION` lowers it. `PROFILE=max` uses 0.95 and sixteen request slots.
- **Disk prefix cache.** Evicted cache blocks and KDA recurrent-state snapshots spill to NVMe, 48 GiB under `MODEL_ROOT/prefix-cache`. A later request that shares a prefix resumes from disk instead of prefilling again. `PREFIX_CACHE_GB=0` turns it off, and it turns itself off if the disk lacks room.
- **Display carveout.** The KV cache borrows the GB10’s 2 GiB display carveout when no other Spark* server holds it. It places whole per-layer buffers there. At eight full windows each of Ling’s seven latent buffers is 2.4 GiB, too large to fit, so the default pool gains nothing from it. Smaller pools, such as the `saver` profile’s, do use it. `DISPLAY_CARVEOUT=0` leaves it to the display.

## Exact native drafting

Ling-3.2-air ships one MTP layer. Atlas runs that layer to propose the next token and verifies each proposal together with the current token in one two-row pass. Every row of that pass, including attention over the compressed cache and the FFN, uses the arithmetic single-token decode uses. Drafted greedy text matched plain decode on all eight prompts, at 60.4 tok/s against 44.7. The predictor’s first draft was accepted on 100% of counting steps, 98% for Python and 72–95% elsewhere.

Drafting is on for up to four active requests. Atlas verifies their drafts in one batched pass, each request’s rows against its own cache and recurrent state, and the predictor drafts for all of them in one pass. From five requests Atlas decodes plainly: with 512 routed experts, a verify of eight requests costs about as much as the tokens it gains.

LingSante-3.1-air-VL has no predictor of its own. In Spark mode it borrows Ling-3.2-air’s layer, downloaded with the model. Its drafted text also matched plain decode on all eight prompts, at 57.4 tok/s against 44.2. `DRAFTER=none` turns drafting off for either model.

SparkLing drafts one token per step. A second draft would add a verify row, and a three-row verify costs about 44 ms against 30 ms for two. It would pay off only if the second draft were accepted more than about 90% of the time. On counting, vLLM accepted its second draft from the same predictor 71% of the time. `bench/draft_decode.py --min-count-accept 0.95` checks that a build’s drafter still accepts at least 95% on counting.

## Quality

The compressed cache changes how attention is computed, so 0.1.1 was checked against 0.1.0 and against independent references. 0.1.2 changes only what the draft predictor sees, and 0.1.3 only how several requests draft together. One request’s output from either is byte-identical to 0.1.1 and to plain decoding on all sixteen probe prompts, so these results hold for both.

| GSM8K, first 200 test problems, greedy, thinking off | Ling-3.2-air | LingSante-3.1-air-VL |
| --- | ---: | ---: |
| 0.1.0 | 196 | 193 |
| 0.1.1, as shipped (NVFP4 absorption) | 192 | 192 |
| 0.1.1, BF16 absorption | 193 | 189 |

Builds that differ only in rounding moved by up to four problems, so these differences are within noise.

| Ling-3.2-air next-token distributions against vLLM on the same checkpoint | Top-1 agreement | Mean total variation |
| --- | ---: | ---: |
| Decode, 0.1.0 (772 positions) | 94.2% ± 0.8 | 0.049 ± 0.002 |
| Decode, 0.1.1 as shipped (780 positions) | 95.0% ± 0.8 | 0.050 ± 0.002 |
| Decode, 0.1.1 with BF16 absorption (770 positions) | 94.3% ± 0.8 | 0.050 ± 0.002 |
| Prompt, 0.1.0 (1,183 positions) | 97.4% | 0.036 |
| Prompt, 0.1.1 (1,183 positions) | 97.0% | 0.036 |

The decode rows continue 220 contexts for six greedy tokens and compare each position while the texts still agree. The prompt rows force eight passages of prose, code, JSON, arithmetic, dialogue, Chinese and a list through the engine. On those passages 0.1.0 and 0.1.1 both measure perplexity 3.598, and vLLM 3.613. LingSante-3.1-air-VL, scored against inclusionAI’s original BF16 model on the same 68 forced positions as before, agreed on the top token at 56 of 68 positions in both 0.1.0 and 0.1.1, with the same total variation of 0.090. It returned the same text on all five free continuations. [Quality runs](results/2026-11-25-0.1.1/README.md#quality)

## Models and modes

| `--model` | Spark mode (default) | Strict mode | Context |
| --- | --- | --- | ---: |
| `ling-3.2-air` (default) | Primitive AI NVFP4A16 experts, NVFP4 prefill and attention decode, native drafting | inclusionAI’s original dynamic FP8, checkpoint precision | 262,144 tokens |
| `lingsante-3.1-air-vl` | Enntity NVFP4 from inclusionAI’s BF16, NVFP4 prefill and attention decode, Ling’s drafter | inclusionAI’s original BF16 | 131,072 tokens |

Ling-3.2-air is a 124B mixture-of-experts model with 5.5B parameters active per token. It has 35 KDA linear-attention layers, 7 gated-MLA layers and 512 routed experts, of which 8 are active per token. LingSante-3.1-air-VL is inclusionAI’s medical vision-language model on the same backbone. `./start.sh` and LLooM both serve them as `ling-3.2-air-atlas` and `lingsante-3.1-air-vl-atlas`. Set the model with `--model` or `SPARKLING_MODEL` in `.env`; the earlier `sante-air-vl` and `MODEL=` still work.

**Strict mode** serves the original checkpoints for reference. Ling’s FP8 weights are 120.4 GiB, and Air-VL’s BF16 weights are 232.55 GiB. Neither fits in memory, so Strict pages experts from disk and decodes at about 2 tokens per second. Strict’s KV pool stops at eight full windows (15.8 GB at 262K), so the rest of memory can cache the experts it reads from disk. With no limit the pool took 68 GB and Strict slowed to 0.3 tok/s. Use Spark mode for speed. [Strict runs](results/2026-11-25-0.1.1/README.md#strict-mode)

## Input

- **Text and tools.** Tool calls use Ling’s template and parser. The tool guard is on by default and blocks calls to metadata addresses and calls that send credentials. A blocked call ends the response with `content_filter`. In streamed LingSante responses tested on November 25, a tool call’s arguments arrived in one piece once the call was complete, even with `stream_tool_arguments` set.
- **Images.** Send `image_url` parts as base64 data URIs.
- **Video.** Send `video_url` parts. GIF is decoded in process; MP4, MOV, WebM and AVI are decoded by the ffmpeg in the image.
  - Sampling follows inclusionAI’s processor: at most 2 frames per second and 32 frames, with one frame size chosen from a 4.7-megapixel budget.
  - Requests may be up to 256 MiB. A 90-second 720p H.264 clip is about 47 MB as a data URI and answered in 6.6 s.
- **Checks on one Spark.**
  - A counting clip (the numbers 1 to 8) was read back in order, as GIF and as MP4.
  - A red-to-blue clip, an invoice and a labelled grid were read correctly.
  - [Media checks](results/2026-11-25/raw/video3.jsonl)

## Precision, sampling and caching

In Spark mode, `PREFILL_PRECISION=nvfp4` quantizes routed-expert activations for large prompt batches. `DECODE_PRECISION=nvfp4` quantizes the large attention projections at load time, including the two halves of `kv_b_proj` that decode applies to the compressed cache, and keeps the published BF16 vocabulary head. Set either to `checkpoint` to follow the checkpoint’s own precision. Strict uses the published sampling settings; Spark uses Atlas’s sampling defaults, including min-p 0.08 and top-n-sigma 1.0, unless the request overrides them. The disk prefix cache uses a separate directory for each precision. [Launcher settings](.env.example)

Use `./start.sh status`, `./start.sh logs` and `./start.sh stop` to manage the server, and `./start.sh --version` to print the product version and engine revision. `./start.sh download` and `./start.sh verify` stage a checkpoint ahead of time. Each snapshot has its own immutable revision directory under `MODEL_ROOT` (default `~/models/sparkling`).

## Reproduce

[results/2026-11-26-0.1.3](results/2026-11-26-0.1.3/README.md), [results/2026-11-26-0.1.2](results/2026-11-26-0.1.2/README.md) and [results/2026-11-25-0.1.1](results/2026-11-25-0.1.1/README.md) list the scripts and commands behind every number above. The reference launchers pin the vLLM and SGLang images. [Benchmark instructions](docs/REPRODUCE.md) · [Functional checks](bench/README.md) · [Reference launchers](reference/README.md) · [Earlier results](results/README.md)

## Engine and license

SparkLing contains the launcher, profiles and benchmarks; the implementation lives in Atlas. The install manifest pins the exact engine commit and source tree. SparkLing and Atlas are AGPL-3.0-only. Ling-3.2-air, LingSante-3.1-air-VL, Primitive AI’s NVFP4A16 and Enntity’s NVFP4 weights are MIT. [Engine pin](install/atlas-source.json) · [Upstream Atlas PR](https://github.com/Atlas-Inf/atlas/pull/411) · [License](LICENSE) · [Notices](NOTICE)
