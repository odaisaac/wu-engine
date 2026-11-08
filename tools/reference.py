#!/usr/bin/env python3
"""Analyse a reference video so a new film can borrow its structure, pacing and hooks (never its words).

  python3 tools/reference.py OUT_DIR [--transcript item.json] [--video clip.mp4]

--transcript : one dataset row from the Apify actor johnvc/YoutubeTranscripts
               (input {"youtube_url": URL, "languages": ["en"], "include_metadata": true});
               YouTube blocks transcript requests from the cloud workspace, Apify does not.
--video      : the video file itself, if Damilare attaches it or it can be downloaded
               (adds shot-cut pacing, a keyframe contact sheet and loudness).
Writes OUT_DIR/reference.json and OUT_DIR/reference.md:
  speaking pace (wpm), hook (first 30 s), chapter/segment map with word counts, questions and
  numbers per minute, second-person ("you") rate, re-hook phrases, average shot length,
  cuts per minute over time, loudness — then a "blueprint" to follow in build_spec.py.
"""
import argparse, json, os, re, subprocess

REHOOK = re.compile(r"\b(but here'?s|here'?s the thing|but that'?s not|and that'?s where|the real (reason|question)|so why|what if|it turns out|the problem is|but wait|remember)\b", re.I)


def ts(sec):
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def chapters_from(desc):
    out = []
    for line in (desc or "").splitlines():
        m = re.match(r"\s*\(?((?:\d+:)?\d{1,2}:\d{2})\)?\s*[-–—|]?\s*(.+)", line)
        if m:
            p = [int(x) for x in m.group(1).split(":")]
            out.append((p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1], m.group(2).strip()))
    return out if len(out) >= 3 and out[0][0] == 0 else []


def text_stats(snips, a, b):
    seg = [s for s in snips if a <= s["start"] < b]
    txt = " ".join(s["text"].replace("\n", " ") for s in seg)
    words = txt.split()
    mins = max((b - a) / 60, 1e-6)
    return dict(start=a, end=b, words=len(words), wpm=round(len(words) / mins), questions=txt.count("?"),
                numbers=len(re.findall(r"\b\d[\d,.%]*\b|\b(hundred|thousand|million|billion|percent)\b", txt, re.I)),
                you=round(len(re.findall(r"\byou(r|'re|'ll)?\b", txt, re.I)) / max(len(words), 1) * 100, 1),
                rehooks=[m.group(0) for m in REHOOK.finditer(txt)][:6], first=" ".join(words[:28]))


def analyse_transcript(item):
    snips = [dict(text=t, start=float(s), dur=float(d)) for t, s, d in zip(item["timestamped"]["text"], item["timestamped"]["start"], item["timestamped"]["duration"])] \
        if isinstance(item.get("timestamped"), dict) else [dict(text=x["text"], start=float(x["start"]), dur=float(x.get("duration", 0))) for x in item["timestamped"]]
    total = float(item.get("video_duration_seconds") or item.get("total_seconds") or (snips[-1]["start"] + snips[-1]["dur"]))
    ch = chapters_from(item.get("description"))
    bounds = [c[0] for c in ch] + [total] if ch else [min(total, x) for x in range(0, int(total) + 60, 60)]
    segs = []
    for i in range(len(bounds) - 1):
        if bounds[i + 1] <= bounds[i]:
            continue
        st = text_stats(snips, bounds[i], bounds[i + 1])
        st["title"] = ch[i][1] if ch else f"Minute {i + 1}"
        segs.append(st)
    allst = text_stats(snips, 0, total)
    hook = " ".join(s["text"].replace("\n", " ") for s in snips if s["start"] < 30)
    return dict(title=item.get("title"), channel=item.get("channel_name"), views=item.get("view_count"), duration=total, url=item.get("url"),
                chapters=[dict(t=ts(c[0]), title=c[1]) for c in ch], overall=allst, hook=hook, segments=segs)


