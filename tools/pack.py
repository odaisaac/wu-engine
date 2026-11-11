#!/usr/bin/env python3
"""Build the YouTube upload pack for a film and check it against YouTube's limits.

  python3 tools/pack.py FILM            -> FILM/youtube-pack.md + FILM/captions.srt

Reads FILM/pack.json (written by hand for each film), spec.json, timing.json and the footage credit files.
pack.json fields:
  keyword     main search phrase — must be in the first title and the first 150 characters of the description
  titles      3–5 options, best first (the second is the A/B alternative)
  thumb_text  words on the thumbnail (must add to the title, not repeat it)
  thumbs      [{"file": "thumbnail-A.png", "idea": "what it shows"}]  (first = default upload)
  hook        the first two lines of the description (what shows before "…more")
  about       bullets: what the viewer will learn
  chapters    {"shot id": "chapter title"} (the first shot is forced to 0:00); default: the spec's act titles
  question    comment prompt        next   title of the video to send viewers to (end screen + pinned comment)
  sources     [["label", "https://…"], …]      extra_credits  ["NASA …", …]
  tags        search tags            hashtags  up to 3, shown above the title
  shorts      [{"file": "shorts/x.mp4", "title": "…", "hook": "…"}]
  synthetic   true when AI images/footage appear in the film (decides the "altered content" answer)
  playlist, publish   optional
Chapters, end-screen time, footage credits and captions are worked out from the film itself, so they cannot drift.
Every limit YouTube enforces is checked and reported at the top of the pack."""
import json, os, re, subprocess, sys

film = sys.argv[1]
J = lambda n, d=None: json.load(open(os.path.join(film, n))) if os.path.exists(os.path.join(film, n)) else d
P = J("pack.json")
if not P:
    sys.exit("no pack.json in " + film)
spec, timing = J("spec.json"), J("timing.json")
S = spec["shots"]; T = {t["id"]: t for t in timing["shots"]}
fps = timing.get("fps", 30)
total = timing["total"] / fps
warn = []
ts = lambda sec: f"{int(sec) // 60}:{int(sec) % 60:02d}"

# ---- chapters
ch = P.get("chapters") or {s["id"]: s["act"]["title"] for s in S if s.get("act")}
chapters = sorted((T[i]["start"] / fps, t) for i, t in ch.items() if i in T)
if chapters:
    chapters[0] = (0, chapters[0][1])
end = next((s for s in S if s.get("kind") == "endcard"), None)
end_at = T[end["id"]]["start"] / fps if end else None
if end and not any(abs(c[0] - end_at) < 1 for c in chapters):
    chapters.append((end_at, "What to watch next"))
if len(chapters) < 3: warn.append(f"chapters: only {len(chapters)} — YouTube needs at least 3 for them to show")
for (a, ta), (b, tb) in zip(chapters, chapters[1:]):
    if b - a < 10: warn.append(f"chapters: '{ta}' is under 10 s — YouTube will ignore the chapter list")
for _, t in chapters:
    if re.search(r"\bact\b|\bpart \d", t, re.I): warn.append(f"chapters: '{t}' reads like a planning label — name what the viewer gets")
if end:
    d = T[end["id"]]["dur"] / fps
    if not 5 <= total - end_at <= 20: warn.append(f"end screen: the end card runs {total - end_at:.0f}s — YouTube end screens need 5–20 s at the very end")

# ---- titles
titles = P["titles"]; kw = P.get("keyword", "").lower()
for i, t in enumerate(titles):
    if len(t) > 100: warn.append(f"title {i + 1}: {len(t)} characters — YouTube's limit is 100")
    elif len(t) > 60 and i < 2: warn.append(f"title {i + 1}: {len(t)} characters — phones cut titles at about 60; put the hook first")
    if sum(1 for w in t.split() if len(w) > 2 and w.isupper()) > 2: warn.append(f"title {i + 1}: more than two ALL-CAPS words reads as spam")
if kw and kw not in titles[0].lower(): warn.append(f"title 1 does not contain the keyword '{P['keyword']}'")
if P.get("thumb_text") and P["thumb_text"].lower().strip(" .!?") == titles[0].lower().strip(" .!?"):
    warn.append("thumbnail text repeats the title — it should add to it")

# ---- footage credits (from the film's own files)
ids, other = [], []
for v in (J("files.json", {}) or {}).values():
    for p in v:
        m = re.search(r"pexels-(\d+)", p)
        if m and m.group(1) not in ids: ids.append(m.group(1))
for v in (J("stock/credits.json", {}) or {}).values():
    for c in v:
        sid = c.get("src_id", "")
        if sid.startswith("pexels-") and sid[7:].isdigit() and sid[7:] not in ids: ids.append(sid[7:])
        elif sid.startswith("coverr-") and "Stock video from Coverr (coverr.co)" not in other: other.append("Stock video from Coverr (coverr.co)")
        elif sid.startswith("pixabay-") and "Stock video from Pixabay (pixabay.com)" not in other: other.append("Stock video from Pixabay (pixabay.com)")
