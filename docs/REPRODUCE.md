<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# One-Spark comparison

Use RigMark at `40fabcaf6e96`, the revision used by SparkInkling 0.4.2.
Reserve one physical GB10. Record the GPU UUID, model revision, image digest,
cache dtype, sequence limit, drafter settings, driver version and concurrent
traffic for both engines. Stop the first engine before bringing up the second.
Use the same tokenizer, template, thinking setting and generation parameters.

Run the code and prose suites and the functional checks in [bench](../bench/README.md).
Keep cold and replayed prefill separate. Save each repetition, failed
completion and the raw JSON. List the exact commands and generate SHA256SUMS
for the files in each results directory.

## The functional check

Score arithmetic and tool calls, inspect the vision fixtures and check
streamed tool arguments and prefix-cache behavior before interpreting speed.
For the NVFP4A16 mode, report quality changes against the publisher's FP8
checkpoint separately from the same-checkpoint engine comparison.
