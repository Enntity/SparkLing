<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# Benchmark runner and functional-check drivers

SparkLing keeps the SparkInkling functional checks and runs the shared
SparkModelBench suite for throughput and quality. The drivers are model-agnostic so the same requests can be replayed
against SparkLing and its reference implementation.

## Throughput and quality

`run.sh` runs the pinned [SparkModelBench](https://github.com/enntity/sparkmodelbench)
suite against the server `./start.sh` started, in whatever mode it is serving.
It is the suite SparkGLM uses: Alex Ellis's [RigMark](https://github.com/alexellis/rigmark)
decode and exact-depth prefill, four [RigMark Quality](https://github.com/alexellis/rigmark-quality)
agent tasks, and SparkGLM's staggered four-request field guide. The Git submodule
`sparkmodelbench` pins the runner and both upstream suites.

```sh
./start.sh up
git submodule update --init --recursive -- bench/sparkmodelbench
docker build -t rigmark-quality-runtime:0.4 bench/sparkmodelbench/upstream/rigmark-quality/quality_suite
cp bench/sparkmodelbench/upstream/rigmark/metadata.example.json /tmp/sparkling-appliance.json
# Fill in the hardware, model, image and settings of the serving instance.
bench/run.sh --metadata /tmp/sparkling-appliance.json --out /tmp/sparkling-benchmark
```

Set `SERVED_MODEL_NAME=lingsante-3.1-air-vl-atlas` for LingSante and
`SPARKLING_PORT` for another port. Use a new result directory for each run.
The suite asks for `reasoning_effort: low`; Ling's template has no effort
levels, so thinking stays on, as it is by default. The staggered field guide
turns thinking off. Each result holds `CARD.md`, the raw JSON and `SHA256SUMS`.

`rigmark.sh` runs the earlier RigMark 1.1.0 code and prose suites (thinking
off, 1/2/4/8 concurrent requests) behind the 0.1.2 and 0.1.3 release
comparisons with vLLM:

```sh
RIGMARK=/path/to/rigmark bench/rigmark.sh spark metadata.json out/
```

`SPARKLING_URL`, `SPARKLING_PORT`, `SERVED_MODEL_NAME` and
`SPARKLING_COMPARISON_ID` override the default address, port, model name and
RigMark comparison id. Run the candidate and reference one after the other on
the same Spark, with the same checkpoint, request model name, context limit and
benchmark settings, and never leave both model servers resident during a timed
run:

```sh
# Candidate run
SPARKLING_URL=http://127.0.0.1:8897 SERVED_MODEL_NAME=ling-3.2-air-atlas \
  RIGMARK=/path/to/rigmark bench/rigmark.sh candidate metadata-candidate.json out/candidate

# In a separate terminal after stopping SparkLing
python3 reference/serve.py --mode a16 --model-dir "$MODEL_DIR" \
  --served-model-name ling-3.2-air-atlas --port 11897 --gpu-memory-utilization 0.86

# Run against that reference from the original terminal
SPARKLING_URL=http://127.0.0.1:11897 SERVED_MODEL_NAME=ling-3.2-air-atlas \
  RIGMARK=/path/to/rigmark bench/rigmark.sh reference metadata-reference.json out/reference

python3 bench/compare_onespark.py \
  out/candidate/candidate-code.json out/reference/reference-code.json \
  out/candidate/candidate-prose.json out/reference/reference-prose.json
```

## Functional check

The small drivers each release's functional check runs
([REPRODUCE](../docs/REPRODUCE.md#the-functional-check)). They derive from SparkInkling’s release checks.
They need only Python 3, talk to the server `./start.sh` starts on
`http://127.0.0.1:8897` by default, and send greedy requests (temperature 0)
with `chat_template_kwargs.enable_thinking` set explicitly for each case. Run them
one at a time with nothing else using the Spark. They are smoke checks, not
benchmarks; throughput and quality are measured with SparkModelBench as
REPRODUCE describes.

| Driver | What it checks | Run |
|---|---|---|
| `task_probe.py` | 30 arithmetic problems graded exactly and 10 tool-call prompts graded on tool and arguments, thinking enabled | `python3 task_probe.py` or `SPARKLING_PORT=8897 python3 task_probe.py` (prints one JSON summary) |
| `tooltest.py` | A tool call comes back as an OpenAI tool call, blocking and streamed, with thinking on and off | `python3 tooltest.py` |
| `argstream.py` | A streamed tool call's arguments (asked for with `stream_tool_arguments: true`) arrive in many chunks and join to valid JSON | `python3 argstream.py` |
| `forced_stream.py` | Forced tool choices (a named function with thinking on and off, `required`) finish `tool_calls` when streamed; a call to a cloud metadata address streams and then finishes `content_filter` under the default tool guard (both with `stream_tool_arguments: true`); without it, the benign call arrives whole and the blocked one sends no arguments | `python3 forced_stream.py` |
| `vis_chat.py` | Image input: each image is sent as a base64 data URI with its question | `python3 vis_chat.py images/invoice.png "Transcribe all the text in this image exactly, line by line." images/grid.png "This is a 3x3 grid of labelled coloured rectangles. For each label (A1..C3) give its colour, row by row." images/shapes.png "Describe this image in one sentence."` |
| `voice_turns.py` | A voice-agent prompt shape (a long system prompt, history, three trailing messages rebuilt every turn): time to first token per turn, which shows whether the prefix cache resumes at the fork | `python3 voice_turns.py 4` |

`images/` holds the three synthetic PNGs the image check uses. What each
release returned is kept with that release's raw receipts.

`compare_onespark.py` checks that the two RigMark receipts use the same prompt
revision, checkpoint revision, physical device, isolation, temperature, seed,
concurrency matrix and prefill depths. It requires finite positive medians for
every decode, concurrency and cold or warm-replay prefill metric. It then
prints candidate/reference ratios and a separate `winner` field for each
metric. It does not hide failed completion gates or mismatched settings.

For Air-VL set `SERVED_MODEL_NAME=lingsante-3.1-air-vl-atlas` when running these drivers against either engine. The SparkLing launcher uses that API name for both Air-VL precisions.

`python3 vision_check.py 8897 invoice grid gif mp4 gif-count mp4-count` checks three invoice fields, three grid cells, the temporal order of a red-to-blue synthetic clip and the eight numbers of a counting clip, each clip as GIF and MP4. Each requested case emits one JSON record. The command returns a failure if any answer misses its expected fields or the server rejects that input. Pass individual case names to run a shorter check.
