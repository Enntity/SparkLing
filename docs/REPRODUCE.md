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
