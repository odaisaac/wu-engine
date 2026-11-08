#!/usr/bin/env python3
"""Pre-render plan check: catches slideshow-feeling plans and retention gaps before credits/render time are spent.

  python3 tools/plancheck.py FILM

Reads spec.json (+ timing.json if present). Prints PASS/WARN lines and a score; exit 0 always.
Checks (retention rules distilled from long-form YouTube benchmarks):
  hook      — a question or surprise in the first 30 s, title card by ~0:45
  rehooks   — a question / "but" turn / reveal at least every ~90 s (the 2–3 min valley especially)
  variety   — no 3 shots in a row of the same kind, no 2 identical overlay types back to back
  motion    — footage shots longer than ~9 s need 2+ clips (cuts per minute ≥ 4 on footage stretches)
  graphics  — every stat/bars/compare shot has a source; labels within length limits
  subscribe — subscribe card between 40% and 65% of runtime
  practical — at least one practical / hopeful section near the end
"""
import json, os, re, sys

film = sys.argv[1]
spec = json.load(open(os.path.join(film, "spec.json")))
S = spec["shots"]
T = {t["id"]: t for t in json.load(open(os.path.join(film, "timing.json")))["shots"]} if os.path.exists(os.path.join(film, "timing.json")) else {}
FJ = json.load(open(os.path.join(film, "files.json"))) if os.path.exists(os.path.join(film, "files.json")) else {}
fps = 30
starts, acc = {}, 0.0
for s in S:
    d = T[s["id"]]["dur"] / fps if s["id"] in T else len(s.get("text", "").split()) / 2.4 + 0.6
    starts[s["id"]] = acc; acc += d
total = acc
warn, ok = [], []
W = lambda m: warn.append(m)
P = lambda m: ok.append(m)
HOOK = re.compile(r"\?|\bbut\b|\byet\b|\bwhat if\b|\bhere'?s\b|\bthe (real|strange|surprising)\b|\bturns out\b|\bnever\b", re.I)

# hook
early = " ".join(s.get("text", "") for s in S if starts[s["id"]] < 30)
(P if HOOK.search(early) else W)("hook: first 30 s " + ("has a question/turn" if HOOK.search(early) else "has no question or surprise — open with tension"))
intro = next((s for s in S if s.get("kind") == "intro"), None)
if intro:
    (P if starts[intro["id"]] <= 50 else W)(f"title card at {starts[intro['id']]:.0f}s" + ("" if starts[intro["id"]] <= 50 else " — move it before ~0:45"))
# re-hooks
marks = [starts[s["id"]] for s in S if HOOK.search(s.get("text", "")) or (s.get("overlay") or {}).get("type") in ("stat", "map", "quote")]
gaps = [(a, b) for a, b in zip([0] + marks, marks + [total]) if b - a > 95]
for a, b in gaps:
    W(f"rehook gap {a / 60:.1f}–{b / 60:.1f} min ({b - a:.0f}s) — add a question, a 'but…' turn or a reveal")
if not gaps:
    P("rehooks: no gap over 95 s")
# variety
for i in range(2, len(S)):
    if S[i].get("kind") == S[i - 1].get("kind") == S[i - 2].get("kind") and S[i].get("kind") == "graphic":
        W(f"variety: 3 graphic shots in a row at {S[i - 2]['id']}–{S[i]['id']}")
for i in range(1, len(S)):
    a, b = (S[i - 1].get("overlay") or {}).get("type"), (S[i].get("overlay") or {}).get("type")
    if a and a == b and a not in ("kinetic", "none", "lower"):
        W(f"variety: two '{a}' overlays back to back at {S[i - 1]['id']}/{S[i]['id']}")
# motion on footage
for s in S:
    if s.get("kind") == "footage":
        d = T[s["id"]]["dur"] / fps if s["id"] in T else 0
        n = len(FJ.get(s["id"], s.get("files", [])) or [])
        if d > 9 and n and n < 2:
            W(f"motion: shot {s['id']} is {d:.0f}s on one clip — add a second clip")
cuts = sum(max(1, len(FJ.get(s["id"], []) or [1])) for s in S)
cpm = cuts / (total / 60)
(P if cpm >= 4 else W)(f"pace: ~{cpm:.1f} cuts/min" + ("" if cpm >= 4 else " — documentary channels run 6–12; add clips or split long shots"))
# graphics hygiene
for s in S:
    ov = s.get("overlay") or {}
    if ov.get("type") in ("stat", "bars", "compare", "map") and not s.get("source") and s.get("kind") == "graphic" and ov.get("type") != "map":
        W(f"source: shot {s['id']} ({ov['type']}) has no on-screen source")
    if ov.get("type") == "stat" and len(ov.get("label", "")) > 70:
        W(f"label: shot {s['id']} stat label {len(ov['label'])} chars (max 70)")
    for it in ov.get("items", []) if ov.get("type") == "bars" else []:
        if len(it.get("label", "")) > 22:
            W(f"label: shot {s['id']} bar label '{it['label']}' > 22 chars")
    if re.search(r"\bact \d\b", json.dumps(ov), re.I) or re.search(r"\bact (one|two|three|four|five|\d)\b", s.get("text", ""), re.I):
        W(f"acts: shot {s['id']} mentions an act — acts are planning only")
# subscribe
sub = next((s for s in S if s.get("kind") == "subscribe"), None)
if not sub:
    W("subscribe: no subscribe card")
else:
    r = starts[sub["id"]] / total
    (P if 0.4 <= r <= 0.65 else W)(f"subscribe at {r:.0%} of runtime" + ("" if 0.4 <= r <= 0.65 else " — move to 40–65%"))
# practical / hopeful ending
tail = " ".join(s.get("text", "") for s in S if starts[s["id"]] > total * 0.7).lower()
(P if re.search(r"\b(you can|what helps|solution|plan|try|change|protect|reclaim|take back)\b", tail) else W)("practical/hopeful section in the last 30%")

score = max(0, 100 - 8 * len(warn))
print(f"PLAN CHECK {os.path.basename(os.path.abspath(film))}: {score}/100  ({total / 60:.1f} min, {len(S)} shots)")
for m in ok:
    print("  PASS", m)
for m in warn:
    print("  WARN", m)
