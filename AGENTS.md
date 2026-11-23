# SparkLing

Keep the inference engine in Enntity/atlas. Pin its commit and tree under
install/. All image inputs belong in install/ and the pinned Atlas checkout.
Publish to Enntity repositories as data-angel.

Strict mode takes the original inclusionAI checkpoint, its dynamic FP8
activation scheme, tokenizer, chat template and multimodal processor. Preserve
expert bytes and scales across storage tiers. Spark mode selects a separately
pinned checkpoint. Keep model weights, host details and credentials out of Git.

Use the single-Spark code and prose RigMark suites and functional checks in
bench/. Preserve the raw runs and their SHA256SUMS in results/. Compare the
same checkpoint on the same idle physical Spark with matched generation limits,
cache settings and request bodies.
