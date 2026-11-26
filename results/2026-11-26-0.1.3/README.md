<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# One DGX Spark, November 26, 2026: SparkLing 0.1.3

Every run used one GB10, with no other model server using the GPU.
- **Release image:** `ghcr.io/enntity/atlas-sparkling:0.1.3` (index digest `sha256:a8565646…71cfbd`), install tree `7a1f9d22997d`, Atlas `ling/3.2-air` at `46ed1a1f3`.
- **Build:** 8,830 engine tests, 0 failures.
- **Launch:** [`harness/rel013.sh`](harness/rel013.sh) started it through `./start.sh up` with the default profile and drafting, then ran the probes. `DRAFTER=none` gave the plain runs.
- **Prefix cache:** the disk tier used a 16 GiB budget, because this Spark's disk was nearly full.

## What changed: several requests draft together

Up to 0.1.2, SparkLing drafted only while a single request was running. From two concurrent requests it decoded plainly: Ling's layers had no verify step that checks several requests' drafts at once, so verifying each request in turn was slower than not drafting. 0.1.3 drafts for up to four live requests.

**Batched verify.** Atlas checks all the live requests' drafts in one forward pass, two rows per request: the committed token and its draft.
- **Recurrent layers:** each linear-attention (KDA) layer advances every request's recurrent state through both rows. It keeps a rollback snapshot after the first row, for a rejected draft.
- **Attention layers:** each MLA layer attends every row against its own request's cache.

**Batched draft.** Ling's predictor drafts for all of those requests in one pass. Its embedding, merge, MLA and MoE body, vocabulary head and argmax each read their weights once for the batch, not once per request.

**Why stop at four.** Ling routes each token to 8 of 512 experts, so different requests rarely share an expert. A verify of eight requests (16 rows) reads 1.63 times the expert weights of a plain eight-request step, and returns about 1.8 tokens per request. On a GB10 that is close to a wash.

Atlas's throughput gate falls back to plain decoding when verifying does not pay. Even so, on the same image with the cap lifted (`ATLAS_MTP_MAX_SEQS=8`), eight requests measured 130.0 tok/s on short code and 110.6 on prose, against 145.2 and 114.9 with it ([receipts](rigmark/uncapped/), [script](harness/rigcap.sh)). Capped at four, eight requests decode as 0.1.2 does.

**Output.** One request's output is unchanged:
- Drafted text equals plain decoding on all 16 probe prompts.
- It also equals 0.1.2's release output on all 16.

Under concurrency, a request's text can depend on what it is batched with, as it already could in 0.1.2's plain batched decoding.

**Cache.** The verify and draft buffers take about 0.6 GB. Ling's shared KV pool is now 2,148,608 tokens, still enough for eight full 262,144-token windows (2,097,152).

## Release image

| | Ling-3.2-air | LingSante-3.1-air-VL |
| --- | ---: | ---: |
| Context window, tokens | 262,144 | 131,072 |
| Shared KV pool, tokens | 2,148,608 | 2,374,592 |
| Single stream, mean of eight prompts, tok/s | 60.4 | 57.4 |
| Plain decode, mean of eight prompts, tok/s | 44.7 | 44.2 |
| Drafted text equal to plain decode | 8 of 8 | 8 of 8 |
| Drafted text equal to 0.1.2 | 8 of 8 | 8 of 8 |
| First drafts accepted, counting | 100% | 100% |
| Aggregate, 1 / 2 / 4 / 8 clients, tok/s | 60.0 / 78.0 / 85.6 / 104.2 | 59.1 / 74.4 / 80.7 / 104.9 |
| Arithmetic, 30 word problems with thinking on | 30 | 30 |
| Single-tool calls, right tool and argument | 10 of 10 | 10 of 10 |
| Media: red-to-blue clip, counting clip (GIF and MP4), 90 s 720p clip, invoice, grid | all read correctly | all read correctly |
| `bench/draft_decode.py --min-count-accept 0.95` | passed | passed |

The aggregate row is our own probe: eight 256-token prompts, one round. Its numbers vary from run to run with output length. RigMark below is the measurement to compare.

[Ling](release/ling-spark-probe.jsonl) · [Ling plain](release/ling-spark-plain.jsonl) · [Ling concurrency](release/ling-spark-conc.jsonl) · [Ling media](release/ling-spark-media.jsonl) · [Ling tasks](release/ling-spark-task.json) · [Ling draft check](release/ling-spark-draft-check.jsonl) · [Ling cache log](release/ling-spark-server-kv.log) · [Air-VL](release/sante-spark-probe.jsonl) · [Air-VL plain](release/sante-spark-plain.jsonl) · [Air-VL concurrency](release/sante-spark-conc.jsonl) · [Air-VL media](release/sante-spark-media.jsonl) · [Air-VL tasks](release/sante-spark-task.json) · [Air-VL draft check](release/sante-spark-draft-check.jsonl) · [Air-VL cache log](release/sante-spark-server-kv.log)

