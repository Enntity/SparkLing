<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# One-Spark comparison

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

`bench/draft_decode.py PORT` sends three greedy 64-token requests. Run it against the same profile with `DRAFTER=none` and `DRAFTER=mtp`. Compare the output strings, accepted prediction token counts and tokens per second after the first token. For Air-VL, pass `--model lingsante-air-vl`.

Build the Air-VL derivative with `./start.sh --model sante-air-vl --mode spark --quant nvfp4 download`. The conversion needs both the 232.55 GiB original and 70.88 GiB output. To reuse an original on another volume, link its immutable revision directory into `MODEL_ROOT`. The launcher checks the BF16 source and verifies the derived files against the pinned SHA-256 manifest. `verify` repeats the hashes. The publisher’s MXFP4 and Strict BF16 keep separate checkpoint directories.

Use `python3 bench/sante_air_vl.py PORT parity` and `speed` for the paired image, text and decode probes. `python3 bench/sante_distributions.py PORT quality` records next-token top-five probabilities. The `prefill` command sends the same cold 512- and 2,048-token inputs to each server. `bench/sante_experts.py --help` gives the offline comparison against the original expert tensors.

For the transferred predictor, set `DRAFTER=ling-mtp` on the Air-VL NVFP4 launch and repeat the same requests. SparkLing fetches only the four donor files needed from the pinned Primitive A16 revision. It prepares a sibling directory that hardlinks Santé’s target files and adds Ling’s final predictor block. Keep that directory on the target filesystem. The `verify` command checks both the target and the draft view. [Donor manifest](../install/checkpoint-sante-draft.json)
