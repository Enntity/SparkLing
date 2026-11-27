# usage: note_replay.py [cold]  replay the demo's x-ray read then the forced-tool note (as app.js sends them)
import base64, json, os, sys, urllib.request
# The demo's images (demo/lingsante/data); DEMO_DATA overrides.
D = os.environ.get("DEMO_DATA", os.path.join(os.path.dirname(__file__), "../../../demo/lingsante/data")) + "/"
url = lambda f, m: f"data:{m};base64," + base64.b64encode(open(D + f, "rb").read()).decode()
xray, labs = url("cxr-lll-pneumonia-effusion-1024.jpg", "image/jpeg"), url("labs-1182.png", "image/png")
TOOL = {"type": "function", "function": {"name": "file_encounter_note", "description": "File a structured emergency-department encounter note into the chart.",
  "parameters": {"type": "object", "properties": {"working_diagnosis": {"type": "string"}, "imaging_findings": {"type": "array", "items": {"type": "string"}},
    "critical_lab_values": {"type": "array", "items": {"type": "string"}, "description": "Abnormal values with numbers and units"},
    "severity": {"type": "string", "description": "Severity assessment with the score used"}, "orders": {"type": "array", "items": {"type": "string"}},
    "disposition": {"type": "string"}}, "required": ["working_diagnosis", "imaging_findings", "critical_lab_values", "severity", "orders", "disposition"]}}}
def post(body):
    body = {"model": "lingsante-3.1-air-vl-atlas", "temperature": 0, "seed": 31, "stream": True, "stream_options": {"include_usage": True}, **body}
    r = urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8897/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=600)
    text, args, usage, fin = "", "", None, None
    for line in r:
        line = line.decode().strip()
        if not line.startswith("data:") or line.endswith("[DONE]"): continue
        d = json.loads(line[5:]); usage = d.get("usage") or usage
        for c in d.get("choices", []):
            fin = c.get("finish_reason") or fin; dl = c.get("delta", {})
            text += dl.get("content") or ""
            args += "".join((t.get("function") or {}).get("arguments") or "" for t in dl.get("tool_calls") or [])
    return text, args, usage, fin
if sys.argv[1:] != ["cold"]:
    t, _, u, f = post({"max_tokens": 220, "chat_template_kwargs": {"enable_thinking": False}, "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": xray}}, {"type": "text", "text": "You are reviewing a chest radiograph. List the key findings (location, type, side) and your impression in 4 short bullet points."}]}]})
    print("xray", f, u and u.get("completion_tokens"), repr(t[:80]))
t, a, u, f = post({"max_tokens": 800, "chat_template_kwargs": {"enable_thinking": False}, "tools": [TOOL],
    "tool_choice": {"type": "function", "function": {"name": "file_encounter_note"}}, "stream_tool_arguments": True,
    "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": xray}}, {"type": "image_url", "image_url": {"url": labs}},
      {"type": "text", "text": "Emergency department, 71-year-old man with 3 days of cough, fever and dyspnea. The first image is his chest radiograph and the second his admission labs. Interpret both and file the encounter note."}]}]})
print("note", f, u and (u.get("prompt_tokens"), u.get("completion_tokens"), (u.get("prompt_tokens_details") or {}).get("cached_tokens")), "args", len(a), "text", len(t), repr((a or t)[:200]))
