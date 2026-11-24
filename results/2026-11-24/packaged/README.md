# Packaged launcher checks on one DGX Spark

SparkLing commit `928a84e` built an ARM64 image on Spark 03 with the pinned Atlas revision `144e107`. The Docker build passed its configured workspace test and Clippy gates. The local image ID was `sha256:cc8d320da7624456e90389eefc0606f3899d654c787d943be16c96b7253af8af`. The install tree was `959bd233e3d0ad3e87e7fea1b77b8f82175963fc`.

## Santé at 131,072 configured tokens

The public launcher started the derived Santé NVFP4 target with Ling's borrowed predictor, fast attention, MLPs and vocabulary head. The models endpoint advertised 131,072 tokens. One short 64-token request per workload gave **61.10 tok/s counting, 57.56 prose and 68.90 Python**. The output strings matched the corresponding 4K drafted runs byte for byte. The worker returned 391 for the arithmetic check and identified the blue square. These short prompts measure decode with the full context pool configured. [Streams](sante-128k-drafted.jsonl) · [Parity](sante-128k-drafted-parity.jsonl)

## Ling at 40,960 configured tokens

The packaged A16 launch with native MTP generated **59.50 tok/s counting, 50.82 prose and 54.47 Python**. Toggling drafting per request on the same worker changed the prose continuation. The difference also appeared with explicit neutral penalties and greedy settings. [Streams](ling-streams.jsonl) · [Prose control](ling-prose-diagnostic.jsonl)

The model read all three invoice fields and all three grid cells correctly. It rejected the animated GIF with HTTP 400 during placeholder expansion. Ling's template emits `<|video_start|>` and `<|video_end|>`. The active expander searches for `<|vision_start|>` and `<|vision_end|>`. The default server also rejected MP4 because its FFmpeg decoder is disabled. The grid checker ignores Markdown emphasis when matching the labels and colors. [Media checks](media.jsonl) · [Reproduction](../../../bench/vision_check.py)

## Default Ling Strict at 262,144 configured tokens

The bare launcher used the publisher FP8 checkpoint, checkpoint precision, the default 256K profile and ordinary decode. After its startup arithmetic check, a new 39-token counting prompt took **26.56 s to first token** and generated 8 tokens at **1.58 tok/s**. The same prompt immediately repeated with a 64-token limit took **0.637 s to first token** and decoded at **3.37 tok/s**, with zero cached prompt tokens reported. These timings include the benefit of warm expert pages. [Strict request receipts](strict-256k.jsonl)
