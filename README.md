<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<p align="center">
  <img src="docs/assets/banner.png" alt="SparkLing 0.1.1 on one DGX Spark, single-stream decode with exact native drafting at eight full context windows. Counting, prose and Python: Ling-3.2-air 56.7, 55.2 and 53.3 tokens/s; LingSante-3.1-air-VL 55.2, 50.9 and 54.6 tokens/s." width="100%">
</p>

# SparkLing

**SparkLing 0.1.1** serves inclusionAI’s **Ling-3.2-air** and **LingSante-3.1-air-VL** on one NVIDIA DGX Spark, each at its full native context: 262,144 tokens for Ling-3.2-air and 131,072 for LingSante-3.1-air-VL, eight requests at a time from one shared cache. The Atlas engine provides an OpenAI-compatible API for text, images, video and tool calls. In its default Spark mode, SparkLing drafts with each model’s native next-token predictor. Every draft is verified with the same arithmetic as plain decoding, so greedy output is byte-for-byte identical with drafting on or off.

```sh
git clone https://github.com/Enntity/SparkLing.git
cd SparkLing
./start.sh up                          # Ling-3.2-air, Spark mode
./start.sh --model sante-air-vl up     # LingSante-3.1-air-VL, Spark mode
```

The endpoint is `http://127.0.0.1:8897/v1`. The first start downloads and verifies the pinned checkpoint, then pulls the pinned image `ghcr.io/enntity/atlas-sparkling`.

> **Correction to 0.1.0.** SparkLing 0.1.0 advertised a 131,072-token default shared by eight requests. Its KV pool held 56,352 tokens in total, so it could not serve even one 131,072-token request. Atlas cached Ling’s attention as expanded per-head keys and values, 16.6 KB per token per layer. 0.1.1 caches the model’s 576-value compressed latent instead, 1.15 KB per token per layer, and now holds the full window for every request. [0.1.0’s own cache log](results/2026-11-25-0.1.1/raw/010-ling-spark-kv.log)

## Speed on one Spark

All engines below ran on the same GB10, one at a time, with nothing else using the GPU. SparkLing’s column is the published `0.1.1` image launched by `./start.sh up` with its 262,144-token window. The other engines ran with an 8,192-token window. The client sent the same request bodies to each engine: eight greedy prompts of 256 tokens each, with thinking off. Decode rate is measured after the first token.

| November 25, 2026 · one GB10 · Ling-3.2-air | SparkLing 0.1.1 | vLLM, MTP ×3 | vLLM | llama.cpp, MTP | llama.cpp |
| --- | ---: | ---: | ---: | ---: | ---: |
| Single stream, mean of eight prompts, tok/s | **54.8** | 40.2 | 21.8 | 50.2 | 37.3 |
| Prompts on which the engine is fastest | **4 of 8** | 0 | 0 | **4 of 8** | 0 |
| Aggregate, 1 client, tok/s | 54.6 | 44.6 | 21.6 | **56.5** | 37.4 |
| Aggregate, 2 clients, tok/s | **65.7** | 59.2 | 40.2 | 65.1 | 48.0 |
| Aggregate, 4 clients, tok/s | **81.1** | 68.8 | 62.4 | 62.7 | 67.3 |
| Aggregate, 8 clients, tok/s | 104.4 | **109.2** | 96.4 | 78.8 | 69.5 |

SparkLing and vLLM both served Primitive AI’s NVFP4A16 checkpoint. llama.cpp `b12600` served bartowski’s Q4_K_M GGUF, a different quantization, with all layers on the GPU. The aggregate rows count total generated tokens over wall-clock time, starting from the first request, so they include time to first token. The concurrency rows send the counting prompt with a different suffix to each client.

Where SparkLing is not fastest:

- **Highly predictable text.** llama.cpp leads on counting, code, JSON and Rust: 58.4, 57.0, 58.5 and 58.0 tok/s against SparkLing’s 56.7, 53.3, 46.2 and 56.9. llama.cpp drafts several tokens per step, about 2.8 per step here. SparkLing drafts one, because Ling’s single predictor layer is trained to predict one step ahead. A two-token SparkLing draft stayed exact, but the second draft was accepted only 18–25% of the time and the run was slower overall, at 42.2 tok/s. [Two-draft run](results/2026-11-25/raw/b9-d2.jsonl)
- **Eight concurrent requests.** vLLM with MTP leads by 5%. Atlas prefills simultaneous prompts one after another rather than in one batch. At eight clients its median time to first token was 1.04 s, against vLLM’s 0.69 s.

[Measurements, commands and raw streams](results/2026-11-25-0.1.1/README.md) · [0.1.0 comparison runs](results/2026-11-25/README.md)

## Full context, eight at a time

| Default profile, Spark mode | Ling-3.2-air | LingSante-3.1-air-VL |
| --- | ---: | ---: |
| Context window, tokens | 262,144 | 131,072 |
| Shared KV pool, tokens | 2,200,304 (8.4 windows) | 2,377,344 (18 windows) |

