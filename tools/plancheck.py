#!/usr/bin/env python3
"""Pre-render plan check: catches slow, report-like plans and retention gaps before credits/render time are spent.

  python3 tools/plancheck.py FILM

Reads spec.json (+ timing.json / files.json if present). Prints PASS/WARN lines and a score; exit 0 always.
Rules come from comparing our films with small-channel breakout documentaries (Nov 2026):
  hook      — first sentence short; a number or "you" in the first 15 s; no "Picture…/Welcome…" warm-up;
              no channel intro ("This is The World Unpacked…") and no full-screen logo card in the first minute
  title     — the title appears as an overlay on footage by ~0:45 (overlay type "title"), not as a logo card
  pace      — the picture changes every ~5 s on average; no footage hold over 6.5 s, no still graphic over 8 s
              (add clips, or "then" overlay beats; a beat starts at "cue": sentence index or "on": spoken word); shots of 45+ words are split
  rehooks   — a question / "but" turn / reveal at least every ~75 s
  stakes    — the script speaks to the viewer ("you/your") at least ~1.5 times a minute
  language  — average sentence ≤ 17 words, none over 30
  length    — at least the target length (spec "targetMin", default 11 minutes)
  variety   — no 3 graphic shots in a row, no 2 identical overlay types back to back
  graphics  — every stat/bars/compare shot has a source; labels within length limits; no "Act" labels
  subscribe — a corner nudge ("nudge": true) at 30–65 % of runtime; a full-screen subscribe card is flagged
  ending    — a practical / hopeful section in the last 30 %; the end card sends viewers to another video
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cues import clips_for, shot_beats  # noqa: E402

film = sys.argv[1]
spec = json.load(open(os.path.join(film, "spec.json")))
S = spec["shots"]
T = {t["id"]: t for t in json.load(open(os.path.join(film, "timing.json")))["shots"]} if os.path.exists(os.path.join(film, "timing.json")) else {}
FJ = json.load(open(os.path.join(film, "files.json"))) if os.path.exists(os.path.join(film, "files.json")) else {}
fps = 30
CUT = float(spec.get("cutEvery", 4.5))
starts, durs, acc = {}, {}, 0.0
for s in S:
    d = T[s["id"]]["dur"] / fps if s["id"] in T else (len(s.get("text", "").split()) / 2.5 + 0.6 if s.get("text") else s.get("seconds", 4))
    starts[s["id"]] = acc; durs[s["id"]] = d; acc += d
total = acc
warn, ok = [], []
W = lambda m: warn.append(m)
P = lambda m: ok.append(m)
C = lambda cond, good, bad: (P if cond else W)(good if cond else bad)
HOOK = re.compile(r"\?|\bbut\b|\byet\b|\bwhat if\b|\bhere'?s\b|\bthe (real|strange|surprising)\b|\bturns out\b|\bnever\b|\buntil\b|\bexcept\b", re.I)
NUM = re.compile(r"\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion|half|percent)\b", re.I)
YOU = re.compile(r"\b(you|your|yours|you're|you'll|you've)\b", re.I)
sentences = lambda txt: [x for x in re.split(r"(?<=[.!?])\s+", txt.strip()) if x]
script = " ".join(s.get("text", "") for s in S)

# ---- hook
early = " ".join(s.get("text", "") for s in S if starts[s["id"]] < 15)
first = sentences(S[0].get("text", "") or " ")[0] if S and S[0].get("text") else ""
C(len(first.split()) <= 16, f"hook: first sentence is {len(first.split())} words", f"hook: first sentence is {len(first.split())} words — open on one short, concrete line (≤ 16 words)")
C(bool(NUM.search(early) or YOU.search(early)), "hook: a number or 'you' in the first 15 s", "hook: the first 15 s has no number and no 'you' — lead with the most surprising fact and why it matters to the viewer")
if re.match(r"\s*(picture|imagine|welcome|hi\b|hello|today|in this (video|film|documentary))", S[0].get("text", ""), re.I):
    W("hook: opens with a warm-up ('Picture…', 'Welcome…', 'In this video…') — start inside the story instead")
C(bool(HOOK.search(" ".join(s.get("text", "") for s in S if starts[s["id"]] < 30))), "hook: first 30 s has a question/turn", "hook: first 30 s has no question or surprise — open with tension")
for s in S:
    if starts[s["id"]] < 90 and re.search(r"this is the world unpacked|welcome (back )?to|documentary (number )?(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b", s.get("text", ""), re.I):
        W(f"hook: shot {s['id']} is a channel intro in the first 90 s — viewers leave here; cut the line and keep the story moving")
intro = next((s for s in S if s.get("kind") == "intro"), None)
if intro and durs[intro["id"]] > 3.5:
    W(f"title: shot {intro['id']} is a {durs[intro['id']]:.0f}s full-screen logo card — show the title as an overlay on footage instead (overlay type 'title')")
titled = next((s for s in S if s.get("kind") == "intro" or any(o.get("type") == "title" for o in [s.get("overlay") or {}] + list(s.get("then") or []))), None)
C(bool(titled) and starts[titled["id"]] <= 50, f"title on screen at {starts[titled['id']]:.0f}s" if titled else "", "title: no title overlay in the first ~45 s — add overlay type 'title' on an early footage shot")

# ---- pace: how long each picture holds
ANIM = {"list", "bars", "map", "flow"}          # these keep moving on their own
units = 0
for s in S:
    k, d = s.get("kind", "graphic"), durs[s["id"]]
    t = T.get(s["id"], {"dur": round(d * fps)})
    bounds = shot_beats(s, t)
    beats = len(bounds) - 1
    if k in ("footage", "photo"):
        clips = len(FJ.get(s["id"]) or s.get("files") or []) or 1
        if k == "footage":
            clips = max(clips, clips_for(d, CUT))   # stock.py re-uses clips with a punch-in to reach the cut rate
        n = max(clips, beats); hold = d / n
        if hold > 6.5:
            W(f"pace: shot {s['id']} holds one picture for {hold:.0f}s — add clips or a 'then' beat")
    elif k == "graphic":
        ov = (s.get("overlay") or {})
        inner = len(ov.get("items") or ov.get("steps") or ov.get("points") or [1, 1]) if ov.get("type") in ANIM else 1
        n = max(beats, inner)
        beats_ov = [o for o in [s.get("overlay")] + list(s.get("then") or []) if o] or [{}]
        for o, a, b in zip(beats_ov, bounds, bounds[1:]):
            lim = 12 if o.get("type") in ANIM else 8
            if (b - a) / fps > lim + 0.5:
                W(f"pace: graphic {s['id']} ({o.get('type')}) sits for {(b - a) / fps:.0f}s — add a 'then' beat or split the shot (limit {lim}s)")
    else:
        n = 2 if k == "subscribe" else 1
    units += n
    if len(s.get("text", "").split()) > 45:
        W(f"pace: shot {s['id']} has {len(s['text'].split())} words — split it (aim for 15–30 words a shot)")
avg = total / max(1, units)
C(avg <= 5.5, f"pace: the picture changes every {avg:.1f}s on average", f"pace: the picture changes every {avg:.1f}s on average — breakout documentaries change every 3–5 s")

# ---- re-hooks
marks = [starts[s["id"]] for s in S if HOOK.search(s.get("text", "")) or (s.get("overlay") or {}).get("type") in ("stat", "map", "quote")]
gaps = [(a, b) for a, b in zip([0] + marks, marks + [total]) if b - a > 75]
for a, b in gaps:
    W(f"rehook gap {a / 60:.1f}–{b / 60:.1f} min ({b - a:.0f}s) — add a question, a 'but…' turn or a reveal")
if not gaps:
    P("rehooks: no gap over 75 s")

# ---- stakes and language
per_min = len(YOU.findall(script)) / max(0.1, total / 60)
C(per_min >= 1.5, f"stakes: 'you/your' {per_min:.1f} times a minute", f"stakes: 'you/your' only {per_min:.1f} times a minute — say what this means for the viewer (aim for 1.5+)")
sl = [len(x.split()) for x in sentences(script)]
if sl:
    C(sum(sl) / len(sl) <= 17, f"language: average sentence {sum(sl) / len(sl):.0f} words", f"language: average sentence {sum(sl) / len(sl):.0f} words — shorten (aim ≤ 17)")
    if max(sl) > 30:
        W(f"language: one sentence runs {max(sl)} words — break it up")

# ---- length
target = float(spec.get("targetMin", 11))
C(total / 60 >= target * 0.9, f"length: {total / 60:.1f} min", f"length: {total / 60:.1f} min — the target is {target:.0f}+ (breakout videos in this lane run 12–18)")

# ---- variety
for i in range(2, len(S)):
    if S[i].get("kind", "graphic") == S[i - 1].get("kind", "graphic") == S[i - 2].get("kind", "graphic") == "graphic":
        W(f"variety: 3 graphic shots in a row at {S[i - 2]['id']}–{S[i]['id']}")
for i in range(1, len(S)):
    a, b = (S[i - 1].get("overlay") or {}).get("type"), (S[i].get("overlay") or {}).get("type")
    if a and a == b and a not in ("kinetic", "none", "lower", "title"):
        W(f"variety: two '{a}' overlays back to back at {S[i - 1]['id']}/{S[i]['id']}")

# ---- graphics hygiene
for s in S:
    for ov in [s.get("overlay") or {}] + list(s.get("then") or []):
        if ov.get("type") in ("stat", "bars", "compare") and not s.get("source") and s.get("kind", "graphic") == "graphic":
            W(f"source: shot {s['id']} ({ov['type']}) has no on-screen source")
        if ov.get("type") == "stat" and len(ov.get("label", "")) > 70:
            W(f"label: shot {s['id']} stat label {len(ov['label'])} chars (max 70)")
        for it in ov.get("items", []) if ov.get("type") == "bars" else []:
            if len(it.get("label", "")) > 22:
                W(f"label: shot {s['id']} bar label '{it['label']}' > 22 chars")
        if re.search(r"\bact \d\b", json.dumps(ov), re.I):
            W(f"acts: shot {s['id']} shows an act label — acts are planning only")
    if re.search(r"\bact (one|two|three|four|five|\d)\b", s.get("text", ""), re.I):
        W(f"acts: shot {s['id']} mentions an act — acts are planning only")

# ---- subscribe
nudge = next((s for s in S if s.get("nudge")), None)
card = next((s for s in S if s.get("kind") == "subscribe"), None)
if card:
    W(f"subscribe: shot {card['id']} is a full-screen subscribe pause ({durs[card['id']]:.0f}s) — use \"nudge\": true on a story shot instead")
sub = nudge or card
if not sub:
    W("subscribe: no subscribe nudge — add \"nudge\": true to a shot at 30–65 % of runtime, right after a strong beat")
else:
    r = starts[sub["id"]] / total
    C(0.3 <= r <= 0.65, f"subscribe at {r:.0%} of runtime", f"subscribe at {r:.0%} of runtime — move to 30–65 %")
    if nudge and durs[nudge["id"]] < 5.5:
        W(f"subscribe: nudge shot {nudge['id']} is only {durs[nudge['id']]:.1f}s — the nudge needs about 5.5 s")

# ---- ending
tail = " ".join(s.get("text", "") for s in S if starts[s["id"]] > total * 0.7).lower()
C(bool(re.search(r"\b(you can|what helps|solution|plan|try|change|protect|reclaim|take back|recover|save|refill|fix|hope|prepare)\b", tail)), "practical/hopeful section in the last 30%", "ending: no practical or hopeful section in the last 30%")
end = next((s for s in S if s.get("kind") == "endcard"), None)
if not end:
    W("ending: no end card")
else:
    C(bool(re.search(r"\b(next|watch|this one|another)\b", end.get("text", ""), re.I)), "end card points to another video", "ending: the end card only says thanks — tell viewers which video to watch next (it feeds the end screen)")
    if durs[end["id"]] > 16:
        W(f"ending: end card is {durs[end['id']]:.0f}s — keep it under ~15 s")

score = max(0, 100 - 6 * len(warn))
print(f"PLAN CHECK {os.path.basename(os.path.abspath(film))}: {score}/100  ({total / 60:.1f} min, {len(S)} shots, picture changes every {avg:.1f}s)")
for m in ok:
    if m:
        print("  PASS", m)
for m in warn:
    print("  WARN", m)
