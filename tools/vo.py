#!/usr/bin/env python3
"""Narration per shot via ElevenLabs. Usage: ELEVEN_KEY=... vo.py FILM_DIR [--voice ID]"""
import json, os, subprocess, sys
film = sys.argv[1]; voice = sys.argv[sys.argv.index("--voice") + 1] if "--voice" in sys.argv else "onwK4e9ZLuTAKqWW03F9"
spec = json.load(open(f"{film}/spec.json")); key = os.environ["ELEVEN_KEY"]
os.makedirs(f"{film}/vo", exist_ok=True)
for s in spec["shots"]:
    if not s.get("text"): continue
    out = f"{film}/vo/{s['id']}.mp3"
    if os.path.exists(out) and os.path.getsize(out) > 4000: continue
    body = json.dumps({"text": s["text"], "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.55, "similarity_boost": 0.75, "style": 0.15}})
    for _ in range(3):
        r = subprocess.run(["curl", "-sS", "-o", out, "-w", "%{http_code}", "-X", "POST", f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128", "-H", "xi-api-key: " + key, "-H", "Content-Type: application/json", "-d", body], capture_output=True, text=True)
        if r.stdout.strip() == "200": break
    else:
        print("FAILED", s["id"], open(out).read()[:200]); os.remove(out); sys.exit(1)
    print("vo", s["id"])
