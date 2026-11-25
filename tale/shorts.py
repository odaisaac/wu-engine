#!/usr/bin/env python3
"""Vertical Shorts (1080x1920) cut from a finished tale film: same pictures, same narration, big captions.

  python tale/shorts.py FILM                      make every Short listed in FILM/shorts.json
  python tale/shorts.py FILM --only 2             just the second one

FILM/shorts.json:
  {"tag": "Learn English with history",
   "shorts": [{"paras": [2, 3, 67, 68], "hook": "Was Napoleon really short?",
               "title": "Was Napoleon really short? | Learn English with History"}]}

Each Short: the chosen paragraphs in order (aim for 35-55 seconds of speech), a hook line at the top,
the picture with a slow pan, captions under it, and a closing line pointing to the full video.
Text stays inside the area that YouTube's buttons and title don't cover.
Output: FILM/shorts/short-01.mp4 ... and FILM/shorts/shorts.md (titles and descriptions to paste).
After uploading, set each Short's "Related video" to the full video.
"""
import argparse, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tale
from tale import FPS, GAP, chunks, chunk_times, keyword, ass_time, dur_of, find_img

SW, SH = 1080, 1920
PIC_Y, PIC_H = 500, 900                 # picture band
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
HL = "&H4DC9FF&"


def load_pic(path):
    import cv2
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    h, w = img.shape[:2]; k = 1350 / h
    return cv2.resize(img, (round(w * k), 1350), interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_LANCZOS4)


def background(src):
    import cv2
    h, w = src.shape[:2]; k = max(SW / w, SH / h)
    big = cv2.resize(src, (round(w * k), round(h * k)), interpolation=cv2.INTER_AREA)
    y0 = (big.shape[0] - SH) // 2; x0 = (big.shape[1] - SW) // 2
    bg = cv2.GaussianBlur(big[y0:y0 + SH, x0:x0 + SW], (0, 0), 28)
    return (bg * 0.42).astype("uint8")


