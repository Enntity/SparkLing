"""SparkModelBench appliance metadata for the SparkLing 0.1.4 runs."""
import json, os
out = os.path.expanduser("~/models/sparkling/claude-runs/smb014")
os.makedirs(out, exist_ok=True)
base = {"hardware": "1x NVIDIA DGX Spark (GB10, 128 GB)", "topology": "TP1, single Spark", "negotiated_link_speed": "not applicable",
        "competing_traffic": "none"}
img = "ghcr.io/enntity/atlas-sparkling:0.1.4 (= :c523fbc3852c), the release image, via ./start.sh up"
eng = "SparkLing 0.1.4 (Atlas, Enntity/atlas ling/3.2-air @ 469d1649b)"
sched = "SparkLing default profile: max-num-seqs 8, gpu-memory-utilization 0.89, prefill chunks 8192, prefix caching with a disk tier, display carveout"
drafter = "{}, one draft per step for up to four active requests, verified in one batched forward; plain decoding from five"
runs = {
 "ling": dict(model="primitive-ai/Ling-3.2-air-NVFP4A16", model_revision="3a78e58506316b5b9b7d06037910c3f4abdd291f",
   quantisation="NVFP4A16 experts (publisher); Spark mode NVFP4 prefill activations and NVFP4 attention-projection decode, BF16 vocabulary head",
   kv_cache_dtype="bf16 latent MLA (576 values per token per layer)", serving_engine=eng, serving_image=img,
   drafter=drafter.format("Ling-3.2-air's native MTP layer"), context_limit=262144, scheduler=sched),
 "sante": dict(model="Enntity/LingSante-3.1-air-VL-NVFP4 (from inclusionAI/LingSante-3.1-air-VL BF16)", model_revision="SparkLing 0.1.4 pin",
   quantisation="Enntity NVFP4 experts; NVFP4 prefill activations and NVFP4 attention-projection decode", kv_cache_dtype="bf16 latent MLA",
   serving_engine=eng, serving_image=img, drafter=drafter.format("Ling-3.2-air's MTP layer (borrowed)"),
   context_limit=131072, scheduler=sched),
}
for k, v in runs.items():
    json.dump({**base, **v}, open(f"{out}/metadata-{k}.json", "w"), indent=1)
print(sorted(os.listdir(out)))
