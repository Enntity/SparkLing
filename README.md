<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<p align="center">
  <img src="docs/assets/banner.png" alt="SparkLing 0.1.0 on one DGX Spark, single-stream decode with exact native drafting. Counting, prose and Python: Ling-3.2-air 56.9, 55.4 and 54.2 tokens/s; LingSante-3.1-air-VL 54.5, 50.7 and 56.2 tokens/s." width="100%">
</p>

# SparkLing

**SparkLing 0.1.0** serves inclusionAI’s **Ling-3.2-air** and **LingSante-3.1-air-VL** on one NVIDIA DGX Spark. The Atlas engine provides an OpenAI-compatible API for text, images, video and tool calls. In its default Spark mode, SparkLing drafts with each model’s native next-token predictor. Every draft is verified with the same arithmetic as plain decoding, so greedy output is byte-for-byte identical with drafting on or off.

```sh
git clone https://github.com/Enntity/SparkLing.git
cd SparkLing
./start.sh up                          # Ling-3.2-air, Spark mode
./start.sh --model sante-air-vl up     # LingSante-3.1-air-VL, Spark mode
```

The endpoint is `http://127.0.0.1:8897/v1`. The first start downloads and verifies the pinned checkpoint, then pulls the pinned image `ghcr.io/enntity/atlas-sparkling`.

## Speed on one Spark

All engines below ran on the same GB10, one at a time, with nothing else using the GPU. SparkLing’s column is the published `0.1.0` image launched by `./start.sh up`. The client sent the same request bodies to each engine: eight greedy prompts of 256 tokens each, with thinking off. Decode rate is measured after the first token.

| November 25, 2026 · one GB10 · Ling-3.2-air | SparkLing 0.1.0 | vLLM, MTP ×3 | vLLM | llama.cpp, MTP | llama.cpp |
| --- | ---: | ---: | ---: | ---: | ---: |
| Single stream, mean of eight prompts, tok/s | **55.2** | 40.2 | 21.8 | 50.2 | 37.3 |
| Prompts on which the engine is fastest | **5 of 8** | 0 | 0 | 3 of 8 | 0 |
| Aggregate, 1 client, tok/s | 54.6 | 44.6 | 21.6 | **56.5** | 37.4 |
| Aggregate, 2 clients, tok/s | 61.1 | 59.2 | 40.2 | **65.1** | 48.0 |
| Aggregate, 4 clients, tok/s | **77.3** | 68.8 | 62.4 | 62.7 | 67.3 |
| Aggregate, 8 clients, tok/s | 104.0 | **109.2** | 96.4 | 78.8 | 69.5 |

SparkLing and vLLM both served Primitive AI’s NVFP4A16 checkpoint. llama.cpp `b12600` served bartowski’s Q4_K_M GGUF, a different quantization, with all layers on the GPU. The aggregate rows count total generated tokens over wall-clock time, starting from the first request, so they include time to first token. The concurrency rows send the counting prompt with a different suffix to each client.

Where SparkLing is not fastest:

- **Highly predictable text.** llama.cpp leads on counting, code and JSON: 58.4, 57.0 and 58.5 tok/s against SparkLing’s 56.9, 54.2 and 45.5. llama.cpp drafts several tokens per step, about 2.8 per step here. SparkLing drafts one, because Ling’s single predictor layer is trained to predict one step ahead. A two-token SparkLing draft stayed exact, but the second draft was accepted only 18–25% of the time and the run was slower overall, at 42.2 tok/s. [Two-draft run](results/2026-11-25/raw/b9-d2.jsonl)
- **Eight concurrent requests.** vLLM with MTP leads by 5%. Atlas prefills simultaneous prompts one after another rather than in one batch. At eight clients its median time to first token was 1.03 s, against vLLM’s 0.69 s.

[Measurements, commands and raw streams](results/2026-11-25/README.md)

## Exact native drafting

