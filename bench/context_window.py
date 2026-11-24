# SPDX-License-Identifier: AGPL-3.0-only
"""Check recall across an exact prompt + generation budget using the checkpoint tokenizer."""
import argparse
import json
import time
import urllib.request

from transformers import AutoTokenizer


def prompt_ids(tokenizer, length):
    message = ("Store this archive key for the question at the end: MARIGOLD.\n"
               "SPLIT_HERE\nWhat archive key did I give at the beginning? Answer with only that one word.")
    rendered = tokenizer.apply_chat_template([{"role": "user", "content": message}],
                                              tokenize=False, add_generation_prompt=True, enable_thinking=False)
    prefix, suffix = (tokenizer.encode(part, add_special_tokens=False) for part in rendered.split("SPLIT_HERE"))
    room = length - len(prefix) - len(suffix)
    if room < 0:
        raise ValueError("context is too short for the retrieval question")
    filler = []
    index = 0
    while len(filler) < room:
        filler.extend(tokenizer.encode(f"Log {index}: The weather station recorded a stable pressure reading.\n",
                                       add_special_tokens=False))
        index += 1
    return prefix + filler[:room] + suffix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", help="local verified Ling-3.2-air tokenizer directory")
    parser.add_argument("--url", default="http://127.0.0.1:8897")
    parser.add_argument("--window", type=int, default=262144)
    args = parser.parse_args()
    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, local_files_only=True)
    tokens = prompt_ids(tokenizer, args.window - 12)
    body = dict(model="ling-3.2-air-atlas", prompt=tokens, max_tokens=12, temperature=0, seed=31)
    req = urllib.request.Request(args.url.rstrip("/") + "/v1/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=7200) as response:
        result = json.load(response)
    answer = result["choices"][0]["text"]
    print(json.dumps(dict(usage=result["usage"], answer=answer, seconds=time.monotonic() - start)))
    if result["usage"]["prompt_tokens"] != len(tokens) or answer.strip().upper() != "MARIGOLD":
        raise SystemExit("context recall check failed")


if __name__ == "__main__":
    main()
