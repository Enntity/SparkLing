# SPDX-License-Identifier: AGPL-3.0-only
"""Streamed tool call: how many argument chunks arrive, and the joined arguments."""
import json, urllib.request

from _common import SERVED_MODEL_NAME, chat_url

URL = chat_url()
tools = [{"type": "function", "function": {"name": "Say", "description": "Speak text aloud to the user.", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}}]
for extra in ({"chat_template_kwargs": {"enable_thinking": True}}, {"chat_template_kwargs": {"enable_thinking": False}}):
    b = {"model": SERVED_MODEL_NAME, "stream": True, "stream_tool_arguments": True, "temperature": 0, "max_tokens": 600, "tools": tools, "tool_choice": "auto",
         "messages": [{"role": "system", "content": "Always answer by calling Say."}, {"role": "user", "content": "Tell me a short story about a cat, three sentences."}], **extra}
    chunks, args = 0, ""
    for line in urllib.request.urlopen(urllib.request.Request(URL, json.dumps(b).encode(), {"Content-Type": "application/json"}), timeout=600):
        line = line.decode().strip()
        if not line.startswith("data: ") or line == "data: [DONE]": continue
        for c in json.loads(line[6:]).get("choices", []):
            for tc in (c.get("delta") or {}).get("tool_calls") or []:
                a = (tc.get("function") or {}).get("arguments")
                if a: chunks += 1; args += a
    ok = isinstance(json.loads(args).get("text"), str) if args else False
    print(list(extra)[0], "arg chunks", chunks, "valid", ok, args[:80])
