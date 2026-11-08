#!/usr/bin/env python3
"""Cut vertical Shorts (1080x1920) from a finished documentary.

  python3 tools/shorts.py FILM MUSIC.mp3 [--only name1,name2]

FILM/shorts.json:
  [{"name": "harvest", "shots": ["15","16","17"], "hook": "Good harvest. Higher prices?", "title": "Why food costs more",
    "trim": {"15": [0, 0]}}]
- shots: shot ids in play order (consecutive shots are kept as one segment so transitions survive)
- hook: big opening line (last two words get the highlight colour) — make it a question or a surprise
- trim: optional [cut_from_start_frames, cut_from_end_frames] per shot
Needs words in timing.json (tools/words.py) and the film's bundle inputs in video/src + public/film
(render.sh leaves them in place). Output: FILM/shorts/<name>.mp4 at -14 LUFS, plus <name>.txt with a
title/description/hashtags draft. Renders one at a time with concurrency 2.
"""
import json, os, subprocess, sys

ENG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VID = os.path.join(ENG, "video")
FPS, END = 30, 75
CHROME = "/opt/google/chrome/chrome"


def segs_for(timing, shots, trim):
    T = {t["id"]: t for t in timing["shots"]}
    order = [t["id"] for t in timing["shots"]]
    segs = []
    for sid in shots:
        t = T[sid]; a, b = trim.get(sid, [0, 0])
        lo, hi = t["start"] + a, t["start"] + t["dur"] - b
        if segs and order.index(sid) == order.index(segs[-1]["last"]) + 1 and not a and not trim.get(segs[-1]["last"], [0, 0])[1]:
            segs[-1]["to"] = hi; segs[-1]["last"] = sid
        else:
            segs.append({"from": lo, "to": hi, "last": sid})
    return [{"from": s["from"], "to": s["to"]} for s in segs]


def run(cmd, **kw):
    print("+", " ".join(cmd)[:160]); subprocess.run(cmd, check=True, **kw)


def main():
    film, music = os.path.abspath(sys.argv[1]), sys.argv[2]
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    timing = json.load(open(os.path.join(film, "timing.json")))
    defs = json.load(open(os.path.join(film, "shorts.json")))
    out_dir = os.path.join(film, "shorts"); os.makedirs(out_dir, exist_ok=True)
    # make sure the bundle sees this film's spec/timing (with words)
    for f in ("spec.json", "timing.json"):
        run(["cp", os.path.join(film, f), os.path.join(VID, "src", f)])
    for d in defs:
        if only and d["name"] not in only:
            continue
        segs = segs_for(timing, d["shots"], d.get("trim", {}))
        props = {"segs": segs, "hook": d["hook"], "title": d.get("title"), "cta": d.get("cta", "Watch the full documentary"), "hl": d.get("hl", "#FFD23F")}
        pf = os.path.join(out_dir, f"{d['name']}.props.json"); json.dump(props, open(pf, "w"))
        silent = os.path.join(out_dir, f"{d['name']}.silent.mp4")
        if not os.path.exists(silent):
            run(["npx", "remotion", "render", "src/index.ts", "Short", silent, f"--props={pf}", f"--browser-executable={CHROME}", "--concurrency=2",
                 "--offthreadvideo-cache-size-in-bytes=800000000", "--log=error"], cwd=VID)
        # audio: slices of the finished mix (narration + music), short fades at each join, then a music tail under the end card
        mix = os.path.join(film, "mix.m4a")
        parts, fl = [], []
        for i, s in enumerate(segs):
            a, b = s["from"] / FPS, s["to"] / FPS
            parts += ["-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", mix]
            fl.append(f"[{i}:a]afade=t=in:d=0.04,afade=t=out:st={b - a - 0.06:.3f}:d=0.06[a{i}]")
        k = len(segs)
        parts += ["-ss", "35", "-t", f"{END / FPS + 0.5:.2f}", "-i", music]
        fl.append(f"[{k}:a]volume=-16dB,afade=t=in:d=0.3,afade=t=out:st={END / FPS - 0.8:.2f}:d=0.8[a{k}]")
        fl.append("".join(f"[a{i}]" for i in range(k + 1)) + f"concat=n={k + 1}:v=0:a=1,loudnorm=I=-14:TP=-1.5:LRA=11[out]")
        out = os.path.join(out_dir, f"{d['name']}.mp4")
        run(["ffmpeg", "-v", "error", "-y", *parts, "-i", silent, "-filter_complex", ";".join(fl), "-map", f"{k + 1}:v", "-map", "[out]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", out])
        dur = (sum(s["to"] - s["from"] for s in segs) + END) / FPS
        open(os.path.join(out_dir, f"{d['name']}.txt"), "w").write(
            f"{d.get('yt_title', d['hook'])}\n\n{d.get('desc', '')}\n\nFull documentary: {d.get('full', 'link in the related video')}\n\n{d.get('tags', '#Shorts')}\n")
        print(f"{d['name']}: {dur:.1f}s -> {out}")


if __name__ == "__main__":
    main()
