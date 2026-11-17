#!/usr/bin/env python3
"""Thumbnails for tale videos (1280x720 JPEG) from the thumbnail picture, no browser needed.

  python tale/thumb.py FILM --layout story --top "The leaf that" --big "Started Wars" --pill "Learn English"
  python tale/thumb.py FILM --layout brand --top "History of" --big "Tea" --out thumbnail-B.jpg
  python tale/thumb.py FILM --layout money --big "-$80 Billion" --out thumbnail-C.jpg

Layouts
  story  white line, big gold headline, red pill (picture subject on the right, text on the dark left)
  brand  your channel name small at the top left, two big white lines on the left
  money  one huge figure across the top: money amounts and percentages in red, the rest in white

The picture is FILM/thumb_src.jpg (or --img). Make two layouts and run them in YouTube's Test & Compare.
Keep the words to 2-4 big ones; a number or money figure in the headline usually helps.
"""
import argparse, os, re, sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env

W, H = 1280, 720
FONT_SRC = os.path.join(env.ROOT, "video", "public", "fonts")
FACES = {"anton": "anton-latin-400-normal", "archivo": "archivo-black-latin-400-normal",
         "playfair": "playfair-display-latin-700-normal", "inter": "inter-latin-700-normal"}
GOLD, RED, WHITE = (255, 200, 61), (200, 32, 43), (255, 255, 255)
MONEY = re.compile(r"^[-+]?[$€£₦]?\d[\d.,]*[%kKmMbB]?$|^[-+]?[$€£₦]|billion|million|trillion|%$", re.I)


def font(face, size):
    """Fonts ship as .woff2 for the video side; convert once to .ttf in tale/fonts for Pillow."""
    os.makedirs(env.FONTS, exist_ok=True)
    ttf = os.path.join(env.FONTS, FACES[face] + ".ttf")
    if not os.path.exists(ttf):
        try:
            from fontTools.ttLib import TTFont
            f = TTFont(os.path.join(FONT_SRC, FACES[face] + ".woff2")); f.flavor = None; f.save(ttf)
        except Exception as e:
            print(f"(font {face} unavailable: {e}; using the default font)")
            return ImageFont.load_default(size)
    return ImageFont.truetype(ttf, size)


def fit(draw, text, face, size, max_w):
    while size > 20:
        f = font(face, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return font(face, size)


def outlined(draw, xy, text, f, fill, stroke=7, shadow=True):
    x, y = xy
    if shadow:
        draw.text((x, y + 8), text, font=f, fill=(0, 0, 0), stroke_width=stroke, stroke_fill=(0, 0, 0))
    draw.text((x, y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def base(img, focus_x=0.75):
    im = Image.open(img).convert("RGB")
    im = ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(focus_x, 0.4))
    im = ImageOps.autocontrast(im, cutoff=0.5)
    return im


def left_shade(im, strength=0.85, reach=0.62):
    shade = Image.new("L", (W, 1))
    for x in range(W):
        shade.putpixel((x, 0), int(255 * strength * max(0.0, 1 - x / (W * reach))))
    shade = shade.resize((W, H))
    return Image.composite(Image.new("RGB", (W, H)), im, shade)


def story(im, top, big, pill):
    im = left_shade(im); d = ImageDraw.Draw(im); y = 150
    if top:
        f = fit(d, top.upper(), "anton", 92, 700); outlined(d, (46, y), top.upper(), f, WHITE); y += f.size + 10
    f = fit(d, big.upper(), "anton", 150, 640); outlined(d, (42, y), big.upper(), f, GOLD, stroke=8); y += f.size + 46
    if pill:
        f = fit(d, pill.upper(), "anton", 76, 600); tw = d.textlength(pill.upper(), font=f)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((52, y + 12, 52 + tw + 52, y + f.size + 42), 10, fill=(0, 0, 0, 170))
        im.paste(sh.filter(ImageFilter.GaussianBlur(12)), (0, 0), sh.filter(ImageFilter.GaussianBlur(12)))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((48, y, 48 + tw + 52, y + f.size + 30), 8, fill=RED)
        d.text((48 + 26, y + 8), pill.upper(), font=f, fill=WHITE)
    return im


def brand(im, top, big, channel):
    im = left_shade(im, 0.9, 0.6); d = ImageDraw.Draw(im)
    if channel:
        words = channel.split(); a = " ".join(words[:2]); b = " ".join(words[2:])
        f = font("playfair", 38); d.text((34, 26), a, font=f, fill=(242, 195, 90), stroke_width=1, stroke_fill=(0, 0, 0))
        if b:
            d.text((58, 26 + 38), b, font=font("playfair", 30), fill=(242, 195, 90))
    y = 250
    if top:
        f = fit(d, top, "archivo", 80, 640); d.text((40, y + 5), top, font=f, fill=(0, 0, 0)); d.text((40, y), top, font=f, fill=WHITE); y += f.size + 18
    f = fit(d, big, "archivo", 150, 700); d.text((40, y + 6), big, font=f, fill=(0, 0, 0)); d.text((40, y), big, font=f, fill=WHITE)
    return im


def money(im, big):
    top = Image.new("L", (1, H))
    for y in range(H):
        top.putpixel((0, y), int(200 * max(0.0, 1 - y / (H * 0.42))))
    im = Image.composite(Image.new("RGB", (W, H)), im, top.resize((W, H)))
    d = ImageDraw.Draw(im); words = big.upper().split()
    f = fit(d, big.upper(), "archivo", 120, W - 80)
    total = d.textlength(big.upper(), font=f); x = (W - total) / 2; sp = d.textlength(" ", font=f)
    for wd in words:
        outlined(d, (x, 22), wd, f, RED if MONEY.search(wd) else WHITE, stroke=6)
        x += d.textlength(wd, font=f) + sp
    return im


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("film"); ap.add_argument("--layout", choices=["story", "brand", "money"], default="story")
    ap.add_argument("--top", default=""); ap.add_argument("--big", required=True); ap.add_argument("--pill", default="")
    ap.add_argument("--img"); ap.add_argument("--out"); ap.add_argument("--focus", type=float, default=0.75,
                    help="where to keep the picture when cropping, 0 = left edge, 1 = right edge")
    a = ap.parse_args(); env.load_env()
    src = a.img or os.path.join(a.film, "thumb_src.jpg")
    if not os.path.exists(src):
        sys.exit(f"{src} not found: make the 'thumb' picture first (tale/images.py) or pass --img")
    im = base(src, a.focus)
    if a.layout == "story": im = story(im, a.top, a.big, a.pill)
    elif a.layout == "brand": im = brand(im, a.top, a.big, os.environ.get("T2F_CHANNEL", ""))
    else: im = money(im, a.big)
    out = a.out or os.path.join(a.film, "thumbnail.jpg" if a.layout == "story" else f"thumbnail-{a.layout}.jpg")
    im.save(out, quality=92)
    small = im.resize((320, 180), Image.LANCZOS); small.save(os.path.splitext(out)[0] + "-small.jpg", quality=90)
    print(f"wrote {out} (and a feed-size preview next to it: check that the words still read at that size)")