## RigMark

[RigMark](https://github.com/alexellis/rigmark) `40fabcaf6e96`, protocol 1.1.0: the code and prose suites, with the same settings as 0.1.2 ([0.1.2 results](../2026-11-26-0.1.2/README.md#rigmark)).
- **Runs:** two decode runs per workload, two cold prefills per depth, two rounds per concurrency.
- **Thinking:** off, via `chat_template_kwargs.enable_thinking=false`.
- **SparkLing:** ran through `./start.sh` with the default profile and drafter.
- **vLLM columns:** 0.1.2's runs on the same Spark, same RigMark and same checkpoint. Its engine did not change.

Medians:

| | Ling 0.1.3 | Ling 0.1.2 | LingSante 0.1.3 | LingSante 0.1.2 | vLLM, MTP ×3 | vLLM |
|---|---:|---:|---:|---:|---:|---:|
| Code decode, tok/s | 63.0 | 62.9 | 62.4 | 62.5 | 45.4 | 21.6 |
| Prose decode | 54.7 | 54.7 | 49.8 | 49.7 | 32.9 | 21.7 |
| Structured decode | 64.7 | 64.9 | 63.4 | 63.7 | 44.9 | 21.7 |
| 32K cold prefill | 2,577 | 2,582 | 2,576 | 2,573 | 2,474 | 2,120 |
| 8K cold prefill | 3,404 | 3,400 | 3,405 | 3,412 | 2,908 | 2,355 |
| Short code, aggregate C1 / C2 / C4 / C8 | 58.1 / **84.9** / **122.6** / 145.2 | 58.3 / 66.1 / 98.8 / 142.3 | 56.0 / **86.0** / **117.8** / 139.6 | 56.5 / 66.5 / 96.6 / 136.2 | 37.3 / 67.3 / 112.4 / 167.5 | 20.9 / 45.2 / 79.7 / 129.4 |
| Short prose, aggregate C1 / C4 / C8 | 50.5 / **95.9** / 114.9 | 50.6 / 86.6 / 115.1 | 47.0 / **91.1** / 115.5 | 47.0 / 86.8 / 116.5 | 29.2 / 82.2 / 125.8 | 21.3 / 75.7 / 119.6 |
| 32K / 8K prompt sent again, time to first token | 0.02 s / 0.01 s | 0.02 s / 0.01 s | 0.02 s / 0.01 s | 0.02 s / 0.01 s | 1.15 s / 0.72 s | 0.89 s / 0.25 s |
| Basic output gates | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |

**Two to four requests.** Ling's short code is 28% faster at two requests and 24% faster at four. Its prose is 11% faster at four. SparkLing now leads vLLM with its drafter at one, two and four requests, on code and prose.

**Eight requests.** vLLM keeps the lead there: 1.15× on code and 1.09× on prose, against Ling. Its drafter verifies four rows per request. SparkLing decodes eight requests plainly (see above).

[Cards](rigmark/) (`*.card.txt`) · [JSON receipts](rigmark/) · [run script](rigmark/rig013.sh) · [metadata](rigmark/meta013.py)

### Where the time goes at eight requests

Profiled with `nsys` on one GB10, Ling, eight requests (per forward pass):

| | 8-row plain decode | 16-row verify, as first built | 16-row verify, projections and recurrence fixed |
| --- | ---: | ---: | ---: |
| Routed experts (`ling_expert_mma`) | 34.1 ms | 52.8 ms | 54.2 ms |
| Everything else | 26.3 ms | 73.1 ms | 55.5 ms |
| Forward pass | 60.4 ms | 125.9 ms | 109.7 ms |

The first build sent 16-row attention projections to a BF16 GEMM and ran the recurrence once per request per row. The second build sent them to the NVFP4 decode tiers, and ran the recurrence as two launches: one over every request's first row, one over every second row. Moving the router and the shared expert to the decode kernels as well left eight requests level with plain decoding.

The experts still set the floor. They already stream at about 245 GB/s, and 16 rows read 1.63 times the expert bytes of 8. The released engine keeps the recurrence change. With at most four requests drafting, a verify never exceeds eight rows, so the 9–32-row kernel changes were withdrawn: they only changed how short prompt chunks prefill (Enntity/atlas#45).
