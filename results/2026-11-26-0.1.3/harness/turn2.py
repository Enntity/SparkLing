"""usage: turn2.py PORT MODEL   Second-turn decode at one request: speed and draft acceptance of each follow-up.
Each conversation's first turn is generated, then the follow-up is sent with the full history; only
the follow-up is measured (verify counters read before and after it)."""
import json, re, sys, time, urllib.request
PORT, MODEL = sys.argv[1], sys.argv[2]
CONVS = [
    ("Write a Python function that parses ISO-8601 durations like P3DT4H.", "Now add unit tests for it with pytest."),
    ("Explain how a heat pump works, in three paragraphs.", "Now explain why it gets less efficient in very cold weather."),
    ("List ten everyday uses of vinegar.", "Expand the third and seventh items into a short paragraph each."),
    ("Draft a polite email declining a meeting invitation.", "Make it shorter and a little warmer."),
]
def counters():
    t = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/metrics").read().decode()
    get = lambda o: sum(float(m) for m in re.findall(r'atlas_spec_decode_verify_total\{[^}]*outcome="%s"[^}]*\} ([0-9.e+]+)' % o, t))
    return get("accept"), get("reject")
def chat(messages, n=320):
    body = dict(model=MODEL, messages=messages, max_tokens=n, temperature=0, chat_template_kwargs={"enable_thinking": False})
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time(); d = json.load(urllib.request.urlopen(req, timeout=600)); dt = time.time() - t0
    return d["choices"][0]["message"]["content"], d["usage"]["completion_tokens"], dt
for first, follow in CONVS:
    msgs = [{"role": "user", "content": first}]
    answer, _, _ = chat(msgs)
    msgs += [{"role": "assistant", "content": answer}, {"role": "user", "content": follow}]
    a0, r0 = counters(); _, n, dt = chat(msgs); a1, r1 = counters()
    acc = (a1 - a0) / max(1, (a1 - a0) + (r1 - r0))
    print(json.dumps(dict(prompt=follow[:30], tokens=n, tok_s=round(n / dt, 1), accept=round(acc, 3))), flush=True)
