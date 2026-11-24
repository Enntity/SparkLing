# SPDX-License-Identifier: AGPL-3.0-only
"""Compare short, greedy counting, prose and code streams on matched servers."""
import argparse
import json

from _common import SERVED_MODEL_NAME, chat_url
from short_decode import run

PROMPTS = {
    "count": "Count upward from one using English words separated by commas. Continue through one hundred.",
    "prose": "Describe how an archivist would restore order to a box of unlabeled photographs. Write one concrete paragraph.",
    "code": "Write a Python function that merges two sorted lists into a new sorted list. Give only the function definition and body.",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port")
    parser.add_argument("--model", default=SERVED_MODEL_NAME)
    args = parser.parse_args()
    for label, prompt in PROMPTS.items():
        body = dict(model=args.model, messages=[dict(role="user", content=prompt)], max_tokens=64,
                    temperature=0, seed=31, stream=True, chat_template_kwargs={"enable_thinking": False},
                    stream_options={"include_usage": True})
        result = run(chat_url(args.port), json.dumps(body, separators=(",", ":")).encode())
        print(json.dumps(dict(probe=label, **result)), flush=True)


if __name__ == "__main__":
    main()
