#!/usr/bin/env python3
"""Pictures for tale mode: one per paragraph, made in Gemini in your browser.

  python tale/images.py prompts FILM            write FILM/prompts.txt (one line per picture) and FILM/ai-helper.txt
  python tale/images.py snippet FILM [--style oil|watercolour|storybook|photo|paper|comic|"your own style line"]
                                   [--character "one sentence describing a recurring invented main character"]
                                                write FILM/gemini-snippet.js to paste into the Gemini page
  python tale/images.py import FILM ZIP [ZIP ...] [--host PICTURE]
                                                unpack the downloaded zips into FILM/img/ and report anything missing

prompts.txt lines look like:   012 | Soldiers march through a French village at dawn
The last line, "thumb | ...", is a picture for the thumbnail (subject on the right, dark empty space on the left).
Paragraphs that start with [host] use one shared presenter picture: pass it with --host, or put it at FILM/img/host.jpg.
"""
import argparse, glob, json, os, re, shutil, sys, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env
import tale

STYLES = {
    "oil": "A rich classical oil painting with visible brushstrokes, warm dramatic lighting, deep shadows and golden highlights, "
           "painted like an old master history painting, highly detailed.",
    "watercolour": "A soft ink and watercolour illustration on cream paper, fine pen lines and gentle washes of colour.",
    "storybook": "A warm, detailed children's storybook illustration with soft light and rich colours.",
    "photo": "A cinematic documentary photograph, natural light, shallow depth of field, realistic detail.",
    "paper": "A hand-drawn cartoon illustration in the style of a satirical newspaper drawing on warm textured paper, "
             "bold black ink outlines, flat bright colours with soft shading, big expressive exaggerated faces and reactions, "
             "one clear focal subject, cinematic lighting.",
    "comic": "A bold modern comic-book panel, thick ink lines, halftone shading, dramatic angles and strong colour contrast.",
}
NO_REAL = (" All people are invented characters, not real or famous people; never draw a likeness of a real person, "
           "company logo or brand mark.")
FRAME = (" The picture fills the entire frame edge to edge with no border, no frame, no paper margin, "
         "no text and no letters. Scene: ")


def style_line(s, character=""):
    """character: one sentence describing a recurring invented main character, so every picture shows the same
    person (for example "a round-faced businessman in his fifties with grey hair, big glasses and a black leather jacket")."""
    line = "Generate an image, wide 16:9 landscape. " + STYLES.get(s, s).rstrip()
    if s in ("paper", "comic") or character:
        line += NO_REAL
    if character:
        line += (" The recurring main character, drawn exactly the same in every picture whenever the scene includes him or her: "
                 + character.rstrip(". ") + ".")
    return line + FRAME


def read_prompts(film):
    p = f"{film}/prompts.txt"
    if not os.path.exists(p):
        sys.exit(f"{p} not found. Run: python tale/images.py prompts {film}")
    out = []
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        n, text = [x.strip() for x in line.split("|", 1)]
        if not text:
            continue
        out.append(["thumb" if n.lower() == "thumb" else int(n), text])
    return out


def cmd_prompts(film, force):
    items = tale.load(film)["items"]
    p = f"{film}/prompts.txt"
    if os.path.exists(p) and not force:
        sys.exit(f"{p} already exists (use --force to overwrite)")
    pics = [it for it in items if not it["host"]]
    lines = ["# One picture per line:  number | what the picture shows.",
             "# Describe a scene, not the words. Keep people, places and time period clear. Don't ask for text in the picture.",
             "# Replace the paragraph text below with your own descriptions, or use ai-helper.txt to have an AI write them.", ""]
    lines += [f"{it['i']:03d} | {it['text']}" for it in pics]
    lines += ["thumb | The main subject of the video on the right side of the frame, looking at the viewer. The left half is dark and simple."]
    open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    helper = ("Below is the script of my video, one numbered paragraph per line.\n"
              "For each paragraph, write ONE short description of a picture that shows it (a scene a painter could paint).\n"
              "Rules: one line per paragraph, in the format  NNN | description  (keep my numbers). Describe people, place, time\n"
              "period, light and mood. No text, letters or signs in the picture. No gore. Keep each description under 40 words.\n"
              "Finish with one extra line:  thumb | (a striking picture for the thumbnail: main subject on the right side,\n"
              "looking at the viewer, dark simple space on the left)\n\nSCRIPT:\n" +
              "\n".join(f"{it['i']:03d} | {it['text']}" for it in pics) + "\n")
    open(f"{film}/ai-helper.txt", "w", encoding="utf-8").write(helper)
    host = sum(1 for it in items if it["host"])
    print(f"wrote {p} ({len(pics)} pictures + thumbnail; {host} host paragraphs use the host picture)")
    print(f"Tip: paste {film}/ai-helper.txt into ChatGPT or Gemini and save its answer as {p}")


def cmd_snippet(film, style, character=""):
    prompts = read_prompts(film)
    tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser", "gemini-images.js"), encoding="utf-8").read()
    slug = re.sub(r"[^a-z0-9-]+", "-", os.path.basename(os.path.abspath(film)).lower()).strip("-") or "film"
    js = (tpl.replace('"__FILM__"', json.dumps(slug)).replace("__STYLE__", json.dumps(style_line(style, character)))
             .replace("__PROMPTS__", json.dumps(prompts, ensure_ascii=False)))
    out = f"{film}/gemini-snippet.js"
    open(out, "w", encoding="utf-8").write(js)
    print(f"wrote {out} with {len(prompts)} pictures.")
    print("Next: open https://gemini.google.com/app, press F12, choose Console, paste the whole file and press Enter.")


def cmd_import(film, zips, host):
    items = tale.load(film)["items"]
    os.makedirs(f"{film}/img", exist_ok=True)
    got = 0
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            for name in zf.namelist():
                base = os.path.basename(name)
                if not re.fullmatch(r"(\d{3}|thumb)\.(jpg|jpeg|png|webp)", base, re.I):
                    continue
                dst = f"{film}/thumb_src.jpg" if base.lower().startswith("thumb") else f"{film}/img/{base}"
                with zf.open(name) as src, open(dst, "wb") as out:
                    shutil.copyfileobj(src, out)
                got += 1
    host_src = host or next((p for p in glob.glob(f"{film}/img/host.*")), None)
    hosts = [it["i"] for it in items if it["host"]]
    if hosts and host_src:
        ext = os.path.splitext(host_src)[1].lower()
        for n in hosts:
            shutil.copyfile(host_src, f"{film}/img/{n:03d}{ext}")
    missing = [it["i"] for it in items if not tale.find_img(film, it["i"])]
    print(f"imported {got} pictures into {film}/img")
    if missing:
        print("still missing pictures for paragraphs:", ", ".join(map(str, missing)))
        if any(n in hosts for n in missing):
            print("  (host paragraphs need --host PICTURE or a picture at img/host.jpg)")
    else:
        print("every paragraph has a picture.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["prompts", "snippet", "import"]); ap.add_argument("film"); ap.add_argument("zips", nargs="*")
    ap.add_argument("--style", default=None); ap.add_argument("--character", default=None); ap.add_argument("--host"); ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    env.load_env()
    a.style = a.style or os.environ.get("T2F_IMAGE_STYLE") or "oil"
    a.character = a.character if a.character is not None else os.environ.get("T2F_CHARACTER", "")
    if a.cmd == "prompts": cmd_prompts(a.film, a.force)
    elif a.cmd == "snippet": cmd_snippet(a.film, a.style, a.character)
    else:
        if not a.zips: sys.exit("give the zip files to import")
        cmd_import(a.film, a.zips, a.host)
