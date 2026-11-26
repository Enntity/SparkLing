// SPDX-License-Identifier: AGPL-3.0-only
// LingSante demo director: three live scenes against the local SparkLing engine.
const MODEL = new URLSearchParams(location.search).get("model") || "lingsante-air-vl";
const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const results = {};

function esc(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
function md(text) {
  return esc(text).split("\n").map((line) => {
    let l = line.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/^#+\s*/, "");
    if (/^\s*([-*•]|\d+\.)\s+/.test(l)) return `<div class="li">${l.replace(/^\s*[-*•]\s+/, "• ")}</div>`;
    return l.trim() ? `<div>${l}</div>` : `<div style="height:6px"></div>`;
  }).join("");
}

// Stream one chat completion; returns timing, usage, text and tool arguments.
const request = (body) => ({ model: MODEL, temperature: 0, seed: 31, stream: true, ...body });

async function* sseLines(resp) {
  const reader = resp.body.getReader(), dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
      if (line.startsWith("data:") && !line.endsWith("[DONE]")) yield JSON.parse(line.slice(5));
    }
  }
}

// Accumulates one streamed completion: timing, usage, text and tool arguments.
function collector(onText, onTool, t0 = performance.now()) {
  const r = { ttft: null, total: null, usage: null, text: "", args: "", gen: null };
  r.add = (d) => {
    if (d.usage) r.usage = d.usage;
    const delta = d.choices && d.choices[0] && d.choices[0].delta;
    if (!delta) return;
    const piece = delta.content || "";
    const tool = (delta.tool_calls || []).map((c) => (c.function && c.function.arguments) || "").join("");
    if ((piece || tool) && r.ttft === null) r.ttft = performance.now() - t0;
    if (piece) { r.text += piece; onText && onText(r.text); }
    if (tool) { r.args += tool; onTool && onTool(r.args); }
  };
  r.end = () => {
    r.total = performance.now() - t0;
    if (r.usage && r.ttft !== null) r.gen = r.usage.completion_tokens / Math.max(0.001, (r.total - r.ttft) / 1000);
    return r;
  };
  return r;
}

async function stream(body, onText, onTool) {
  const r = collector(onText, onTool);
  const resp = await fetch("/v1/chat/completions", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request(body)) });
  for await (const d of sseLines(resp)) r.add(d);
  return r.end();
}

// Many completions at once through the demo server's /fanout (a browser opens only six per host).
async function streamMany(bodies, onText) {
  const t0 = performance.now();
  const rs = bodies.map((_, i) => collector((t) => onText(i, t), null, t0));
  const resp = await fetch("/fanout", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(bodies.map(request)) });
  for await (const m of sseLines(resp)) {
    if (m.line.startsWith("data:") && !m.line.endsWith("[DONE]")) rs[m.i].add(JSON.parse(m.line.slice(5)));
  }
  return rs.map((r) => r.end());
}

function ticker(el, prefix) {
  const t0 = performance.now();
  const id = setInterval(() => { el.textContent = `${prefix} ${((performance.now() - t0) / 1000).toFixed(1)} s`; }, 100);
  return () => clearInterval(id);
}
function follow(el) { el.scrollTop = el.scrollHeight; const p = el.parentElement; if (p) p.scrollTop = p.scrollHeight; }
async function show(id) {
  document.querySelectorAll(".scene").forEach((s) => s.classList.remove("on"));
  await sleep(350); $(id).classList.add("on"); await sleep(650);
}
async function typeInto(el, text, ms = 22) { for (let i = 1; i <= text.length; i++) { el.innerHTML = text.slice(0, i); await sleep(ms); } }
const fmt = (n) => n.toLocaleString("en-US");

// ---- scene 1: chart review -------------------------------------------------
const REVIEW = "You are a careful internal-medicine reviewer preparing for today's visit. Using only the chart above, " +
  "answer each check in turn, quoting the chart evidence with dates.\n" +
  "(a) Follow-up studies recommended in any report that were never done.\n" +
  "(b) Her most recent eGFR and its date, then only the medications that are contraindicated or need a renal dose change at that eGFR, one line each.\n" +
  "(c) Dangerous drug combinations.\n" +
  "(d) Worrying lab trends.\n" +
  "Finish with: Actions today, the three most urgent, one line each. English only, concise.";
const FOLLOW = "She sees orthopedics next week for her knees. What should she use for knee pain instead of ibuprofen? Three short bullets.";

