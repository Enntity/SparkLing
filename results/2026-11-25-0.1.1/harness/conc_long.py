# SPDX-License-Identifier: AGPL-3.0-only
"""N simultaneous recall requests of `window` tokens each, with distinct
content from the first token (no shared prefix), on one server."""
import json, sys, threading, time, urllib.request
from transformers import AutoTokenizer

KEYS = ["MARIGOLD", "JUNIPER", "OBSIDIAN", "LANTERN", "SAFFRON", "HARBOR", "CINDER", "TUNDRA"]


def prompt(tok, length, i):
    message = (f"Store this archive key for the question at the end: {KEYS[i]}.\nSPLIT_HERE\n"
               "What archive key did I give at the beginning? Answer with only that one word.")
    rendered = tok.apply_chat_template([{"role": "user", "content": message}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False)
    prefix, suffix = (tok.encode(p, add_special_tokens=False) for p in rendered.split("SPLIT_HERE"))
    filler, index = [], 0
    while len(filler) < length - len(prefix) - len(suffix):
        filler.extend(tok.encode(f"Station {i}, log {index}: pressure reading stable.\n", add_special_tokens=False))
        index += 1
    return prefix + filler[: length - len(prefix) - len(suffix)] + suffix


def main():
    tok = AutoTokenizer.from_pretrained("/ckpt", local_files_only=True)
    n, window = int(sys.argv[1]), int(sys.argv[2])
    results = [None] * n

    def run(i):
        ids = prompt(tok, window - 12, i)
        body = dict(model="ling-3.2-air-atlas", prompt=ids, max_tokens=12, temperature=0, seed=31)
        t = time.monotonic()
        req = urllib.request.Request("http://127.0.0.1:8897/v1/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=14400))
        results[i] = dict(i=i, prompt_tokens=r["usage"]["prompt_tokens"], answer=r["choices"][0]["text"].strip(),
                          ok=r["choices"][0]["text"].strip().upper() == KEYS[i], seconds=round(time.monotonic() - t, 1))

    start = time.monotonic()
    threads = [threading.Thread(target=run, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for r in results:
        print(json.dumps(r))
    print(json.dumps(dict(requests=n, window=window, correct=sum(r["ok"] for r in results),
                          total_prompt_tokens=sum(r["prompt_tokens"] for r in results),
                          wall_s=round(time.monotonic() - start, 1))))


if __name__ == "__main__":
    main()
