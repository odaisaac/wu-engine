#!/usr/bin/env python3
"""Find, download and normalise stock footage/photos for each shot.
Usage: PIXABAY_KEY=... [PEXELS_KEY=...] stock.py FILM_DIR [--only 03,04] [--redo]
Shots with kind "footage" or "photo" need a "query" (string or list of strings).
Output: FILM/stock/<id>.mp4 (1920x1080, 30fps, exact shot length, no audio) or <id>.jpg, plus credits.json."""
import json, os, subprocess, sys, urllib.parse, urllib.request

film = sys.argv[1]
only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
redo = "--redo" in sys.argv
spec = json.load(open(f"{film}/spec.json")); timing = {t["id"]: t for t in json.load(open(f"{film}/timing.json"))["shots"]}
os.makedirs(f"{film}/stock/raw", exist_ok=True)
cred_path = f"{film}/stock/credits.json"
credits = json.load(open(cred_path)) if os.path.exists(cred_path) else {}
used = {c["src_id"] for v in credits.values() for c in v}
PX, PE, CV = os.environ.get("PIXABAY_KEY"), os.environ.get("PEXELS_KEY"), os.environ.get("COVERR_KEY")

def get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": "wu-engine/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=40) as r: return json.load(r)

def dl(url, path, headers=None):
    if not os.path.exists(path):
        subprocess.run(["curl", "-sS", "-L", "--fail", "-o", path, url] + sum([["-H", f"{k}: {v}"] for k, v in (headers or {}).items()], []), check=True)
    return path

PXL = json.load(open(f"{film}/pexels.json")) if os.path.exists(f"{film}/pexels.json") else []

def pexels_from_apify(q):
    """Results of the Apify Pexels run (automation-lab/pexels-stock-media-scraper) saved to FILM/pexels.json."""
    out = []
    for it in PXL:
        if it.get("query", "").lower() != q.lower() or it.get("orientation", "landscape") == "portrait": continue
        rs = [r for r in (it.get("renditions") or []) if r.get("width") and r["width"] >= 1280 and r.get("url")]
        if not rs or (it.get("width") or 0) < (it.get("height") or 0) * 1.5: continue
        r = min(rs, key=lambda r: abs(r["width"] - 1920))
        out.append({"src": "pexels", "src_id": f"pexels-{it['mediaId']}", "url": r["url"], "w": r["width"], "dur": float(it.get("duration") or 0), "page": it.get("detailUrl"), "author": (it.get("creator") or {}).get("name") or it.get("creator.name", "Pexels"), "text": " ".join([it.get("title") or "", " ".join(it.get("tags") or [])]).lower()})
    return out

def video_candidates(q):
    out = pexels_from_apify(q)
    if PE:
        try:
            d = get(f"https://api.pexels.com/videos/search?query={urllib.parse.quote(q)}&orientation=landscape&per_page=20", {"Authorization": PE})
            for v in d.get("videos", []):
                files = [f for f in v["video_files"] if f.get("width") and f["width"] >= 1280 and f["width"] >= f["height"] * 1.5]
                if not files: continue
                f = min(files, key=lambda f: abs(f["width"] - 1920))
                out.append({"src": "pexels", "src_id": f"pexels-{v['id']}", "url": f["link"], "w": f["width"], "dur": v["duration"], "page": v["url"], "author": v["user"]["name"]})
        except Exception as e: print("pexels error", e)
    if CV:
        try:
            d = get(f"https://api.coverr.co/videos?query={urllib.parse.quote(q)}&page_size=20&urls=true", {"Authorization": f"Bearer {CV}"})
            for h in d.get("hits", []):
                if h.get("is_vertical") or h.get("is_ai_generated") or h.get("is_premium") or not h.get("urls", {}).get("mp4"): continue
                if (h.get("max_width") or 0) < 1280: continue
                out.append({"src": "coverr", "src_id": f"coverr-{h['id']}", "url": h["urls"]["mp4"], "w": h["max_width"], "dur": float(h["duration"]), "page": f"https://coverr.co/videos/{h['slug']}", "author": "Coverr", "text": " ".join([h.get("title") or "", h.get("description") or "", " ".join(h.get("tags") or [])]).lower()})
        except Exception as e: print("coverr error", e)
    if PX:
        try:
            d = get(f"https://pixabay.com/api/videos/?key={PX}&q={urllib.parse.quote(q[:100])}&per_page=30&safesearch=true&video_type=film")
            for h in d.get("hits", []):
                v = h["videos"]; f = v["large"] if v["large"].get("url") and v["large"]["width"] >= 1280 else v["medium"]
                if not f.get("url") or f["width"] < 1280 or f["width"] < f["height"] * 1.5: continue
                out.append({"src": "pixabay", "src_id": f"pixabay-{h['id']}", "url": f["url"], "w": f["width"], "dur": h["duration"], "page": h["pageURL"], "author": h["user"], "text": h.get("tags", "").lower()})
        except Exception as e: print("pixabay error", e)
    return out