async function sceneChart() {
  await show("s1");
  const chart = `Record export ${Date.now()}\n` + await (await fetch("data/chart.txt")).text();
  const pre = $("c-chart"); pre.textContent = chart;
  const out = $("c-out"), status = $("c-status");
  let reading = true;
  (async () => { const t0 = performance.now(), h = pre.scrollHeight - pre.clientHeight;
    while (reading) { pre.scrollTop = h * Math.min(1, (performance.now() - t0) / 25000); await sleep(30); } })();
  const stop = ticker(status, "reading chart…");
  let started = false;
  const messages = [{ role: "user", content: chart + "\n\n" + REVIEW }];
  const r = await stream({ max_tokens: 1400, chat_template_kwargs: { enable_thinking: false }, messages },
    (t) => { if (!started) { started = true; reading = false; stop(); status.textContent = "answering"; out.classList.add("cursor"); }
      out.innerHTML = md(t); follow(out); });
  out.classList.remove("cursor"); stop();
  status.textContent = `done in ${(r.total / 1000).toFixed(1)} s`;
  const read = r.ttft / 1000;
  $("m1-tok").textContent = fmt(r.usage.prompt_tokens);
  $("m1-read").textContent = `${read.toFixed(1)} s`;
  $("m1-rate").textContent = `${fmt(Math.round(r.usage.prompt_tokens / read))} tok/s`;
  $("m1-gen").textContent = `${r.gen.toFixed(1)} tok/s`;
  results.review = r.text;
  Object.assign(results, { chartTokens: r.usage.prompt_tokens, chartRead: read, chartGen: r.gen });
  await sleep(2500);
  // Follow-up: the chart and the review are already in the prefix cache.
  $("c-fu").style.display = "block";
  follow(out);
  await typeInto($("c-fu-q"), `<b>Q:</b> ${FOLLOW}`, 18);
  const fout = $("c-fu-out"), fst = $("c-fu-status");
  const stop2 = ticker(fst, "thinking…");
  messages.push({ role: "assistant", content: r.text }, { role: "user", content: FOLLOW });
  let s2 = false;
  const f = await stream({ max_tokens: 220, chat_template_kwargs: { enable_thinking: false }, messages },
    (t) => { if (!s2) { s2 = true; stop2(); fst.textContent = "chart already cached"; } fout.innerHTML = md(t); });
  stop2();
  fst.textContent = `first token ${(f.ttft / 1000).toFixed(1)} s · ${fmt(f.usage.prompt_tokens)}-token context`;
  $("m1-fu").textContent = `${(f.ttft / 1000).toFixed(1)} s`;
  results.followTtft = f.ttft / 1000; results.follow = f.text;
  await sleep(5000);
}

// ---- scene 2: imaging + labs ------------------------------------------------
const TOOL = { type: "function", function: { name: "file_encounter_note",
  description: "File a structured emergency-department encounter note into the chart.",
  parameters: { type: "object", properties: {
    working_diagnosis: { type: "string" },
    imaging_findings: { type: "array", items: { type: "string" } },
    critical_lab_values: { type: "array", items: { type: "string" }, description: "Abnormal values with numbers and units" },
    severity: { type: "string", description: "Severity assessment with the score used" },
    orders: { type: "array", items: { type: "string" } },
    disposition: { type: "string" } },
    required: ["working_diagnosis", "imaging_findings", "critical_lab_values", "severity", "orders", "disposition"] } } };

async function dataUrl(path) {
  const blob = await (await fetch(path)).blob();
  return await new Promise((res) => { const r = new FileReader(); r.onload = () => res(r.result); r.readAsDataURL(blob); });
}
function list(v) { return (Array.isArray(v) ? v : String(v).split(/;\s*/)).filter(Boolean).map((x) => `<li>${esc(x)}</li>`).join(""); }

async function sceneImaging() {
  await show("s2");
  const xray = await dataUrl("data/cxr-lll-pneumonia-effusion-1024.jpg"), labs = await dataUrl("data/labs-1182.png");
  const xo = $("x-out"), xs = $("x-status");
  const stop = ticker(xs, "reading film…");
  let s = false;
  const r = await stream({ max_tokens: 220, chat_template_kwargs: { enable_thinking: false }, messages: [{ role: "user", content: [
      { type: "image_url", image_url: { url: xray } },
      { type: "text", text: "You are reviewing a chest radiograph. List the key findings (location, type, side) and your impression in 4 short bullet points." }] }] },
    (t) => { if (!s) { s = true; stop(); xs.textContent = "reading"; } xo.innerHTML = md(t); });
  stop(); xs.textContent = `first token ${(r.ttft / 1000).toFixed(1)} s · done in ${(r.total / 1000).toFixed(1)} s`;
  results.xrayTtft = r.ttft / 1000; results.xrayTotal = r.total / 1000; results.xray = r.text;
  await sleep(1500);
  const no = $("n-out"), ns = $("n-status");
  const stop2 = ticker(ns, "reading film + labs, writing the note…");
  let s2 = false;
  const n = await stream({ max_tokens: 800, chat_template_kwargs: { enable_thinking: false }, tools: [TOOL],
      tool_choice: { type: "function", function: { name: "file_encounter_note" } }, stream_tool_arguments: true,
      messages: [{ role: "user", content: [{ type: "image_url", image_url: { url: xray } }, { type: "image_url", image_url: { url: labs } },
        { type: "text", text: "Emergency department, 71-year-old man with 3 days of cough, fever and dyspnea. The first image is his chest " +
          "radiograph and the second his admission labs. Interpret both and file the encounter note." }] }] },
    null, (a) => { if (!s2) { s2 = true; stop2(); ns.textContent = "writing the note"; } no.textContent = a; follow(no); });
  stop2();
  let note;
  try { note = JSON.parse(n.args); } catch (e) { note = null; }
  ns.textContent = `${fmt(n.usage.completion_tokens)} tokens in ${(n.total / 1000).toFixed(1)} s · checked by the tool guard`;
  results.noteTotal = n.total / 1000; results.note = n.args;
  if (note) {
    await sleep(1200);
    no.classList.remove("mono"); no.style.whiteSpace = "normal";
    no.innerHTML = `<div class="card"><h3>${esc(note.working_diagnosis || "")}</h3><div class="cols"><div>
      <div class="k">Imaging</div><ul>${list(note.imaging_findings)}</ul>
      <div class="k">Severity</div><div>${esc(note.severity || "")}</div>
      <div class="k">Disposition</div><div>${esc(note.disposition || "")}</div></div><div>
      <div class="k">Critical values</div><ul>${list(note.critical_lab_values)}</ul>
      <div class="k">Orders</div><ul>${list(note.orders)}</ul></div></div></div>`;
  }
  await sleep(6000);
}

