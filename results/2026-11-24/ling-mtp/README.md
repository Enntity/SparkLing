# Ling-3.2-air native one-token drafting

The Primitive AI NVFP4A16 checkpoint contains one appended attention and MoE predictor. It receives a target hidden state and the next token embedding, projects the pair, and predicts through the shared vocabulary. Atlas now runs this predictor, maintains its own attention cache, and verifies the proposed token with the target. When a token is rejected, the target rolls its KDA recurrence and convolution state back to the committed boundary. The published 40K RigMark comparison used ordinary decode on both engines.

Each row below used the same GB10 and checkpoint, a 4K maximum context, one client, fast attention and a BF16 **target** vocabulary head. The requests used greedy sampling with thinking off and generated 64 tokens each. The rates exclude time to first token.

| Atlas configuration | Counting | Prose | Python |
| --- | ---: | ---: | ---: |
| Ordinary decode | 44.34 | 44.95 | 45.32 |
| Native MTP, BF16 draft head | 50.41 | 45.86 | 49.03 |
| Native MTP, batched MLA verification and NVFP4 draft head | 59.57 | 50.27 | 53.89 |

The third run accepted 29, 23 and 25 predicted tokens. Counting and Python matched the ordinary outputs byte for byte. The prose responses first diverged after “protect the images”. The faster verifier executes two target rows together. Consequently the launcher exposes drafting as an opt-in. Each timing is one short decision run per prompt. [Ordinary](ordinary.jsonl) · [BF16 drafter](bf16-draft-head.jsonl) · [Batched verifier](batched-draft.jsonl) · [Benchmark client](../../../bench/draft_decode.py)

Set `DRAFTER=mtp` when launching the base model. The default and Strict launcher settings use ordinary decode. For vLLM use the same A16 checkpoint, `--draft-tokens 3`, and the same one-client requests. The publisher uses its own three-token MTP vLLM recipe on four GPUs. [Publisher recipe](https://huggingface.co/inclusionAI/Ling-3.2-air) · [SparkLing reference launcher](../../../reference/serve.py)

KV-only prompt priming computes the predictor's keys and values in tiles of 128, omitting its historical queries, attention outputs, MoE and vocabulary projection. This version measured **59.04, 50.47 and 53.99 tok/s** with 29, 23 and 25 accepted predictions. A diagnostic with scalar KDA verification measured **43.68, 37.36 and 41.29**, and still differed on prose. [KV-only priming](primed.jsonl) · [Scalar KDA control](serial.jsonl)