Ling-3.2-air ships one MTP layer. Atlas runs that layer to propose the next token and verifies each proposal together with the current token in one two-row pass. Every row of that pass, including its FFN, uses the kernels that single-token decode uses. Drafted greedy text matched plain decode on all eight prompts, at 55.2 tok/s against 44.3. Drafting is on for one active request. From two requests, Atlas switches to batched plain decoding, which is faster here than verifying requests in turn.

LingSante-3.1-air-VL has no predictor of its own. In Spark mode it borrows Ling-3.2-air’s layer, downloaded with the model. Its drafted text also matched plain decode on all eight prompts, at 53.9 tok/s against 43.1. `DRAFTER=none` turns drafting off for either model.

## Models and modes

| `--model` | Spark mode (default) | Strict mode | Default context |
| --- | --- | --- | ---: |
| `ling-3.2-air` (default) | Primitive AI NVFP4A16 experts, NVFP4 prefill and attention decode, native drafting | inclusionAI’s original dynamic FP8, checkpoint precision | 131,072 tokens |
| `sante-air-vl` | Enntity NVFP4 from inclusionAI’s BF16, NVFP4 prefill and attention decode, Ling’s drafter | inclusionAI’s original BF16 | 131,072 tokens |

Ling-3.2-air is a 124B mixture-of-experts model with 5.5B parameters active per token. It has 35 KDA linear-attention layers, 7 gated-MLA layers and 512 routed experts, of which 8 are active per token. LingSante-3.1-air-VL is inclusionAI’s medical vision-language model on the same backbone. Served names are `ling-3.2-air-atlas` and `lingsante-air-vl`.

**Context.** The default profile serves 131,072 tokens shared across eight requests, with every expert resident in memory. `PROFILE=max` serves Ling’s full 262,144-token window. At that size the BF16 KV cache (28.4 GiB) and the weights do not fit together on one Spark, so Atlas reads some experts from the model files and one stream decodes at about 9–14 tok/s. A key placed at the start of a 262,132-token prompt was recalled at that size. [256K retrieval](results/2026-11-24/base-window-long.json) · [256K and 128K decode](results/2026-11-25/raw/)

**Strict mode** serves the original checkpoints for reference. Ling’s FP8 weights are 120.4 GiB, and Air-VL’s BF16 weights are 232.55 GiB. Neither fits in memory, so Strict pages experts from disk and decodes at a few tokens per second. Use Spark mode for speed. [Strict timings](results/2026-11-24/packaged/strict-256k.jsonl)

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

In Spark mode, `PREFILL_PRECISION=nvfp4` quantizes routed-expert activations for large prompt batches. `DECODE_PRECISION=nvfp4` quantizes the large attention projections at load time, and keeps the published BF16 vocabulary head. Set either to `checkpoint` to follow the checkpoint’s own precision. Strict uses the published sampling settings; Spark uses Atlas’s sampling defaults, including min-p 0.08 and top-n-sigma 1.0, unless the request overrides them. Optional disk prefix caches use a separate directory for each precision. [Launcher settings](.env.example)

Use `./start.sh status`, `./start.sh logs` and `./start.sh stop` to manage the server, and `./start.sh --version` to print the product version and engine revision. `./start.sh download` and `./start.sh verify` stage a checkpoint ahead of time. Each snapshot has its own immutable revision directory under `MODEL_ROOT` (default `~/models/sparkling`).

## Reproduce

[results/2026-11-25](results/2026-11-25/README.md) lists the scripts and commands behind every number above. The reference launchers pin the vLLM and SGLang images. [Benchmark instructions](docs/REPRODUCE.md) · [Functional checks](bench/README.md) · [Reference launchers](reference/README.md) · [Earlier results](results/README.md)

## Engine and license

SparkLing contains the launcher, profiles and benchmarks; the implementation lives in Atlas. The install manifest pins the exact engine commit and source tree. SparkLing and Atlas are AGPL-3.0-only. Ling-3.2-air, LingSante-3.1-air-VL, Primitive AI’s NVFP4A16 and Enntity’s NVFP4 weights are MIT. [Engine pin](install/atlas-source.json) · [Upstream Atlas PR](https://github.com/Atlas-Inf/atlas/pull/411) · [License](LICENSE) · [Notices](NOTICE)