// ---- scene 3: eight patients at once ---------------------------------------
const ESI_COLORS = { 1: "#ff5a5a", 2: "#ff9f43", 3: "#ffd166", 4: "#5ad1c8", 5: "#7aa2ff" };

async function sceneTriage() {
  await show("s3");
  const cases = await (await fetch("data/cases.json")).json();
  const grid = $("t-grid");
  grid.innerHTML = cases.map((c, i) => `<div class="panel case"><div class="who">${esc(c.id)}</div>
    <div class="txt">${esc(c.text)}</div><div class="out" id="t-out-${i}"></div></div>`).join("");
  await sleep(1500);
  const t0 = performance.now();
  const stop = ticker($("m3-time"), "");
  const done = await streamMany(cases.map((c) => ({ max_tokens: 150, chat_template_kwargs: { enable_thinking: false }, messages: [
      { role: "system", content: "You are an experienced emergency department triage nurse." },
      { role: "user", content: "Triage this patient. Reply in exactly three lines:\nESI: <1-5>\nWhy: <one sentence>\n" +
        "First action: <one sentence>\n\nPatient: " + c.text }] })),
    (i, t) => {
      const m = t.match(/ESI:\s*(\d)/);
      const body = md(t.replace(/^.*ESI:\s*\d[^\n]*\n?/, ""));
      $(`t-out-${i}`).innerHTML = (m ? `<span class="esi" style="background:${ESI_COLORS[m[1]] || "#888"};color:#0b1220">ESI ${m[1]}</span>` : "") + body;
    });
  stop();
  const wall = (performance.now() - t0) / 1000;
  const tokens = done.reduce((a, r) => a + (r.usage ? r.usage.completion_tokens : 0), 0);
  const firstAll = Math.max(...done.map((r) => r.ttft)) / 1000, firstAny = Math.min(...done.map((r) => r.ttft)) / 1000;
  const agg = tokens / (wall - firstAny);
  $("m3-first").textContent = `${firstAll.toFixed(1)} s`;
  $("m3-time").textContent = `${wall.toFixed(1)} s`;
  $("m3-agg").textContent = `${Math.round(agg)} tok/s`;
  results.triage = done.map((r) => r.text);
  Object.assign(results, { triageWall: wall, triageAgg: agg, triageFirst: firstAll });
  await sleep(6000);
}

// ---- recap -----------------------------------------------------------------
async function sceneRecap() {
  const items = [
    [`${fmt(results.chartTokens)} tokens`, `six-year chart read in ${results.chartRead.toFixed(1)} s, safety review at ${results.chartGen.toFixed(0)} tok/s`],
    [`${results.followTtft.toFixed(1)} s`, "to the first token of a follow-up question about that chart"],
    [`${results.xrayTotal.toFixed(1)} s`, "for a chest radiograph read; a structured note from film plus labs as a tool call"],
    [`8 at once`, `every patient answering within ${results.triageFirst.toFixed(1)} s, all eight triaged in ${results.triageWall.toFixed(1)} s`],
  ];
  $("recap").innerHTML = items.map(([v, k]) => `<div class="metric"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join("");
  await show("s4");
  await sleep(9000);
}

async function run() {
  await show("s0"); await sleep(5500);
  await sceneChart();
  await sceneImaging();
  await sceneTriage();
  await sceneRecap();
  window.__results = results; window.__done = true;
}
window.__done = false;
if (new URLSearchParams(location.search).get("autoplay") === "1") run();
else document.addEventListener("keydown", (e) => { if (e.key === " ") run(); }, { once: true });
