<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# Reproduce our numbers

## Current suite

Run SparkModelBench with the server up and nothing else using the Spark. The
Git submodule pins the shared runner and both upstream RigMark suites; it is
the suite SparkGLM uses. Prepare the CPU quality judge before measuring.

```sh
./start.sh up
git submodule update --init --recursive -- bench/sparkmodelbench
docker build -t rigmark-quality-runtime:0.4 bench/sparkmodelbench/upstream/rigmark-quality/quality_suite
cp bench/sparkmodelbench/upstream/rigmark/metadata.example.json /tmp/sparkling-appliance.json
# Fill in the hardware, model, image and settings of the serving instance.
bench/run.sh --metadata /tmp/sparkling-appliance.json --out /tmp/sparkling-benchmark
```

For LingSante, start it with `./start.sh --model lingsante-3.1-air-vl up` and
run with `SERVED_MODEL_NAME=lingsante-3.1-air-vl-atlas`. Use a new result
directory for each run. Prefill depths beyond the model's window (with its
eight-token output reserve) are skipped: 256K for Ling, 128K and 256K for
LingSante. Every result includes a card, raw JSON and SHA256SUMS. See the
[suite protocol](../bench/sparkmodelbench) for how to read output gates, cache
evidence and task budgets.

The vLLM column (measured November 26 for 0.1.3 and reused for 0.1.4, since vLLM did not change) ran 0.1.2's reference command
([vllm-mtp3.cmd](../results/2026-11-26-0.1.2/rigmark/vllm-mtp3.cmd)) with
`--max-model-len 262144`, on the same Spark after SparkLing stopped, through
`bench/sparkmodelbench/run.py --base-url http://127.0.0.1:8897 --model ling-3.2-air-atlas`.

