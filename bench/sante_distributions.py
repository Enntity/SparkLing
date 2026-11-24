# SPDX-License-Identifier: AGPL-3.0-only
"""Compare matched Air-VL next-token distributions and cold single-request prefill."""
import argparse
import hashlib
import json
import random
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PROMPTS = (
    "Synthetic laboratory inventory. Tube A is blue. Tube B is red. The color of tube B is",
    "In the phrase 'left lower lobe', the word describing the side is",
    "Synthetic chart. Samples were received on Tuesday and logged two days later, on",
    "Of these two labels, control and placebo, the label listed first was",
    "The study listed three stages: collection, storage, and",
    "A technician wrote: the measurement was repeated to improve",
    "A report contains rows A17, A21, and A29. The middle row is",
    "The table summarizes counts by specimen type. A natural title for the table is",
)
PASSAGE = ("Synthetic accession log. A technician received two tubes on Tuesday. "
           "The blue tube carried label B17, and the red tube carried label K42. "
           "Before storage, both barcodes were checked against the manifest. "
           "A second reader independently transcribed the labels. When the two readings "
           "agreed, the inventory system recorded the shelf and time of entry.")


def measure(port, prompt, scores=False, echo=False):
    body = dict(model="lingsante-air-vl", prompt=prompt, max_tokens=1, temperature=0, seed=31)
    if scores:
        body["logprobs"] = 5
    if echo:
        body["echo"] = True
    data = json.dumps(body, separators=(",", ":")).encode()
    req = Request(f"http://127.0.0.1:{port}/v1/completions", data, {"Content-Type": "application/json"})
    start = time.perf_counter()
    with urlopen(req, timeout=480) as response:
        result = json.load(response)
    elapsed = time.perf_counter() - start
    return dict(request_sha256=hashlib.sha256(data).hexdigest(), prompt=prompt if scores else len(prompt),
                seconds=elapsed, choice=result["choices"][0], usage=result["usage"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", type=int)
    parser.add_argument("kind", choices=("quality", "prefill"))
    args = parser.parse_args()
    if args.kind == "quality":
        for prompt in PROMPTS:
            print(json.dumps(measure(args.port, prompt, scores=True)), flush=True)
        try:
            print(json.dumps(measure(args.port, PASSAGE, scores=True, echo=True)), flush=True)
        except HTTPError as error:
            print(json.dumps(dict(teacher_forced_error=str(error))), flush=True)
    else:
        for length, seed in ((512, 1485), (2048, 7123), (2048, 1193)):
            rng = random.Random(seed)
            tokens = [rng.randrange(450, 8300) for _ in range(length)]
            print(json.dumps(measure(args.port, tokens)), flush=True)


if __name__ == "__main__":
    main()
