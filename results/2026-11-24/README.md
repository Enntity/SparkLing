# One DGX Spark, November 24, 2026

## Ling-3.2-air context

The default profile admitted a 262,132-token prompt with 12 tokens reserved for completion. Spark mode used Primitive AI’s NVFP4A16 checkpoint, the optional NVFP4 prefill and decode paths, and the BF16 vocabulary head. The engine revision was `84613c151`. The 512-token control and the long request both returned the key `MARIGOLD` from the beginning. Atlas reused 480 prefix tokens on the long request and processed the remaining 261,652. The request took 482.53 seconds. This is a recall check at the context boundary. [Control](base-window-short.json) · [Boundary request](base-window-long.json)

The seven attention layers stored 4,160 BF16 values per token for keys and the same number for values. At 262,144 tokens the cache occupies 28.44 GiB. The server allocated 16,385 blocks of 16 slots, including the reserved block. A CUDA test compared paged decode against a CPU attention calculation at shuffled block boundaries. A second compared tiled prefill against per-query attention with 8,192 earlier tokens. [Kernel comparisons](sante-operator-check.log)

Strict mode with the original Ling-3.2-air FP8 checkpoint also allocated 16,385 blocks, advertised 262,144 tokens, and answered the short arithmetic control correctly. The end-to-end boundary retrieval above used Spark mode. [Strict capacity smoke](strict-base-window-smoke.json)

## LingSante Air-VL MXFP4

Both servers loaded inclusionAI’s MXFP4 revision `be6dd27338cdb9677e11418ec62b349dfb48fb2d`. Atlas used `15a9b70ab`. SGLang used its publisher-recommended ARM64 image and native FlashInfer MXFP4 backend. Both used a 4,096-token sequence limit. The clients sent the same JSON bytes to each endpoint with temperature zero, thinking disabled and one request at a time. [Reference launch](../../reference/README.md)

| Check | Atlas | SGLang |
| --- | ---: | ---: |
| 17 × 23 | 391 | 391 |
| Color of a 112 × 112 blue square | Blue | Blue |
| First 64-token stream, tokens/s after first token | 10.47 | 28.37 |
| Second 64-token stream, tokens/s after first token | 10.48 | 27.59 |

The text probe used 37 input tokens on both servers. Atlas reported 51 for the image request and SGLang reported 52. Both encoded 16 image patches after merging. The generated text of both 64-token streams also matched byte for byte. The first Atlas implementation used the Qwen channel normalization and called the square purple. The measured revision uses the checkpoint’s CLIP normalization and keeps the MXFP4 experts in device memory. [Initial Atlas answers](sante-atlas-initial.jsonl) · [Atlas answers](sante-atlas-parity.jsonl) · [SGLang answers](sante-ref-parity.jsonl) · [Atlas streams](sante-atlas-speed.jsonl) · [SGLang streams](sante-ref-speed.jsonl)

Routed expert bytes, scales, trunk and vocabulary head give about 4.72 GB of active text weights per decode token, assuming each weight is read once. The 244.8 GB/s device-copy result from this Spark gives a weight-only estimate of 51.9 tokens/s. Twice SGLang’s mean rate would be 56.0 tokens/s, before state and KV traffic. [Checkpoint byte counts](sante-roof.json) · [Hardware measurements and assumptions](../2026-11-23/roofline.md)

A separate launch through `./start.sh --model sante-air-vl --mode spark up` used the packaged ARM64 image, allocated the 128K pool and passed its arithmetic smoke. [Image and launch receipt](package-smoke.json)

Run `bench/sante_air_vl.py` for the paired probes and `bench/context_window.py` for the context check. [Commands](../../docs/REPRODUCE.md)
