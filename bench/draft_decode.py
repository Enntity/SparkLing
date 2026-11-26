# SPDX-License-Identifier: AGPL-3.0-only
"""Compare short, greedy counting, prose and code streams on matched servers.

With drafting on, each record also carries the share of drafts the verify accepted,
read from the engine's `atlas_spec_decode_verify_total` counters around the request.
`--min-count-accept` fails the run when the counting stream accepts less than that
share: a working predictor almost never misses on counting, so a low value means the
drafter is broken even though verify keeps the output exact.
"""
import argparse
import json
import re
import sys
import urllib.request

from _common import SERVED_MODEL_NAME, chat_url
from short_decode import run

PROMPTS = {
    "count": "Count upward from one using English words separated by commas. Continue through one hundred.",
    "prose": "Describe how an archivist would restore order to a box of unlabeled photographs. Write one concrete paragraph.",
    "code": "Write a Python function that merges two sorted lists into a new sorted list. Give only the function definition and body.",
}
VERIFY = re.compile(r'^atlas_spec_decode_verify_total\{[^}]*outcome="(accept|reject)"[^}]*\} ([0-9.e+]+)$', re.M)


def verify_counts(url):
    """Return (accepted, rejected) single-draft verifies so far, or None without the counters."""
    try:
        text = urllib.request.urlopen(url.replace("/v1/chat/completions", "/metrics"), timeout=10).read().decode()
    except OSError:
        return None
    totals = {"accept": 0.0, "reject": 0.0}
    for outcome, value in VERIFY.findall(text):
        totals[outcome] += float(value)
    return totals["accept"], totals["reject"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("port")
    parser.add_argument("--model", default=SERVED_MODEL_NAME)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--min-count-accept", type=float, help="fail if counting accepts less than this share of drafts")
    args = parser.parse_args()
    url = chat_url(args.port)
    count_accept = None
    for label, prompt in PROMPTS.items():
        body = dict(model=args.model, messages=[dict(role="user", content=prompt)], max_tokens=args.max_tokens,
                    temperature=0, seed=31, stream=True, chat_template_kwargs={"enable_thinking": False},
                    stream_options={"include_usage": True})
        before = verify_counts(url)
        result = run(url, json.dumps(body, separators=(",", ":")).encode())
        after = verify_counts(url)
        if before and after and sum(after) > sum(before):
            accepted, rejected = after[0] - before[0], after[1] - before[1]
            result["draft_accept"] = accepted / (accepted + rejected)
            if label == "count":
                count_accept = result["draft_accept"]
        print(json.dumps(dict(probe=label, **result)), flush=True)
    if args.min_count_accept is not None and (count_accept is None or count_accept < args.min_count_accept):
        sys.exit(f"counting accepted {count_accept} of drafts, below {args.min_count_accept}")


if __name__ == "__main__":
    main()
