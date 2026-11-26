"""Write RigMark metadata for the SparkLing 0.1.2 and vLLM reference runs."""
import json, os
out = os.path.expanduser("~/models/sparkling/claude-runs/rig012")
os.makedirs(out, exist_ok=True)
base = {"hardware": "1x NVIDIA DGX Spark (GB10, 128 GB)", "topology": "TP1, single Spark", "negotiated_link_speed": "not applicable",
        "competing_traffic": "none", "reasoning": "thinking off (chat_template_kwargs.enable_thinking=false); Ling's template has no effort levels"}
img = "ghcr.io/enntity/atlas-sparkling:0.1.2 (= :2b64f3eb9763, index sha256:a86632ffc12369be26cd9b9250d09f9dd24c96dacdf00703374dc40a2294581f), the release image, via ./start.sh"
eng = "SparkLing 0.1.2 (Atlas, Enntity/atlas ling/3.2-air @ 18dec2347)"
sched = "SparkLing default profile: max-num-seqs 8, gpu-memory-utilization 0.89, prefill chunks 8192, prefix caching (16 GiB disk tier), display carveout"
runs = {
 "sparkling-ling": dict(model="primitive-ai/Ling-3.2-air-NVFP4A16", model_revision="3a78e58506316b5b9b7d06037910c3f4abdd291f",
   quantisation="NVFP4A16 experts (publisher); Spark mode NVFP4 prefill activations and NVFP4 attention-projection decode, BF16 vocabulary head",
   kv_cache_dtype="bf16 latent MLA (576 values per token per layer)", serving_engine=eng, serving_image=img,
   drafter="Ling-3.2-air's native MTP layer, one draft per step with one live request, plain decode from two", context_limit=262144, scheduler=sched),
 "sparkling-sante": dict(model="Enntity/LingSante-3.1-air-VL-NVFP4 (from inclusionAI/LingSante-3.1-air-VL BF16)", model_revision="SparkLing 0.1.2 pin",
   quantisation="Enntity NVFP4 experts; NVFP4 prefill activations and NVFP4 attention-projection decode", kv_cache_dtype="bf16 latent MLA",
   serving_engine=eng, serving_image=img, drafter="Ling-3.2-air's MTP layer (borrowed), one draft per step with one live request, plain decode from two",
   context_limit=131072, scheduler=sched),
 "vllm-mtp3": dict(model="primitive-ai/Ling-3.2-air-NVFP4A16", model_revision="3a78e58506316b5b9b7d06037910c3f4abdd291f", quantisation="NVFP4A16 (Marlin weight-only FP4 on GB10)",
   kv_cache_dtype="auto", serving_engine="vLLM nightly a2bcb5657 (SparkLing reference/serve.py --mode a16)", serving_image="vllm/vllm-openai:cu134-nightly-a2bcb5657 @ sha256:24541db8",
   drafter="native MTP, num_speculative_tokens 3", context_limit=40960, scheduler="max-num-seqs 8, reference launcher defaults"),
}
runs["vllm"] = dict(runs["vllm-mtp3"], drafter="none")
for k, v in runs.items():
    json.dump({**base, **v}, open(f"{out}/metadata-{k}.json", "w"), indent=1)
print(sorted(os.listdir(out)))
