# SPDX-License-Identifier: AGPL-3.0-only
"""Check document and video reading on the local SparkLing chat endpoint."""
import argparse
import base64
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

from _common import SERVED_MODEL_NAME, chat_url

HERE = Path(__file__).resolve().parent
VIDEO_PROMPT = "Name the first and last colors shown in the video, in order. Use two words."
COUNT_PROMPT = ("A large number is shown in the video and it changes over time. "
                "List every number you see, in the order they appear, separated by commas.")
CASES = {
    "invoice": ("images/invoice.png", "image/png",
                "Transcribe the supplier name, invoice number, and total as printed. Answer concisely."),
    "grid": ("images/grid.png", "image/png", "Read the labelled grid. Give the color of cells A1, B2 and C3."),
    "gif": ("video/red-blue.gif", "image/gif", VIDEO_PROMPT),
    "mp4": ("video/red-blue.mp4", "video/mp4", VIDEO_PROMPT),
    # Eight one-second frames numbered 1 to 8: temporal order and reading.
    "gif-count": ("video/count8.gif", "image/gif", COUNT_PROMPT),
    "mp4-count": ("video/count8.mp4", "video/mp4", COUNT_PROMPT),
}


def correct(case, answer):
    answer = answer.lower().translate(str.maketrans("", "", "*_`"))
    if case == "invoice":
        return all(field in answer for field in ("harbor street bakery", "48213", "66.15"))
    if case == "grid":
        return all(re.search(label + r"[^a-z0-9]{0,12}(?:is\s+)?" + color + r"\b", answer)
                   for label, color in (("a1", "red"), ("b2", "blue"), ("c3", "green")))
    if case.endswith("-count"):
        return re.findall(r"\d", answer) == list("12345678")
    return re.findall(r"\b(?:red|blue)\b", answer) == ["red", "blue"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port")
    parser.add_argument("cases", nargs="+", choices=CASES)
    parser.add_argument("--model", default=SERVED_MODEL_NAME)
    args = parser.parse_args()
    passed = True
    for case in args.cases:
        path, mime, prompt = CASES[case]
        data = base64.b64encode((HERE/path).read_bytes()).decode()
        video = mime != "image/png"
        field = "video_url" if video else "image_url"
        media = {"type": field, field: {"url": f"data:{mime};base64,{data}"}}
        content = [media, {"type": "text", "text": prompt}]
        body = {"model": args.model, "temperature": 0, "seed": 31, "max_tokens": 32 if video else 96,
                "messages": [{"role": "user", "content": content}],
                "chat_template_kwargs": {"enable_thinking": False}}
        request = urllib.request.Request(chat_url(args.port), json.dumps(body).encode(),
                                         {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                message = json.load(response)
            answer = message["choices"][0]["message"].get("content") or ""
            result = {"answer": answer, "usage": message["usage"], "passed": correct(case, answer)}
        except urllib.error.HTTPError as error:
            result = {"status": error.code, "error": error.read().decode(), "passed": False}
        print(json.dumps({"case": case, **result}), flush=True)
        passed &= result["passed"]
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
