"""Write RigMark metadata for the SparkLing 0.1.3 runs (the vLLM references are 0.1.2's, same Spark and RigMark)."""
import json, os
out = os.path.expanduser("~/models/sparkling/claude-runs/rig013r")
os.makedirs(out, exist_ok=True)
base = {"hardware": "1x NVIDIA DGX Spark (GB10, 128 GB)", "topology": "TP1, single Spark", "negotiated_link_speed": "not applicable",
        "competing_traffic": "none", "reasoning": "thinking off (chat_template_kwargs.enable_thinking=false); Ling's template has no effort levels"}
img = "ghcr.io/enntity/atlas-sparkling:0.1.3 (= :7a1f9d22997d), the release image, via ./start.sh"
eng = "SparkLing 0.1.3 (Atlas, Enntity/atlas ling/3.2-air @ 46ed1a1f3)"
sched = "SparkLing default profile: max-num-seqs 8, gpu-memory-utilization 0.89, prefill chunks 8192, prefix caching (16 GiB disk tier), display carveout"
drafter = "{}, one draft per step for every active request, verified in one batched forward; Atlas's throughput gate decodes plainly when that delivers more"
runs = {
 "sparkling-ling": dict(model="primitive-ai/Ling-3.2-air-NVFP4A16", model_revision="3a78e58506316b5b9b7d06037910c3f4abdd291f",
   quantisation="NVFP4A16 experts (publisher); Spark mode NVFP4 prefill activations and NVFP4 attention-projection decode, BF16 vocabulary head",
   kv_cache_dtype="bf16 latent MLA (576 values per token per layer)", serving_engine=eng, serving_image=img,
   drafter=drafter.format("Ling-3.2-air's native MTP layer"), context_limit=262144, scheduler=sched),
 "sparkling-sante": dict(model="Enntity/LingSante-3.1-air-VL-NVFP4 (from inclusionAI/LingSante-3.1-air-VL BF16)", model_revision="SparkLing 0.1.3 pin",
   quantisation="Enntity NVFP4 experts; NVFP4 prefill activations and NVFP4 attention-projection decode", kv_cache_dtype="bf16 latent MLA",
   serving_engine=eng, serving_image=img, drafter=drafter.format("Ling-3.2-air's MTP layer (borrowed)"),
   context_limit=131072, scheduler=sched),
}
for k, v in runs.items():
    json.dump({**base, **v}, open(f"{out}/metadata-{k}.json", "w"), indent=1)
print(sorted(os.listdir(out)))
