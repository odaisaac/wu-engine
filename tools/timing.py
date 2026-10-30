#!/usr/bin/env python3
"""Shot timing from narration lengths. Usage: timing.py FILM_DIR"""
import json, math, subprocess, sys
film = sys.argv[1]; spec = json.load(open(f"{film}/spec.json"))
dur = lambda p: float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))
start = 30; out = []
for s in spec["shots"]:
    d = dur(f"{film}/vo/{s['id']}.mp3") if s.get("text") else s.get("seconds", 4)
    fr = math.ceil((d + s.get("pad", 0.6)) * 30)
    out.append({"id": s["id"], "start": start, "dur": fr}); start += fr
json.dump({"fps": 30, "total": start + 30, "shots": out}, open(f"{film}/timing.json", "w"), indent=1)
print(f"{len(out)} shots, {start/30/60:.2f} min")
