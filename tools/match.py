#!/usr/bin/env python3
"""Rank candidate clips/photos against each shot with CLIP, then (optionally) download the winners.

  python3 tools/match.py FILM [--only 03,07]            # score + contact sheets in FILM/qa/match_<id>.png
  python3 tools/match.py FILM --apply [--only ..] [--k 2] [--pin 09=wiki:File:X.webm,pexels:123]

Reads FILM/candidates.json (tools/sources.py + tools/pexels_import.py), FILM/spec.json and FILM/timing.json.
Scores = cosine(CLIP text, CLIP thumbnail) using openai/clip-vit-base-patch32 on CPU, with the shot's
search phrases + kinetic line as the text. Already-used ids are skipped so one clip never repeats.
--apply downloads the top clips (one per ~4.5 s of the shot, or --k; video first; photos become 7 s Ken Burns clips), converts everything to
H.264 in FILM/stock/raw/<src>-<id>.mp4, writes FILM/files.json for build_spec.py, and records licences
and credits in FILM/open_credits.json for the YouTube pack. Then run build_spec.py and stock.py as usual.
"""
import argparse, hashlib, io, json, math, os, re, subprocess, sys, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from sources import resolve, UA  # noqa: E402
from cues import clips_for  # noqa: E402

MODEL = "openai/clip-vit-base-patch32"
MIN = 0.24          # below this CLIP similarity a match is usually wrong — check the sheet instead
_m = None


def model():
    global _m
    if _m is None:
        import torch
        from transformers import CLIPModel, CLIPProcessor
        torch.set_num_threads(max(1, (os.cpu_count() or 2) - 1))
        _m = (CLIPModel.from_pretrained(MODEL).eval(), CLIPProcessor.from_pretrained(MODEL), torch)
    return _m


def fetch(url, path):
    if not os.path.exists(path):
        r = urllib.request.Request(url, headers={"User-Agent": UA})
        data = urllib.request.urlopen(r, timeout=60).read()
        open(path, "wb").write(data)
    return path


def shot_text(s):
    parts = list(s.get("query", []))[:3]
    ov = s.get("overlay") or {}
    if ov.get("type") == "kinetic":
        parts.append(ov.get("text", ""))
    return [p for p in parts if p]


def score(film, shots, cand):
    from PIL import Image
    M, P, torch = model()
    tdir = os.path.join(film, "cand"); os.makedirs(tdir, exist_ok=True)
    for s in shots:
        cs = cand.get(s["id"], [])
        imgs, keep = [], []
        for c in cs:
            if not c.get("thumb"):
                continue
            p = os.path.join(tdir, hashlib.md5(c["thumb"].encode()).hexdigest()[:12] + ".jpg")
            try:
                try:
                    fetch(c["thumb"], p)
                except Exception:
                    if c["src"] == "pexels" and c["thumb"].endswith("preview-0.jpg"):
                        fetch(c["thumb"].replace("preview-0.jpg", "preview-0.jpeg"), p)   # pexels uses either extension
                    elif c["kind"] != "image" or not c.get("url"):
                        raise
                    else:
                        fetch(c["url"], p)            # some Openverse thumbs fail: use the original
                im = Image.open(p).convert("RGB"); im.thumbnail((640, 640)); imgs.append(im); keep.append(c)
            except Exception as e:
                c["score"] = -1; print("  thumb fail", c["src"], c["id"][:40], e)
        if not keep:
            continue
        with torch.no_grad():
            inp = P(text=shot_text(s), images=imgs, return_tensors="pt", padding=True, truncation=True)
            o = M(**inp)
            te = o.text_embeds / o.text_embeds.norm(dim=-1, keepdim=True)
            ie = o.image_embeds / o.image_embeds.norm(dim=-1, keepdim=True)
            sim = (ie @ te.T)            # images x phrases
            sc = (0.6 * sim.max(dim=1).values + 0.4 * sim.mean(dim=1)).tolist()
        for c, v in zip(keep, sc):
            c["score"] = round(float(v), 4) + (0.006 if c["kind"] == "video" else 0)   # small motion bonus
        cs.sort(key=lambda c: c.get("score", -1), reverse=True)
        print(s["id"], " | ".join(f"{c['src']}:{c['score']:.3f}" for c in cs[:5]))
        sheet(film, s, cs[:8], tdir)


