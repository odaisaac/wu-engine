#!/usr/bin/env python3
"""Storyboard approval page: one frame per scene + narration + on-screen text + source + clip credits.

  python3 tools/storyboard.py FILM [--stills FILM/qa]   -> FILM/qa/storyboard.html (self-contained)

Stills: FILM/qa/sNN.png in shot order (the contact-sheet stills from the QA step). The page also
embeds the plan-check result. Publish it as an artifact so Damilare can approve (or flag scenes by
number) before the long render. Frames are embedded as JPEG data URIs, so the file stands alone.
"""
import base64, html, io, json, os, subprocess, sys
from PIL import Image

film = sys.argv[1]
qa = sys.argv[sys.argv.index("--stills") + 1] if "--stills" in sys.argv else os.path.join(film, "qa")
spec = json.load(open(os.path.join(film, "spec.json")))
T = {t["id"]: t for t in json.load(open(os.path.join(film, "timing.json")))["shots"]}
FJ = json.load(open(os.path.join(film, "files.json"))) if os.path.exists(os.path.join(film, "files.json")) else {}
OC = json.load(open(os.path.join(film, "open_credits.json"))) if os.path.exists(os.path.join(film, "open_credits.json")) else {}
check = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "plancheck.py"), film], capture_output=True, text=True).stdout
E = html.escape


def img(i):
    p = os.path.join(qa, f"s{i + 1:02d}.png")
    if not os.path.exists(p):
        return ""
    im = Image.open(p).convert("RGB"); im.thumbnail((640, 360))
    b = io.BytesIO(); im.save(b, "JPEG", quality=78)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def ov_text(o):
    if not o:
        return ""
    t = o.get("type")
    if t == "kinetic": return f"“{o.get('text', '')}”"
    if t == "stat": return f"{o.get('prefix', '')}{o.get('value')}{o.get('suffix', '')} — {o.get('label', '')}"
    if t in ("bars", "compare"): return f"{o.get('title', '')}: " + ", ".join(f"{x.get('label')} {x.get('display', x.get('value'))}" for x in o.get("items", []))
    if t == "list": return f"{o.get('title', '')}: " + " · ".join(o.get("items", []))
    if t == "flow": return f"{o.get('title', '')}: " + " → ".join(x["label"] for x in o.get("steps", []))
    if t == "map": return f"Map: {o.get('title', '')} — {o.get('note', '')}"
    if t == "quote": return f"“{o.get('text', '')}” — {o.get('by', '')}"
    if t == "title": return o.get("text", "")
    return t or ""


def mmss(f):
    s = f // 30
    return f"{s // 60}:{s % 60:02d}"


cards = []
for i, s in enumerate(spec["shots"]):
    t = T.get(s["id"], {"start": 0, "dur": 0})
    clips = ", ".join(os.path.basename(p).replace(".mp4", "") for p in FJ.get(s["id"], s.get("files", [])) or [])
    oc = "; ".join(f"{c['credit']} ({c['license']})" for c in OC.get(s["id"], []))
    src = img(i)
    cards.append(f"""<article class="card" id="s{s['id']}">
  <div class="frame">{f'<img src="{src}" alt="Scene {E(s["id"])}" loading="lazy">' if src else '<div class="nofr">no still</div>'}<span class="no">{E(s['id'])}</span><span class="tc">{mmss(t['start'])} · {t['dur'] / 30:.0f}s</span></div>
  <div class="meta"><span class="kind">{E(s.get('kind', 'graphic'))}</span>{f'<span class="ov">{E(ov_text(s.get("overlay")))}</span>' if s.get('overlay') else ''}</div>
  <p class="vo">{E(s.get('text', ''))}</p>
  {f'<p class="src">Source: {E(s["source"])}</p>' if s.get('source') else ''}
  {f'<p class="clips">Clips: {E(clips)}</p>' if clips else ''}{f'<p class="clips">{E(oc)}</p>' if oc else ''}
</article>""")

title = spec.get("title", "Storyboard")
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} Storyboard</title>
<style>
:root{{--bg:#F6F3EE;--card:#FFFFFF;--ink:#1B1A17;--mute:#6B665E;--line:#E4DED4;--acc:#B5452B;--chip:#EFE9DF}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#121315;--card:#1B1D20;--ink:#ECE8E1;--mute:#9C978F;--line:#2C2F33;--acc:#E7774F;--chip:#25282C}}}}
:root[data-theme="dark"]{{--bg:#121315;--card:#1B1D20;--ink:#ECE8E1;--mute:#9C978F;--line:#2C2F33;--acc:#E7774F;--chip:#25282C}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}}
header{{padding:28px 16px 8px;max-width:1280px;margin:auto}}h1{{font:600 28px/1.15 Georgia,"Times New Roman",serif;margin:0 0 6px}}
.sub{{color:var(--mute);margin:0}}details{{max-width:1280px;margin:14px auto 0;padding:0 16px}}summary{{cursor:pointer;color:var(--acc);font-weight:600}}
pre{{white-space:pre-wrap;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;font-size:13px}}
main{{max-width:1280px;margin:18px auto 40px;padding:0 16px;display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}}
.frame{{position:relative;aspect-ratio:16/9;background:#000}}.frame img{{width:100%;height:100%;object-fit:cover;display:block}}
.nofr{{color:#888;display:grid;place-items:center;height:100%}}
.no{{position:absolute;left:8px;top:8px;background:var(--acc);color:#fff;font-weight:700;border-radius:6px;padding:1px 8px}}
.tc{{position:absolute;right:8px;bottom:8px;background:#000B;color:#fff;font-size:12px;border-radius:6px;padding:1px 7px}}
.meta{{display:flex;gap:6px;flex-wrap:wrap;padding:10px 12px 0}}.kind{{background:var(--chip);border-radius:999px;padding:1px 9px;font-size:12px;color:var(--mute)}}
.ov{{font-size:13px;font-weight:600}}.vo{{margin:8px 12px;font-size:14px}}.src,.clips{{margin:0 12px 8px;font-size:12px;color:var(--mute)}}
</style></head><body>
<header><h1>Storyboard: {E(title)}</h1><p class="sub">{len(spec['shots'])} scenes · {mmss(json.load(open(os.path.join(film, 'timing.json')))['total'])} · reply with scene numbers to change before the full render.</p></header>
<details><summary>Plan check</summary><pre>{E(check)}</pre></details>
<main>
{''.join(cards)}
</main></body></html>"""
out = os.path.join(film, "qa", "storyboard.html")
open(out, "w").write(page)
print(out, f"{len(page) / 1e6:.1f} MB")