for v in (J("open_credits.json", {}) or {}).values():
    for c in v:
        if c.get("src") in (None, "pexels"): continue
        line = f"{c.get('title') or c.get('id')} — {c.get('credit') or c.get('src')} ({c.get('license') or 'see source'}){': ' + c['page'] if c.get('page') else ''}"
        if line not in other: other.append(line)
credits = list(P.get("extra_credits", [])) + other
if ids: credits.append("Stock video from Pexels contributors (pexels.com), clip IDs " + ", ".join(ids) + ". Each is at https://www.pexels.com/video/ID/")
credits.append("Narration: AI voice (ElevenLabs)." + (" Some images are AI-generated illustrations and are labelled on screen." if P.get("synthetic") else ""))

# ---- description
tags = P.get("tags", []); hashtags = [h if h.startswith("#") else "#" + h for h in P.get("hashtags", [])]
lines = [P["hook"].strip(), ""]
if P.get("about"): lines += ["In this documentary:"] + ["• " + a for a in P["about"]] + [""]
lines += ["CHAPTERS"] + [f"{ts(a)} {t}" for a, t in chapters] + [""]
if P.get("question"): lines += [P["question"].strip() + " Tell us in the comments.", ""]
lines += ["Subscribe to The World Unpacked for a new documentary every week on the hidden systems behind everyday life.", ""]
if P.get("next"): lines += [f"WATCH NEXT: {P['next']}", ""]
if P.get("sources"): lines += ["SOURCES"] + [f"• {a}: {b}" for a, b in P["sources"]] + [""]
lines += ["FOOTAGE AND CREDITS"] + ["• " + c for c in credits] + ["", " ".join(hashtags[:3])]
desc = "\n".join(lines).strip()
if len(desc) > 5000: warn.append(f"description: {len(desc)} characters — YouTube's limit is 5,000 (trim sources or credits)")
if kw and kw not in desc[:150].lower(): warn.append(f"description: the keyword '{P['keyword']}' is not in the first 150 characters (the part shown in search)")
if re.search(r"[<>]", desc): warn.append("description contains < or > — YouTube rejects these characters")
for a, b in P.get("sources", []):
    if not b.startswith("https://"): warn.append(f"source link is not https: {b}")
if sum(len(t) for t in tags) + max(0, len(tags) - 1) > 500: warn.append(f"tags: {sum(len(t) for t in tags) + len(tags) - 1} characters — YouTube's limit is 500")
if not 8 <= len(tags) <= 25: warn.append(f"tags: {len(tags)} — use 8–25, most specific first")
if len(hashtags) > 3: warn.append(f"hashtags: {len(hashtags)} — only the first 3 show above the title; the pack uses the first 3")
if any(" " in h for h in hashtags): warn.append("hashtags cannot contain spaces")

# ---- thumbnails
thumbs = P.get("thumbs", [])
for t in thumbs:
    p = os.path.join(film, t["file"])
    if not os.path.exists(p): warn.append(f"thumbnail file missing: {t['file']}"); continue
    if os.path.getsize(p) > 2_000_000:
        jpg = os.path.splitext(p)[0] + ".jpg"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", p, "-q:v", "2", jpg], check=True)
        t["file"] = os.path.relpath(jpg, film)        # YouTube refuses thumbnails over 2 MB
if not thumbs: warn.append("no thumbnails listed")
elif len(thumbs) < 2: warn.append("only one thumbnail — make a second, different idea so Test & Compare has something to test")

# ---- shorts
for sh in P.get("shorts", []):
    p = os.path.join(film, sh.get("file", ""))
    if sh.get("file") and os.path.exists(p):
        d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))
        sh["secs"] = d
        if d > 60: warn.append(f"short {sh['file']}: {d:.0f}s — keep Shorts under 60 s")
    if len(sh.get("title", "")) > 70: warn.append(f"short title too long ({len(sh['title'])}): {sh['title']}")

# ---- captions (.srt) from the narration and its word timings
def srt_time(x):
    ms = int(round(x * 1000)); return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
cues = []
for s in S:
    txt = s.get("text"); t = T.get(s["id"])
    if not txt or not t: continue
    ws = txt.split(); wt = t.get("words")
    if not wt or len(wt) != len(ws):
        span = max(1, t["dur"] - 18); acc = 0; wt = []
        tot = sum(len(w) + 1 for w in ws)
        for w in ws:
            a = acc / tot * span; acc += len(w) + 1; wt.append([w, a, acc / tot * span])
    cur, st = [], None
    for i, w in enumerate(ws):
        if st is None: st = wt[i][1]
        cur.append(w)
        endp = re.search(r"[.!?][\"')]?$", w); clause = re.search(r"[,;:]$", w)
        if endp or (clause and len(" ".join(cur)) > 34) or len(" ".join(cur)) > 62 or i == len(ws) - 1:
            if i < len(ws) - 1 and len(ws) - 1 - i <= 1 and not endp: continue
            cues.append(((t["start"] + st) / fps, (t["start"] + wt[i][2]) / fps + 0.25, " ".join(cur))); cur, st = [], None
for i in range(len(cues) - 1):   # never overlap the next line
    if cues[i][1] > cues[i + 1][0]: cues[i] = (cues[i][0], cues[i + 1][0] - 0.02, cues[i][2])
