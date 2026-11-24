# SPDX-License-Identifier: AGPL-3.0-only
"""Run the paired Air-VL text/image probes or the short streamed decode check."""
import argparse
import base64
import hashlib
import json
import struct
import urllib.request
import zlib

from _common import chat_url
from short_decode import run as stream_decode


def blue_square():
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    side = 112
    pixels = (b"\0" + bytes([0, 0, 255]) * side) * side
    header = struct.pack(">IIBBBBB", side, side, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(png).decode()


def request(content, limit, stream=False):
    body = dict(model="lingsante-air-vl", messages=[dict(role="user", content=content)],
                max_tokens=limit, temperature=0, seed=31, stream=stream,
                chat_template_kwargs={"enable_thinking": False})
    if stream:
        body["stream_options"] = {"include_usage": True}
    return json.dumps(body, separators=(",", ":")).encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port")
    parser.add_argument("mode", choices=["parity", "speed"])
    args = parser.parse_args()
    url = chat_url(args.port)
    if args.mode == "speed":
        body = request("Count upward from one using English words separated by commas. Continue through one hundred.",
                       64, stream=True)
        for _ in range(2):
            print(json.dumps(stream_decode(url, body)), flush=True)
        return

    probes = {
        "text": "What is 17 times 23? Reply with only the number.",
        "image": [{"type": "image_url", "image_url": {"url": blue_square()}},
                  {"type": "text", "text": "What single color fills this image? Reply with one word."}],
    }
    for label, content in probes.items():
        body = request(content, 16)
        req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=1800) as response:
            result = json.load(response)
        choice = result["choices"][0]
        print(json.dumps(dict(probe=label, request_sha256=hashlib.sha256(body).hexdigest(),
                              answer=choice["message"]["content"], usage=result["usage"],
                              finish_reason=choice["finish_reason"])), flush=True)


if __name__ == "__main__":
    main()
