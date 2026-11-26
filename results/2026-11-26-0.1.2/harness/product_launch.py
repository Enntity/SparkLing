"""Print SparkLing serve.py's argv and engine env for a configuration, as JSON."""
import json, sys
sys.path.insert(0, "claude-sl/install")
import serve
model, mode, drafter = sys.argv[1:4]
quant = "nvfp4" if model == "sante-air-vl" and mode == "spark" else "publisher"
precision = serve.default_precision(mode, model, quant)
env = {"MODEL_PATH": "/model", "SPARKLING_MODEL": model, "SPARKLING_MODE": mode, "SPARKLING_DRAFTER": drafter,
       "SPARKLING_QUANT": quant, "SPARKLING_PREFILL_PRECISION": precision, "SPARKLING_DECODE_PRECISION": precision,
       "SPARKLING_PREFIX_CACHE_GB": "0", "SPARKLING_DISPLAY_CARVEOUT": "0"}
env.update(a.split("=", 1) for a in sys.argv[4:])
profile = json.load(open("claude-sl/install/profiles/" + env.get("SPARKLING_PROFILE", "default") + ".json"))
argv, out = serve.launch(env, profile)
keep = {k: v for k, v in out.items() if k.startswith(("ATLAS_", "SPARKLING_", "CUDA_", "RUST_"))}
print(json.dumps({"argv": argv[1:], "env": keep}))
