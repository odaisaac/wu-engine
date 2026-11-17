#!/usr/bin/env python3
"""Narration with Gemini voices through the Google AI Studio web page (free, no API key).

  python tale/aistudio.py snippet FILM [--mode paragraph|chapter]
        write FILM/aistudio-snippet.js to paste into https://aistudio.google.com/generate-speech
  python tale/aistudio.py import FILM ZIP [ZIP ...]
        turn the downloaded recordings into FILM/vo/ (ready for tale.py build)

--mode paragraph (default): one recording per paragraph. Exact timing; about 10 seconds a paragraph.
--mode chapter: one recording per chapter, then split into paragraphs at the pauses. Fewer runs;
                a split can land a sentence early or late, so listen to the result.
"""
import argparse, glob, io, json, os, re, subprocess, sys, zipfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env
import tale
from kvo import trim
from gvo import to_float


def slug(film):
    return re.sub(r"[^a-z0-9-]+", "-", os.path.basename(os.path.abspath(film)).lower()).strip("-") or "film"


def cmd_snippet(film, mode):
    items = tale.load(film)["items"]
    if mode == "paragraph":
        parts = [[f"{it['i']:03d}", [it["i"]], it["text"]] for it in items]
    else:
        parts, cur = [], None
        for it in items:
            if cur is None or it["first"]:
                cur = [f"ch{len(parts) + 1:02d}", [], []]; parts.append(cur)
            cur[1].append(it["i"]); cur[2].append(it["text"])
        parts = [[n, ps, "\n\n".join(ts)] for n, ps, ts in parts]
    tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser", "aistudio-voice.js"), encoding="utf-8").read()
    js = (tpl.replace('"__FILM__"', json.dumps(slug(film))).replace('"__MODE__"', json.dumps(mode))
             .replace("__PARTS__", json.dumps(parts, ensure_ascii=False)))
    out = f"{film}/aistudio-snippet.js"
    open(out, "w", encoding="utf-8").write(js)
    print(f"wrote {out}: {len(parts)} recordings ({mode} mode).")
    print("Next: open https://aistudio.google.com/generate-speech, click Create new dialog, choose the voice and style,")
    print("      then press F12, choose Console, paste the whole file and press Enter.")


def write_para(film, n, text, y, sr):
    mp3, js = f"{film}/vo/{n:03d}.mp3", f"{film}/vo/{n:03d}.json"
    p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-", "-ar", "44100", "-b:a", "160k", mp3],
                       input=y.astype(np.float32).tobytes())
    if p.returncode:
        sys.exit(f"could not write {mp3}")
    d = len(y) / sr; L = max(1, len(text))
    json.dump({"engine": "gemini", "chars": list(text), "starts": [round(d * i / L, 3) for i in range(L)],
               "ends": [round(d * (i + 1) / L, 3) for i in range(L)]}, open(js, "w"))
    return d


def split_points(x, sr, lengths):
    """Cut a chapter recording into len(lengths) paragraphs: aim for the share of time their text length
    suggests, then move each cut to the nearest real pause (longer pauses preferred)."""
    w = sr // 100; n = len(x) // w
    db = 20 * np.log10(np.sqrt((x[:n * w].reshape(n, w) ** 2).mean(axis=1)) + 1e-9)
    gaps, run = [], 0
    for i, v in enumerate(db):
        if v < -45: run += 1
        else:
            if run >= 20: gaps.append(((i - run / 2) * 0.01, run * 0.01))
            run = 0
    total = len(x) / sr; cuts = []; acc = 0; tl = sum(lengths); lo = 0.0
    for L in lengths[:-1]:
        acc += L; target = total * acc / tl
        cand = [(abs(c - target) - 0.6 * g, c) for c, g in gaps if c > lo + 1.0]
        c = min(cand)[1] if cand else target
        cuts.append(c); lo = c
    return cuts


def cmd_import(film, zips):
    items = {it["i"]: it for it in tale.load(film)["items"]}
    os.makedirs(f"{film}/vo", exist_ok=True)
    made = 0; mode = None
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            meta = json.loads(zf.read("parts.json")) if "parts.json" in zf.namelist() else {"parts": {}}
            mode = meta.get("mode", mode)
            for name in zf.namelist():
                if not name.endswith(".wav"):
                    continue
                paras = meta["parts"].get(name) or [int(re.sub(r"\D", "", name))]
                x, sr = to_float(zf.read(name), "")
                if len(paras) == 1:
                    n = paras[0]; d = write_para(film, n, items[n]["text"], trim(x, sr), sr); made += 1
                    print(f"{n:03d} {d:.1f}s")
                    continue
                cuts = [0.0] + split_points(x, sr, [len(items[n]["text"]) for n in paras]) + [len(x) / sr]
                for k, n in enumerate(paras):
                    seg = x[int(cuts[k] * sr):int(cuts[k + 1] * sr)]
                    d = write_para(film, n, items[n]["text"], trim(seg, sr), sr); made += 1
                    print(f"{n:03d} {d:.1f}s  (from {name})")
    missing = [n for n in items if not os.path.exists(f"{film}/vo/{n:03d}.mp3")]
    print(f"imported {made} paragraphs into {film}/vo")
    if missing:
        print("still missing narration for paragraphs:", ", ".join(map(str, missing)))
    if mode == "chapter":
        print("Chapter mode: listen to a few paragraph files to check the splits before building.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["snippet", "import"]); ap.add_argument("film"); ap.add_argument("zips", nargs="*")
    ap.add_argument("--mode", choices=["paragraph", "chapter"], default="paragraph")
    a = ap.parse_args()
    env.load_env()
    if a.cmd == "snippet": cmd_snippet(a.film, a.mode)
    else:
        if not a.zips: sys.exit("give the zip files to import")
        cmd_import(a.film, a.zips)
