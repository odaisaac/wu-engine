#!/usr/bin/env python3
"""Narration per shot via ElevenLabs. Usage: ELEVEN_KEY=... vo.py FILM_DIR [--voice ID] [--speed 1.05]
Each request carries the previous and next shot's text, so short shots still flow as one continuous read.
--speed (0.7–1.2) sets the voice's pace; 1.0 is the default.
After each clip, a stray blip at the very end (the next shot's first sound leaking in because of next_text,
heard as "si... Sinking") is cut off; the original is kept in vo_orig/."""
import json, os, shutil, subprocess, sys
import numpy as np


def trim_stray(path):
    """Cut a short sound (< 0.3 s) that follows >= 0.2 s of silence at the end of a clip. Returns seconds cut."""
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(pcm, np.float32); n = 320
    on = [20 * np.log10(np.sqrt(np.mean(x[i:i + n] ** 2)) + 1e-9) > -45 for i in range(0, len(x) - n, n)]
    segs, st = [], None
    for i, v in enumerate(on):
        if v and st is None: st = i
        if not v and st is not None: segs.append((st, i)); st = None
    if st is not None: segs.append((st, len(on)))
    if len(segs) < 2: return 0
    (a0, a1), (b0, b1) = segs[-2], segs[-1]
    if (b1 - b0) * 0.02 >= 0.3 or (b0 - a1) * 0.02 < 0.2: return 0
    keep = a1 * 0.02 + 0.15; full = len(x) / 16000
    bak = os.path.join(os.path.dirname(os.path.dirname(path)), "vo_orig"); os.makedirs(bak, exist_ok=True)
    orig = os.path.join(bak, os.path.basename(path))
    if not os.path.exists(orig): shutil.copy(path, orig)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", orig, "-t", f"{keep:.3f}", "-af", f"afade=t=out:st={keep - 0.08:.3f}:d=0.08",
                    "-c:a", "libmp3lame", "-q:a", "2", path], check=True)
    return full - keep

film = sys.argv[1]; voice = sys.argv[sys.argv.index("--voice") + 1] if "--voice" in sys.argv else "onwK4e9ZLuTAKqWW03F9"
speed = float(sys.argv[sys.argv.index("--speed") + 1]) if "--speed" in sys.argv else None
spec = json.load(open(f"{film}/spec.json")); key = os.environ["ELEVEN_KEY"]
os.makedirs(f"{film}/vo", exist_ok=True)
said = [s for s in spec["shots"] if s.get("text")]
for i, s in enumerate(said):
    out = f"{film}/vo/{s['id']}.mp3"
    if os.path.exists(out) and os.path.getsize(out) > 4000:
        cut = trim_stray(out)
        if cut: print(f"vo {s['id']}: cut a stray sound at the end ({cut:.2f} s)")
        continue
    vs = {"stability": 0.55, "similarity_boost": 0.75, "style": 0.15}
    if speed: vs["speed"] = speed
    base = {"text": s["text"], "model_id": "eleven_multilingual_v2", "voice_settings": vs}
    ctx = dict(base)
    if i > 0: ctx["previous_text"] = said[i - 1]["text"]
    if i < len(said) - 1: ctx["next_text"] = said[i + 1]["text"]
    for body in (ctx, ctx, base):   # fall back to a plain request if the context fields are refused
        r = subprocess.run(["curl", "-sS", "-o", out, "-w", "%{http_code}", "-X", "POST", f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128", "-H", "xi-api-key: " + key, "-H", "Content-Type: application/json", "-d", json.dumps(body)], capture_output=True, text=True)
        if r.stdout.strip() == "200": break
    else:
        print("FAILED", s["id"], open(out).read()[:200]); os.remove(out); sys.exit(1)
    cut = trim_stray(out)
    print("vo", s["id"], f"(cut a stray sound at the end, {cut:.2f} s)" if cut else "")