def photo_candidates(q):
    out = []
    if PE:
        try:
            d = get(f"https://api.pexels.com/v1/search?query={urllib.parse.quote(q)}&orientation=landscape&per_page=20", {"Authorization": PE})
            for p in d.get("photos", []):
                out.append({"src": "pexels", "src_id": f"pexels-p{p['id']}", "url": p["src"]["large2x"], "w": 1880, "page": p["url"], "author": p["photographer"]})
        except Exception as e: print("pexels error", e)
    if PX:
        try:
            d = get(f"https://pixabay.com/api/?key={PX}&q={urllib.parse.quote(q[:100])}&image_type=photo&orientation=horizontal&per_page=30&safesearch=true&min_width=1280")
            for h in d.get("hits", []):
                out.append({"src": "pixabay", "src_id": f"pixabay-p{h['id']}", "url": h["largeImageURL"], "w": 1280, "page": h["pageURL"], "author": h["user"], "text": h.get("tags", "").lower()})
        except Exception as e: print("pixabay error", e)
    return out

def norm(parts, secs, out):
    """Cut the clips into equal segments covering secs, scale/crop to 1920x1080@30, concat."""
    n = len(parts); seg = secs / n; tmp = []
    for i, (path, dur) in enumerate(parts):
        speed = min(1.0, dur / seg)  # slow clips slightly if they are short
        take = min(dur, seg * speed)
        ss = max(0.0, (dur - take) / 2)
        t = f"{out}.part{i}.mp4"
        vf = f"setpts={1/speed:.4f}*PTS,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,eq=contrast=1.06:saturation=1.12,format=yuv420p"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{ss:.2f}", "-t", f"{take:.2f}", "-i", path, "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", t], check=True)
        tmp.append(t)
    lst = f"{out}.txt"; open(lst, "w").write("".join(f"file '{os.path.abspath(t)}'\n" for t in tmp))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-vf", f"tpad=stop_mode=clone:stop_duration=3", "-t", f"{secs:.2f}", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30", out], check=True)
    for t in tmp + [lst]: os.remove(t)

for s in spec["shots"]:
    kind = s.get("kind", "graphic")
    if kind not in ("footage", "photo") or (only and s["id"] not in only): continue
    out = f"{film}/stock/{s['id']}.{'mp4' if kind == 'footage' else 'jpg'}"
    if os.path.exists(out) and not redo: continue
    secs = timing[s["id"]]["dur"] / 30
    if s.get("files"):
        parts = []
        for f in s["files"]:
            p = f if os.path.isabs(f) else os.path.join(film, f)
            parts.append((p, float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))))
        norm(parts, secs, out)
        credits[s["id"]] = [{"src": "picked", "src_id": "picked-" + os.path.basename(f), "page": f, "author": "see raw"} for f in s["files"]]
        print("picked files", s["id"], len(parts)); continue
    if s.get("file"):
        src = s["file"] if os.path.isabs(s["file"]) else os.path.join(film, "own", s["file"])
        if kind == "photo": subprocess.run(["cp", src, out], check=True)
        else:
            d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src]))
            norm([(src, d)], secs, out)
        credits[s["id"]] = [{"src": "own", "src_id": "own-" + s["id"], "page": s["file"], "author": "supplied"}]; print("own file", s["id"]); continue
    queries = s["query"] if isinstance(s["query"], list) else [s["query"]]
    must = [m.lower() for m in s.get("must", [])]
    cands = []
    for q in queries:
        cands += [c for c in (video_candidates(q) if kind == "footage" else photo_candidates(q)) if c["src_id"] not in used and c["src_id"] not in {x["src_id"] for x in cands}]
    if must: cands = [c for c in cands if any(m in c.get("text", "") for m in must)]
    if not cands: print("NO RESULTS", s["id"], queries, "must:", must); continue
    if kind == "photo":
        c = cands[0]; dl(c["url"], out); used.add(c["src_id"]); credits[s["id"]] = [c]; print("photo", s["id"], c["src_id"]); continue
    # prefer full-HD and clips long enough; keep search relevance order otherwise
    by_src = {}
    for c in cands: by_src.setdefault(c["src"], []).append(c)
    mixed = []
    for k in range(max(len(v) for v in by_src.values())):
        for src in ("pexels", "coverr", "pixabay"):
            if k < len(by_src.get(src, [])): mixed.append(by_src[src][k])
    cands = sorted(mixed, key=lambda c: (c["w"] < 1920, c["dur"] < min(secs, 8)))
    pick, total = [], 0.0
    max_clips = 1 if secs <= 9 else 2 if secs <= 18 else 3
    for c in cands:
        if len(pick) >= max_clips: break
        pick.append(c); total += c["dur"]
        if total >= secs and len(pick) >= (1 if secs <= 9 else 2): break
    parts = []
    for c in pick:
        p = dl(c["url"], f"{film}/stock/raw/{c['src_id']}.mp4"); parts.append((p, c["dur"])); used.add(c["src_id"])
    norm(parts, secs, out)
    credits[s["id"]] = pick; print("footage", s["id"], [c["src_id"] for c in pick], f"{secs:.1f}s")
    json.dump(credits, open(cred_path, "w"), indent=1)
json.dump(credits, open(cred_path, "w"), indent=1)