def band(src, t, direction):
    """Window of the picture with the band's shape (1080x900), panning sideways and zooming a touch."""
    import cv2, numpy as np
    h, w = src.shape[:2]
    z = 1.0 + 0.06 * t
    vh = h / z; vw = vh * SW / PIC_H
    if vw > w:
        vw = w; vh = vw * PIC_H / SW
    span = w - vw
    x0 = span * (0.2 + 0.6 * (t if direction > 0 else 1 - t)); y0 = (h - vh) / 2
    k = SW / vw
    M = np.float32([[k, 0, -x0 * k], [0, k, -y0 * k]])
    return cv2.warpAffine(src, M, (SW, PIC_H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REFLECT)


def write_ass(path, tag, hook, items, total, end="Full story: tap the link below ▶"):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {SW}
PlayResY: {SH}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Tag,Inter,40,&H005CC8FF,&H00FFFFFF,&H00101010,&H96000000,1,0,0,0,100,100,2,0,1,3,0,8,60,60,190,1
Style: Hook,Anton,118,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,0,0,1,6,4,8,60,60,250,1
Style: Cap,Inter,62,&H00FFFFFF,&H00FFFFFF,&H00141414,&HA0000000,1,0,0,0,100,100,0,0,1,5,3,8,60,150,{PIC_Y + PIC_H + 40},1
Style: End,Inter,46,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,1,0,0,0,100,100,0,0,3,10,0,8,60,150,{PIC_Y + PIC_H - 110},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = [f"Dialogue: 0,0:00:00.00,{ass_time(total)},Tag,,0,0,0,,{tag.upper()}",
          f"Dialogue: 0,0:00:00.00,{ass_time(total)},Hook,,0,0,0,,{{\\fad(200,0)}}{hook.upper()}"]
    for text, align, start, dur in items:
        parts = chunks(text, 28)
        for p, (s, e) in zip(parts, chunk_times(text, parts, align, dur)):
            ws = p.split(); k = keyword(p)
            if k >= 0:
                ws[k] = f"{{\\c{HL}}}{ws[k]}{{\\c&HFFFFFF&}}"
            ev.append(f"Dialogue: 2,{ass_time(start + s)},{ass_time(start + e)},Cap,,0,0,0,,{{\\fad(100,0)}}{' '.join(ws)}")
    ev.append(f"Dialogue: 3,{ass_time(total - 3.2)},{ass_time(total)},End,,0,0,0,,{{\\fad(250,0)\\3c&H2B20C8&}}{end}")
    open(path, "w", encoding="utf-8").write(head + "\n".join(ev) + "\n")


def make_short(film, n, spec, tag, out):
    import cv2, numpy as np
    items = tale.load(film)["items"]
    paras = spec["paras"]; segs = []; t = 0.0
    for p in paras:
        a = dur_of(f"{film}/vo/{p:03d}.mp3")
        aj = f"{film}/vo/{p:03d}.json"
        segs.append((p, items[p - 1]["text"], json.load(open(aj)) if os.path.exists(aj) else None, t, a))
        t += a + GAP
    total = t + 0.4
    ass = out.replace(".mp4", ".ass")
    write_ass(ass, tag, spec["hook"], [(txt, al, st, a) for _, txt, al, st, a in segs], total,
              spec.get("end", "Full story: tap the link below ▶"))
    # voice track
    SR = 48000; track = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for p, _, _, st, a in segs:
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", f"{film}/vo/{p:03d}.mp3", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                             capture_output=True).stdout
        x = np.frombuffer(pcm, dtype=np.float32)[:int(a * SR)]
        s0 = int(st * SR); track[s0:s0 + len(x)] += x
    wav = out.replace(".mp4", ".wav")
    import wave
    with wave.open(wav, "wb") as wv:
        wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes((np.clip(track[:int(total * SR)], -1, 1) * 32767).astype("<i2").tobytes())
    # frames
    esc = ass.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    fd = FONTS.replace("\\", "/").replace(":", "\\:")
    tmp = out.replace(".mp4", "_v.mp4")
    pr = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{SW}x{SH}", "-r", str(FPS), "-i", "-",
                           "-vf", f"subtitles='{esc}':fontsdir='{fd}',format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", tmp],
                          stdin=subprocess.PIPE)
    srcs = [load_pic(find_img(film, p)) for p, *_ in segs]
    bgs = [background(s) for s in srcs]
    nf = round(total * FPS); FADE = 12
    starts = [round(st * FPS) for *_, st, _ in segs] + [nf]
    for f in range(nf):
        k = max(i for i in range(len(segs)) if starts[i] <= f)
        span = max(1, starts[k + 1] - starts[k]); tt = (f - starts[k]) / span
        fr = bgs[k].copy(); fr[PIC_Y:PIC_Y + PIC_H] = band(srcs[k], tt, 1 if k % 2 == 0 else -1)
        if k and f - starts[k] < FADE:
            pk = k - 1; pf = bgs[pk].copy(); pf[PIC_Y:PIC_Y + PIC_H] = band(srcs[pk], 1.0, 1 if pk % 2 == 0 else -1)
            a = (f - starts[k] + 1) / (FADE + 1); fr = cv2.addWeighted(fr, a, pf, 1 - a, 0)
        pr.stdin.write(fr.tobytes())
    pr.stdin.close()
    if pr.wait():
        sys.exit("ffmpeg failed")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-af", "aformat=channel_layouts=stereo,loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-shortest", "-movflags", "+faststart", out], check=True)
    for x in (tmp, wav):
        os.remove(x)
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("film"); ap.add_argument("--only", type=int)
    ap.add_argument("--config", default="shorts.json", help="another list of Shorts, e.g. shorts2.json (files named by each Short's \"name\")")
    a = ap.parse_args()
    cfg = json.load(open(f"{a.film}/{a.config}", encoding="utf-8"))
    os.makedirs(f"{a.film}/shorts", exist_ok=True)
    tag = cfg.get("tag", "Learn English with history")
    md = ["# Shorts", "", "After uploading each Short: Studio > the Short > Related video > choose the full video.", ""]
    for k, spec in enumerate(cfg["shorts"], 1):
        out = f"{a.film}/shorts/{spec['name']}.mp4" if spec.get("name") else f"{a.film}/shorts/short-{k:02d}.mp4"
        if a.only and a.only != k:
            continue
        total = make_short(a.film, k, spec, tag, out)
        print(f"{out}  {total:.0f}s  {spec['hook']}")
        md += [f"## {os.path.basename(out)} ({total:.0f} s)", "", f"Title: {spec.get('title', spec['hook'])}", "",
               f"Description: {spec.get('desc', 'Learn English through story. Watch the full story on the channel.')}", ""]
    if not a.only:
        open(f"{a.film}/shorts/" + ("shorts.md" if a.config == "shorts.json" else a.config.replace(".json", ".md")), "w", encoding="utf-8").write("\n".join(md))
