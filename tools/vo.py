#!/usr/bin/env python3
"""Narration per shot via ElevenLabs. Usage: ELEVEN_KEY=... vo.py FILM_DIR [--voice ID] [--speed 1.05]
Each request carries the previous and next shot's text, so short shots still flow as one continuous read.
--speed (0.7–1.2) sets the voice's pace; 1.0 is the default."""
import json, os, subprocess, sys
film = sys.argv[1]; voice = sys.argv[sys.argv.index("--voice") + 1] if "--voice" in sys.argv else "onwK4e9ZLuTAKqWW03F9"
speed = float(sys.argv[sys.argv.index("--speed") + 1]) if "--speed" in sys.argv else None
spec = json.load(open(f"{film}/spec.json")); key = os.environ["ELEVEN_KEY"]
os.makedirs(f"{film}/vo", exist_ok=True)
said = [s for s in spec["shots"] if s.get("text")]
for i, s in enumerate(said):
    out = f"{film}/vo/{s['id']}.mp3"
    if os.path.exists(out) and os.path.getsize(out) > 4000: continue
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
    print("vo", s["id"])