def wrap(t):
    if len(t) <= 42: return t
    ws = t.split(); best = min(range(1, len(ws)), key=lambda k: abs(len(" ".join(ws[:k])) - len(" ".join(ws[k:]))))
    return " ".join(ws[:best]) + "\n" + " ".join(ws[best:])
open(os.path.join(film, "captions.srt"), "w").write("".join(f"{n}\n{srt_time(a)} --> {srt_time(b)}\n{wrap(t)}\n\n" for n, (a, b, t) in enumerate(cues, 1)))

# ---- write the pack
nudge = next((s for s in S if s.get("nudge") or s.get("kind") == "subscribe"), None)
card_at = T[nudge["id"]]["start"] / fps if nudge else total * 0.5
o = [f"# YouTube pack: {titles[0]}", "",
     f"Length {ts(total)} · {len(S)} shots · end screen from **{ts(end_at) if end else '—'}**", ""]
o += ["## Pack check", ""] + (["All checks passed: title, description, chapters, tags, hashtags, thumbnails and end screen are within YouTube's limits."] if not warn else ["Fix these before uploading:"] + ["- " + w for w in warn]) + [""]
o += ["## 1. Title", "", f"**Upload with:** {titles[0]}  ({len(titles[0])} characters)", ""]
if len(titles) > 1:
    o += ["Alternatives, in the order to test them:"] + [f"{i}. {t}  ({len(t)})" for i, t in enumerate(titles[1:], 2)] + [""]
o += ["## 2. Thumbnail", ""]
if P.get("thumb_text"): o += [f"**Text on the thumbnail:** {P['thumb_text']}", ""]
o += [f"- **{'Upload' if i == 0 else 'Test ' + chr(65 + i)}:** `{t['file']}`" + (f" — {t['idea']}" if t.get("idea") else "") for i, t in enumerate(thumbs)]
if len(thumbs) > 1: o += ["", "In Studio › Details › Thumbnail choose **Test & Compare** and add all of them; YouTube picks the winner by watch time."]
o += ["", "## 3. Description (paste as it is)", "", "```", desc, "```", ""]
pin = (P.get("pinned") or ((P.get("question", "").strip() + " ") if P.get("question") else "") + (f"Next, watch: {P['next']}" if P.get("next") else "")).strip()
if pin: o += ["## 4. Pinned comment", "", "Post this as the channel, then pin it:", "", "> " + pin, ""]
o += ["## 5. Tags", "", "```", ", ".join(tags), "```", "", "## 6. Shorts", ""]
days = ["the day after upload", "day 3", "day 5", "day 7"]
for i, sh in enumerate(P.get("shorts", [])):
    o += [f"{i + 1}. **{sh['title']}**" + (f"  (`{sh['file']}`" + (f", {sh['secs']:.0f}s" if sh.get("secs") else "") + ")" if sh.get("file") else ""),
          f"   Opening line: *{sh.get('hook', '')}*  ·  Post: {days[min(i, 3)]}"]
if P.get("shorts"): o += ["", "For each Short set **Related video** to this documentary (Studio › Details), post one a day, never in a batch."]
o += ["", "## 7. Upload settings", "",
      f"- **Altered or synthetic content:** {'Yes — AI images appear in the film.' if P.get('synthetic') else 'No — only the narration is an AI voice; all footage is real.'}",
      "- **Audience:** No, it's not made for kids.",
      "- **Category:** Education · **Language:** English · **Recording date:** leave empty.",
      "- **Subtitles:** upload `captions.srt` (Studio › Subtitles › Add › Upload file › With timing). Exact captions help search and auto-translation.",
      f"- **Playlist:** {P.get('playlist', 'The World Unpacked: Documentaries')}",
      f"- **End screen:** add Video (Best for viewer), Video (your pick{': ' + P['next'] if P.get('next') else ''}) and Subscribe, all starting at **{ts(end_at) if end else '—'}**.",
      f"- **Info card:** one card at about **{ts(card_at)}** linking to {P.get('next', 'a related documentary')}.",
      "- Paste the chapters exactly as written; the first must stay 0:00.",
      f"- **Publish:** {P.get('publish', 'Tuesday or Wednesday, 16:00 Nigeria time; nothing else that day.')}", "",
      "## 8. First 48 hours", "",
      "Open Studio › Analytics for this video and read three numbers:", "",
      "| Number | Healthy | If it is lower |",
      "|---|---|---|",
      "| Impressions click-through rate | 4–8 % | Let Test & Compare finish; if still low, change the title to alternative 2 |",
      "| Average percentage viewed | 40 %+ | Open the retention graph, find the first steep drop, and tell the engine which second it is |",
      "| Impressions | Growing each day | Under ~300 after 48 h means YouTube is still testing; post the first Short and wait |", ""]
open(os.path.join(film, "youtube-pack.md"), "w").write("\n".join(o))
print(f"pack written: {len(desc)} char description, {len(chapters)} chapters, {len(tags)} tags, {len(cues)} caption lines, {len(warn)} warning(s)")
for w in warn: print("  WARN", w)