- **Eight full windows.** Eight simultaneous 262,132-token prompts, each with different content and its own key word to recall, all returned the right word. They held 2,097,056 prompt tokens together and finished in 45 minutes. Eight 65,524-token prompts took 279 seconds. [8 × 256K](results/2026-11-25-0.1.1/release/r11-long-8x256k.jsonl) · [8 × 64K](results/2026-11-25-0.1.1/release/r11-long-8x64k.jsonl)
- **Decode at depth.** With drafting on, 256 tokens after a prompt of 2K, 32K, 128K and 262K tokens decoded at 44.4, 40.6, 34.9 and 27.9 tok/s. 0.1.0 decoded at 3.2 tok/s at 256K, because the old cache forced it to read some experts from disk. [Depth runs](results/2026-11-25-0.1.1/release/ling-spark-depth.jsonl)

Every Spark* memory lever SparkGLM and SparkQwen use is on by default:

- **Compressed cache.** Each token stores one 576-value latent row per attention layer, and keys and values share it.
- **Memory share.** The default profile uses 0.89 of the GB10’s memory, which holds eight full windows with drafting on and leaves the host about 9 GB. `GPU_MEMORY_UTILIZATION` lowers it. `PROFILE=max` uses 0.95 and sixteen request slots.
- **Disk prefix cache.** Evicted cache blocks and KDA recurrent-state snapshots spill to NVMe, 48 GiB under `MODEL_ROOT/prefix-cache`. A later request that shares a prefix resumes from disk instead of prefilling again. `PREFIX_CACHE_GB=0` turns it off, and it turns itself off if the disk lacks room.
- **Display carveout.** The KV cache borrows the GB10’s 2 GiB display carveout when no other Spark* server holds it. It places whole per-layer buffers there. At eight full windows each of Ling’s seven latent buffers is 2.4 GiB, too large to fit, so the default pool gains nothing from it. Smaller pools, such as the `saver` profile’s, do use it. `DISPLAY_CARVEOUT=0` leaves it to the display.

## Exact native drafting

Ling-3.2-air ships one MTP layer. Atlas runs that layer to propose the next token and verifies each proposal together with the current token in one two-row pass. Every row of that pass, including attention over the compressed cache and the FFN, uses the arithmetic single-token decode uses. Drafted greedy text matched plain decode on all eight prompts, at 54.8 tok/s against 44.6. Drafting is on for one active request. From two requests, Atlas switches to batched plain decoding, which is faster here than verifying requests in turn.

LingSante-3.1-air-VL has no predictor of its own. In Spark mode it borrows Ling-3.2-air’s layer, downloaded with the model. Its drafted text also matched plain decode on all eight prompts, at 54.2 tok/s against 44.1. `DRAFTER=none` turns drafting off for either model.

## Quality

The compressed cache changes how attention is computed, so 0.1.1 was checked against 0.1.0 and against independent references.

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
| `sante-air-vl` | Enntity NVFP4 from inclusionAI’s BF16, NVFP4 prefill and attention decode, Ling’s drafter | inclusionAI’s original BF16 | 131,072 tokens |

Ling-3.2-air is a 124B mixture-of-experts model with 5.5B parameters active per token. It has 35 KDA linear-attention layers, 7 gated-MLA layers and 512 routed experts, of which 8 are active per token. LingSante-3.1-air-VL is inclusionAI’s medical vision-language model on the same backbone. Served names are `ling-3.2-air-atlas` and `lingsante-air-vl`.

**Strict mode** serves the original checkpoints for reference. Ling’s FP8 weights are 120.4 GiB, and Air-VL’s BF16 weights are 232.55 GiB. Neither fits in memory, so Strict pages experts from disk and decodes at about 2 tokens per second. Strict’s KV pool stops at eight full windows (15.8 GB at 262K), so the rest of memory can cache the experts it reads from disk. With no limit the pool took 68 GB and Strict slowed to 0.3 tok/s. Use Spark mode for speed. [Strict runs](results/2026-11-25-0.1.1/README.md#strict-mode)

## Input

- **Text and tools.** Tool calls use Ling’s template and parser. The tool guard is on by default and blocks calls to metadata addresses and calls that send credentials. A blocked call ends the response with `content_filter`.
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

[results/2026-11-25-0.1.1](results/2026-11-25-0.1.1/README.md) lists the scripts and commands behind every number above. The reference launchers pin the vLLM and SGLang images. [Benchmark instructions](docs/REPRODUCE.md) · [Functional checks](bench/README.md) · [Reference launchers](reference/README.md) · [Earlier results](results/README.md)

## Engine and license

SparkLing contains the launcher, profiles and benchmarks; the implementation lives in Atlas. The install manifest pins the exact engine commit and source tree. SparkLing and Atlas are AGPL-3.0-only. Ling-3.2-air, LingSante-3.1-air-VL, Primitive AI’s NVFP4A16 and Enntity’s NVFP4 weights are MIT. [Engine pin](install/atlas-source.json) · [Upstream Atlas PR](https://github.com/Atlas-Inf/atlas/pull/411) · [License](LICENSE) · [Notices](NOTICE)
