#!/usr/bin/env python3
"""Build the final soundtrack: narration at each shot start + music bed at a fixed quiet level, ducked under the voice.
Usage: mix.py FILM_DIR MUSIC.mp3 [--bed -31]  -> FILM/mix.m4a"""
import json, re, subprocess, sys
film, music = sys.argv[1], sys.argv[2]
bed = float(sys.argv[sys.argv.index("--bed") + 1]) if "--bed" in sys.argv else -31.0
spec = json.load(open(f"{film}/spec.json")); t = json.load(open(f"{film}/timing.json"))
total = t["total"] / 30
ins, fl, lab = [], [], []
by = {s["id"]: s for s in spec["shots"]}
for sh in t["shots"]:
    if not by[sh["id"]].get("text"): continue
    k = len(lab); ins += ["-i", f"{film}/vo/{sh['id']}.mp3"]; ms = int(sh["start"] / 30 * 1000)
    fl.append(f"[{k}:a]adelay={ms}|{ms}[v{k}]"); lab.append(f"[v{k}]")
fl.append("".join(lab) + f"amix=inputs={len(lab)}:normalize=0,apad[vo]")
open(f"{film}/vo_filter.txt", "w").write(";".join(fl))
subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex_script", f"{film}/vo_filter.txt", "-map", "[vo]", "-t", f"{total:.2f}", "-ac", "2", f"{film}/vo_mix.wav"], check=True)
m = subprocess.run(["ffmpeg", "-v", "info", "-i", music, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
mean = float(re.search(r"mean_volume: (-?[\d.]+)", m).group(1)); gain = bed - mean
subprocess.run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "20", "-i", music, "-t", f"{total:.2f}", "-af", f"volume={gain:.1f}dB,afade=t=in:d=3,afade=t=out:st={total-8:.2f}:d=8", f"{film}/music_bed.wav"], check=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{film}/vo_mix.wav", "-i", f"{film}/music_bed.wav", "-filter_complex",
    "[1:a][0:a]sidechaincompress=threshold=0.012:ratio=12:attack=10:release=800[d];[0:a][d]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[a]",
    "-map", "[a]", "-c:a", "aac", "-b:a", "192k", f"{film}/mix.m4a"], check=True)
print(f"mix ok: music {mean:.1f} dB -> {bed} dB bed, {total:.1f}s")