def sheet(film, s, top, tdir):
    from PIL import Image, ImageDraw
    W, H = 384, 216
    im = Image.new("RGB", (W * 4, H * 2), "#111")
    d = ImageDraw.Draw(im)
    for i, c in enumerate(top):
        try:
            t = Image.open(os.path.join(tdir, hashlib.md5(c["thumb"].encode()).hexdigest()[:12] + ".jpg")).convert("RGB")
            t.thumbnail((W, H)); im.paste(t, ((i % 4) * W, (i // 4) * H))
        except Exception:
            pass
        x, y = (i % 4) * W, (i // 4) * H
        d.rectangle([x, y, x + W, y + 18], fill="#000")
        d.text((x + 4, y + 3), f"{i + 1}. {c['src']} {c['kind'][0]} {c.get('score', 0):.3f}  {c['title'][:28]}", fill="#fff")
    os.makedirs(os.path.join(film, "qa"), exist_ok=True)
    im.save(os.path.join(film, "qa", f"match_{s['id']}.png"))


def safe(x):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", x)[:60]


def to_mp4(src, out, kind, trim=False):
    if kind == "image":   # 7 s slow push-in, 1920x1080
        vf = ("crop=iw*0.93:ih*0.93," if trim else "") + "scale=2400:1350:force_original_aspect_ratio=increase,crop=2400:1350,zoompan=z='min(zoom+0.0006,1.12)':d=210:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30"
        cmd = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", src, "-vf", vf, "-t", "7", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out]
    else:
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-t", "40", "-an", "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out]
    subprocess.run(cmd, check=True)


def apply(film, shots, cand, k, pins):
    timing = {t["id"]: t for t in json.load(open(os.path.join(film, "timing.json")))["shots"]} if os.path.exists(os.path.join(film, "timing.json")) else {}
    fj_path, cr_path = os.path.join(film, "files.json"), os.path.join(film, "open_credits.json")
    files = json.load(open(fj_path)) if os.path.exists(fj_path) else {}
    creds = json.load(open(cr_path)) if os.path.exists(cr_path) else {}
    raw = os.path.join(film, "stock", "raw"); os.makedirs(raw, exist_ok=True)
    cut = float(json.load(open(os.path.join(film, "spec.json"))).get("cutEvery", 4.5))
    used = {os.path.basename(p) for sid, v in files.items() for p in v if sid not in {s["id"] for s in shots}}
    for s in shots:
        cs = [c for c in cand.get(s["id"], []) if c.get("score", -1) >= MIN]
        want = pins.get(s["id"])
        if want:
            cs = [next(c for c in cand[s["id"]] if f"{c['src']}:{c['id']}" == w) for w in want]
        n = k or clips_for(timing.get(s["id"], {}).get("dur", 270) / 30, cut)
        got, cr = [], []
        for c in cs:
            if len(got) >= n:
                break
            name = f"{c['src']}-{safe(c['id'])}.mp4"
            if name in used:
                continue
            out = os.path.join(raw, name)
            try:
                if not os.path.exists(out):
                    url = resolve(c)
                    if not url:
                        continue
                    tmp = out + ".src"
                    fetch(url, tmp); to_mp4(tmp, out, c["kind"], trim=c["src"] in ("loc", "archive")); os.remove(tmp)
            except Exception as e:
                print("  skip", c["src"], c["id"][:40], e); continue
            used.add(name); got.append(os.path.relpath(out, film)); cr.append({k2: c.get(k2) for k2 in ("src", "id", "title", "license", "credit", "page")})
        if got:
            files[s["id"]] = got; creds[s["id"]] = cr
            print(s["id"], "->", ", ".join(os.path.basename(g) for g in got))
    json.dump(files, open(fj_path, "w"), indent=1); json.dump(creds, open(cr_path, "w"), indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film"); ap.add_argument("--only", default=""); ap.add_argument("--apply", action="store_true")
    ap.add_argument("--k", type=int, default=0); ap.add_argument("--pin", default="")
    a = ap.parse_args()
    spec = json.load(open(os.path.join(a.film, "spec.json")))
    only = set(filter(None, a.only.split(",")))
    shots = [s for s in spec["shots"] if s["kind"] in ("footage", "photo") and (not only or s["id"] in only)]
    cp = os.path.join(a.film, "candidates.json"); cand = json.load(open(cp))
    pins = {}
    for item in filter(None, a.pin.split(";")):
        sid, v = item.split("="); pins[sid] = v.split(",")
    if not a.apply or any("score" not in c for s in shots for c in cand.get(s["id"], [])):
        score(a.film, shots, cand); json.dump(cand, open(cp, "w"), indent=1)
    if a.apply:
        apply(a.film, shots, cand, a.k, pins)


if __name__ == "__main__":
    main()