The eight-request rows come from SparkModelBench's optional concurrency lane,
RigMark's own 1/2/4/8 sweep, which runs only when named:
`bench/run.sh --metadata ... --out ... --lanes concurrency`. 0.1.5 and 0.1.4
measured Ling-3.2-air at `293a44f` (180-second quality task budget) so numbers
compare directly with vLLM; `bench/sparkmodelbench` now pins `2b9ce8c`, which
raises `task_seconds` to 300 for future runs. 0.1.3's concurrency rows came
from `ebc29c4` (Enntity/sparkmodelbench#1).
The [scorecard](../results/sparkmodelbench-v0.1.5/CARD.md) combines those
summaries; its `SHA256SUMS` covers every published file.

## Prefill A/B and exactness (0.1.4)

[results/2026-11-27-0.1.4/harness](../results/2026-11-27-0.1.4/harness) holds
the scripts behind 0.1.4's prefill comparison. `pf-ab.sh LABEL BINARY` starts
the 0.1.3 release image through its `start.sh` arguments with an engine binary
mounted in place of its own (`release` keeps the image's), then runs the
eight probes, `long_id.py` (greedy output and logprobs after fixed prompts of
the given lengths) and cold prefills from 8K to 128K. `pf-sante.sh` does the
same for LingSante, and `note_replay.py` replays the demo's radiograph read and
forced-tool note. Compare two runs' JSON lines for equal text and logprobs.

## One-Spark comparison with RigMark 1.1.0 (0.1.0 to 0.1.3)

Use RigMark at `40fabcaf6e963ac27ab347f61d54a225dbd07419`, the revision used by SparkInkling 0.4.2.
Reserve one physical GB10. Record the GPU UUID, model revision, image digest,
cache dtype, sequence limit, drafter settings, driver version and concurrent
traffic for both engines. Stop the first engine before bringing up the second.
Use `PROFILE=rigmark-40k` for the historical 40,960-token comparison. Allow at least 40,960 tokens on both endpoints to leave room for the 32K prefill and its completion. Use the same tokenizer, template, thinking setting and generation parameters.

Run the code and prose suites and the functional checks in [bench](../bench/README.md).
Keep cold and replayed prefill separate. Save each repetition, failed
completion and the raw JSON. List the exact commands and generate SHA256SUMS
for the files in each results directory.

## The functional check

Score arithmetic and tool calls, inspect the vision fixtures and check
streamed tool arguments and prefix-cache behavior before interpreting speed.
For the NVFP4A16 mode, report quality changes against the publisher's FP8
checkpoint separately from the same-checkpoint engine comparison.

## Context retrieval and Air-VL checks

With Ling-3.2-air running and its tokenizer available locally, use
`python3 bench/context_window.py /path/to/checkpoint --window 524` for
the 512-token control. Repeat with `--window 262144` for the full
prompt and output budget. Both requests place the key at the beginning.
The recorded run used Spark mode with `PREFILL_PRECISION=nvfp4` and
`DECODE_PRECISION=nvfp4`. The script uses Transformers for tokenization.

For Air-VL, run `python3 bench/sante_air_vl.py 8897 parity` on Atlas
and repeat on port 8898 for SGLang. Compare the request hashes and the
arithmetic and image answers. Replace `parity` with `speed` to time two
64-token streams. The decode rate excludes time to the first token.

## Native drafting and Air-VL NVFP4

`bench/draft_decode.py PORT` sends three greedy 64-token requests. Run it against the same profile with `DRAFTER=none` and `DRAFTER=mtp`. Compare the output strings and tokens per second after the first token. With drafting on, each record also has `draft_accept`, the share of drafts the verify accepted. `--min-count-accept 0.95` fails the run if counting accepts less: the predictor almost never misses on counting, so a lower share means the drafter is broken even though the output stays exact. For Air-VL, pass `--model lingsante-3.1-air-vl-atlas`.

Download the 70.88 GiB Air-VL checkpoint with `./start.sh --model lingsante-3.1-air-vl --mode spark --quant nvfp4 download`. The launcher fetches Enntity’s pinned Hub revision, checks SHA-256 for all 70 inference files, and shares the cache directory with the previous byte-identical local conversion. An existing verified copy also works offline. The same command with `verify` repeats the hashes. Strict BF16 and publisher MXFP4 have their own checkpoint directories. [Published weights](https://huggingface.co/Enntity/LingSante-3.1-air-VL-NVFP4)

To reproduce the quantization independently, run `python3 install/quantize_sante.py ORIGINAL_BF16 OUTPUT` with Python, CUDA PyTorch, Triton and safetensors as used in the pinned SGLang image. The 232.55 GiB original and the output must both fit on disk. [Quantizer](../install/quantize_sante.py)

Use `python3 bench/sante_air_vl.py PORT parity` and `speed` for the paired image, text and decode probes. `python3 bench/sante_distributions.py PORT quality` records next-token top-five probabilities. The `prefill` command sends the same cold 512- and 2,048-token inputs to each server. `bench/sante_experts.py --help` gives the offline comparison against the original expert tensors.

For the transferred predictor, set `DRAFTER=ling-mtp` on the Air-VL NVFP4 launch and repeat the same requests. SparkLing fetches only the four donor files needed from the pinned Primitive A16 revision. It prepares a sibling directory that hardlinks Santé’s target files and adds Ling’s final predictor block. Keep that directory on the target filesystem. The `verify` command checks both the target and the draft view. [Donor manifest](../install/checkpoint-sante-draft.json)

## Release checks and quality (0.1.1)

[results/2026-11-25-0.1.1/harness](../results/2026-11-25-0.1.1/harness) holds the scripts behind the 0.1.1 tables. `rel11.sh` launches the image through `./start.sh up` and runs the speed, concurrency, media and task probes. `conc_long.py N WINDOW` sends N simultaneous recall prompts with distinct content. `deep_decode.py WINDOW 256` measures decode after a prompt of that length. `gsm8k_eval.py` scores the first 200 GSM8K test problems. `dist_ling.py`, `dist_decode2.py` and their scorers compare next-token distributions with a reference engine; `dist.sh` and `dist3.sh` run them against vLLM on the same checkpoint. `prof.sh` records one drafted probe under Nsight Systems. The GPU check of the latent cache kernels is `tests/ling/mla_latent.cu` in the pinned Atlas tree.

## Release comparison (0.1.0)

[results/2026-11-25/harness](../results/2026-11-25/harness) holds the scripts behind the 0.1.0 tables. `probe.py PORT 256` sends the eight greedy prompts. `conc.py PORT MODEL 256 1 2 4 8` runs the concurrency sweep. `summary.py RUN.jsonl REFERENCE.jsonl` reports each prompt's rate and whether its text equals the reference. `release-check.sh` launches the image through `./start.sh up` and runs every probe. `comp-vllm.sh`, `comp-llama.sh` and `comp-sglang.sh` run the same probes against the other engines.
