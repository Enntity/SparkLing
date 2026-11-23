# SPDX-License-Identifier: AGPL-3.0-only
"""Replay the short single-stream decode probe and emit one JSON record per run."""
import argparse
import hashlib
import json
import time
import urllib.request

from _common import SERVED_MODEL_NAME, chat_url


def run(url, request_bytes):
    req = urllib.request.Request(
        url, data=request_bytes, headers={"Content-Type": "application/json"}
    )
    first = None
    last = None
    usage = None
    text = []
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=1800) as response:
        for line in response:
            if not line.startswith(b"data: "):
                continue
            payload = line[6:].strip()
            if payload == b"[DONE]":
                break
            event = json.loads(payload)
            if event.get("usage"):
                usage = event["usage"]
            for choice in event.get("choices", []):
                delta = choice["delta"]
                chunk = delta.get("content") or delta.get("reasoning_content") or delta.get("reasoning")
                if chunk:
                    last = time.perf_counter()
                    if first is None:
                        first = last
                    text.append(chunk)
    if first is None or first == last or not usage or usage["completion_tokens"] < 2:
        raise ValueError(f"incomplete stream, usage={usage}")
    return {
        "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
        "usage": usage,
        "ttft_s": first - start,
        "decode_tok_s": (usage["completion_tokens"] - 1) / (last - first),
        "text": "".join(text),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--tokens", type=int, default=64)
    args = parser.parse_args()
    if args.repeat < 1 or args.tokens < 2:
        parser.error("at least one repetition and two completion tokens are required")
    body = {
        "model": SERVED_MODEL_NAME,
        "messages": [{
            "role": "user",
            "content": "List the positive integers from 1 to 100, one number per line.",
        }],
        "max_tokens": args.tokens,
        "temperature": 0,
        "seed": 31,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {"enable_thinking": False},
    }
    request_bytes = json.dumps(body, separators=(",", ":")).encode()
    for rep in range(args.repeat):
        print(json.dumps({"rep": rep, **run(chat_url(args.port), request_bytes)}), flush=True)


if __name__ == "__main__":
    main()
