#!/usr/bin/env python3
"""Judge thumbnails at the sizes viewers really see them.

  python3 tools/thumbcheck.py FILM thumbnail-A.png [thumbnail-B.png ...]   -> FILM/qa/thumb_check.png

For each thumbnail: the phone-feed size (360 px wide) on YouTube's dark and light backgrounds, the suggested-video
size (168 px), and a grey version (if the words vanish in grey, the contrast is too weak). Look at the sheet: the
main word must be readable in the 168 px column, and the subject clear of the bottom-right corner (the duration badge).
Also warns when a file is not 16:9, under 1280 px wide, or over YouTube's 2 MB limit."""
import os, sys
from PIL import Image, ImageDraw

film, files = sys.argv[1], sys.argv[2:]
rows = []
for f in files:
    p = f if os.path.isabs(f) else os.path.join(film, f)
    im = Image.open(p).convert("RGB")
    w, h = im.size
    if abs(w / h - 16 / 9) > 0.01: print(f"WARN {f}: {w}x{h} is not 16:9")
    if w < 1280: print(f"WARN {f}: {w}px wide — YouTube wants at least 1280")
    if os.path.getsize(p) > 2_000_000: print(f"WARN {f}: {os.path.getsize(p) / 1e6:.1f} MB — over YouTube's 2 MB limit; export a JPG copy")
    rows.append((os.path.basename(f), im))
PAD, RH = 24, 250
sheet = Image.new("RGB", (PAD * 5 + 360 * 2 + 168 + 360, PAD + len(rows) * (RH + PAD)), "#0f0f0f")
d = ImageDraw.Draw(sheet)
for r, (name, im) in enumerate(rows):
    y = PAD + r * (RH + PAD)
    big = im.resize((360, 202), Image.LANCZOS); small = im.resize((168, 94), Image.LANCZOS)
    for im2, x, bg in ((big, PAD, "#0f0f0f"), (big, PAD * 2 + 360, "#ffffff"), (small, PAD * 3 + 720, "#0f0f0f"), (big.convert("L").convert("RGB"), PAD * 4 + 720 + 168, "#0f0f0f")):
        d.rectangle([x - 8, y - 8, x + im2.width + 8, y + RH - 12], fill=bg)
        sheet.paste(im2, (x, y))
        d.rectangle([x + im2.width - 44, y + im2.height - 22, x + im2.width - 4, y + im2.height - 4], fill="#000000")   # duration badge
        d.text((x + im2.width - 40, y + im2.height - 19), "12:04", fill="#ffffff")
        d.text((x, y + im2.height + 8), name[:44], fill="#111111" if bg == "#ffffff" else "#f1f1f1")
os.makedirs(os.path.join(film, "qa"), exist_ok=True)
out = os.path.join(film, "qa", "thumb_check.png"); sheet.save(out); print(out)