def analyse_video(path, out):
    from scenedetect import detect, ContentDetector
    scenes = detect(path, ContentDetector(threshold=27))
    cuts = [s[0].get_seconds() for s in scenes]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True).stdout or 0)
    lens = [scenes[i][1].get_seconds() - scenes[i][0].get_seconds() for i in range(len(scenes))] or [dur]
    per_min = [sum(1 for c in cuts if m * 60 <= c < (m + 1) * 60) for m in range(int(dur // 60) + 1)]
    # keyframe sheet: one frame from up to 40 scenes
    from PIL import Image
    pick = scenes[:: max(1, len(scenes) // 40)][:40] if scenes else []
    tiles = []
    for i, (a, b) in enumerate(pick):
        f = os.path.join(out, f"k{i:02d}.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str((a.get_seconds() + b.get_seconds()) / 2), "-i", path, "-frames:v", "1", "-vf", "scale=320:-2", f])
        if os.path.exists(f):
            tiles.append(Image.open(f))
    if tiles:
        W, H = 320, tiles[0].height
        sheet = Image.new("RGB", (W * 8, H * ((len(tiles) + 7) // 8)))
        for i, t in enumerate(tiles):
            sheet.paste(t, ((i % 8) * W, (i // 8) * H))
        sheet.save(os.path.join(out, "reference_keyframes.jpg"))
        for i in range(len(tiles)):
            os.remove(os.path.join(out, f"k{i:02d}.jpg"))
    ln = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "loudnorm=print_format=summary", "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = re.search(r"Input Integrated:\s+(-?[\d.]+)", ln)
    return dict(shots=len(scenes), avg_shot=round(sum(lens) / len(lens), 2), median_shot=round(sorted(lens)[len(lens) // 2], 2), cuts_per_min=per_min,
                lufs=float(lufs.group(1)) if lufs else None, duration=dur)


def report(r):
    L = [f"# Reference: {r.get('title') or 'video'}", ""]
    if r.get("channel"):
        L.append(f"{r['channel']} · {r.get('views') or '?'} views · {ts(r['duration'])} · {r.get('url', '')}")
    o = r.get("overall")
    if o:
        L += ["", "## Voice and pacing", f"- {o['wpm']} words/min overall (Daniel at our settings ≈ 150).",
              f"- {o['questions']} questions, {o['numbers']} numbers, 'you' in {o['you']}% of words.", "", "## Hook (first 30 s)", f"> {r['hook'][:600]}"]
        L += ["", "## Structure", "| at | section | words | wpm | ? | numbers | re-hooks |", "|---|---|---|---|---|---|---|"]
        for s in r["segments"]:
            L.append(f"| {ts(s['start'])} | {s['title'][:40]} | {s['words']} | {s['wpm']} | {s['questions']} | {s['numbers']} | {', '.join(s['rehooks'][:3])} |")
    v = r.get("video")
    if v:
        L += ["", "## Editing", f"- {v['shots']} shots, average {v['avg_shot']} s (median {v['median_shot']} s).",
              f"- Cuts per minute: {', '.join(map(str, v['cuts_per_min']))}.", f"- Loudness {v['lufs']} LUFS.", "- Keyframes: reference_keyframes.jpg"]
    L += ["", "## Blueprint for our film", "- Keep: hook shape, section order and lengths, question/number rhythm, re-hook spacing, cut pace.",
          "- Change: topic, every sentence (write our own), visuals, facts (research fresh, cite sources).",
          "- Never copy lines, music or footage from the reference."]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--transcript"); ap.add_argument("--video")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    r = {}
    if a.transcript:
        item = json.load(open(a.transcript))
        r = analyse_transcript(item[0] if isinstance(item, list) else item)
    if a.video:
        r["video"] = analyse_video(a.video, a.out)
        r.setdefault("duration", r["video"]["duration"])
    json.dump(r, open(os.path.join(a.out, "reference.json"), "w"), indent=1)
    open(os.path.join(a.out, "reference.md"), "w").write(report(r))
    print(open(os.path.join(a.out, "reference.md")).read())


if __name__ == "__main__":
    main()
