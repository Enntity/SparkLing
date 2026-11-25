# SPDX-License-Identifier: AGPL-3.0-only
"""GSM8K test problems 0..N-1 against an OpenAI-compatible server: greedy,
thinking off, eight requests at a time, scored on the last number of the reply.
usage: gsm8k_eval.py PORT MODEL N OUT.jsonl"""
import json, re, sys, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

port, model, n, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
path = hf_hub_download("openai/gsm8k", "main/test-00000-of-00001.parquet", repo_type="dataset",
                       revision="e53f048856ff4f594e959d75785d2c2d37b678ee")
rows = pq.read_table(path).to_pylist()[:n]
PROMPT = ("Solve the problem. Think step by step, then give the final answer on its own last line "
          "as 'Answer: <number>'.\n\n{q}")


def number(text):
    found = re.findall(r"-?\d[\d,]*\.?\d*", text.split("Answer:")[-1] if "Answer:" in text else text)
    return found[-1].replace(",", "").rstrip(".") if found else None


def run(i):
    row = rows[i]
    body = dict(model=model, messages=[dict(role="user", content=PROMPT.format(q=row["question"]))],
                temperature=0, seed=31, max_tokens=768, chat_template_kwargs=dict(enable_thinking=False))
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    reply = json.load(urllib.request.urlopen(req, timeout=1800))["choices"][0]["message"]["content"]
    gold = row["answer"].split("####")[-1].strip().replace(",", "")
    got = number(reply)
    ok = got is not None and abs(float(got) - float(gold)) < 1e-6
    return dict(i=i, gold=gold, got=got, ok=ok, reply=reply)


with ThreadPoolExecutor(8) as pool:
    results = list(pool.map(run, range(len(rows))))
with open(out, "w") as f:
    for r in results:
        f.write(json.dumps(r) + "\n")
print(json.dumps(dict(model=model, n=len(results), correct=sum(r["ok"] for r in results))))
