# SPDX-License-Identifier: AGPL-3.0-only
"""Serve the LingSante demo page and stream /v1/* to the local SparkLing engine.
usage: server.py [PORT] [ENGINE_PORT]"""
import http.client
import http.server
import json
import os
import queue
import sys
import threading

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8700
ENGINE = int(sys.argv[2]) if len(sys.argv) > 2 else 8897
ROOT = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/fanout":
            return self.fanout(json.loads(body))
        if not self.path.startswith("/v1/"):
            self.send_error(404)
            return
        upstream = http.client.HTTPConnection("127.0.0.1", ENGINE, timeout=1800)
        upstream.request("POST", self.path, body, {"Content-Type": "application/json"})
        resp = upstream.getresponse()
        self.send_response(resp.status)
        self.send_header("Content-Type", resp.getheader("Content-Type", "application/json"))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        while True:
            chunk = resp.read1(65536) if hasattr(resp, "read1") else resp.read(65536)
            if not chunk:
                break
            self.wfile.write(chunk)
            self.wfile.flush()
        upstream.close()

    def fanout(self, bodies):
        """Send every request to the engine at once (a browser allows six per host) and
        interleave their SSE lines as {"i": index, "line": ...}."""
        lines = queue.Queue()

        def one(i, req):
            upstream = http.client.HTTPConnection("127.0.0.1", ENGINE, timeout=1800)
            upstream.request("POST", "/v1/chat/completions", json.dumps(req), {"Content-Type": "application/json"})
            for raw in upstream.getresponse():
                if raw.strip():
                    lines.put((i, raw.decode().strip()))
            upstream.close()
            lines.put((i, None))

        for i, req in enumerate(bodies):
            threading.Thread(target=one, args=(i, req), daemon=True).start()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        left = len(bodies)
        while left:
            i, line = lines.get()
            if line is None:
                left -= 1
                continue
            self.wfile.write(("data: " + json.dumps({"i": i, "line": line}) + "\n").encode())
            self.wfile.flush()


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
