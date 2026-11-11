#!/usr/bin/env python3
"""Build the final soundtrack: narration at each shot start + music bed at a fixed quiet level, ducked under the voice.
Usage: mix.py FILM_DIR MUSIC.mp3 [--bed -31] [--lufs -14] [--mstart auto|SECONDS] [--sfx [--sfx-db -14]]  -> FILM/mix.m4a
--mstart auto skips a quiet intro: the bed starts where the track first reaches its normal energy.
--sfx adds the engine's subtle sound-design layer (assets/sfx): whoosh into graphic scenes and
motion transitions, pop on stat/chart reveals, riser + impact into the title card, shutter on photos,
a tick on each overlay beat and a pop on the subscribe nudge.
The finished mix is loudness-normalised (two-pass loudnorm) to --lufs, default -14 LUFS = YouTube's playback reference."""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cues import shot_beats  # noqa: E402
film, music = sys.argv[1], sys.argv[2]
bed = float(sys.argv[sys.argv.index("--bed") + 1]) if "--bed" in sys.argv else -31.0
lufs = float(sys.argv[sys.argv.index("--lufs") + 1]) if "--lufs" in sys.argv else -14.0
mstart = sys.argv[sys.argv.index("--mstart") + 1] if "--mstart" in sys.argv else "0"
use_sfx = "--sfx" in sys.argv
sfx_db = float(sys.argv[sys.argv.index("--sfx-db") + 1]) if "--sfx-db" in sys.argv else -14.0
SFX = __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))), "assets", "sfx")


def music_offset(path):
    """First moment (after 1 s) where the track's 1-second RMS reaches 75% of its median energy."""
    import numpy as np
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "8000", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, np.float32); w = 8000
    rms = np.array([np.sqrt(np.mean(x[i:i + w] ** 2)) for i in range(0, len(x) - w, w)])
    med = float(np.median(rms))
    for i in range(1, len(rms)):
        if rms[i] >= 0.75 * med:
            return float(max(0, i - 1))
    return 0.0
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
off = music_offset(music) if mstart == "auto" else float(mstart)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "20", "-ss", f"{off:.2f}", "-i", music, "-t", f"{total:.2f}", "-af", f"volume={gain:.1f}dB,afade=t=in:d=3,afade=t=out:st={total-8:.2f}:d=8", f"{film}/music_bed.wav"], check=True)
# ---- sound design layer
events = []
if use_sfx and not __import__("os").path.exists(f"{SFX}/whoosh.mp3"):
    subprocess.run(["bash", f"{SFX}/make_sfx.sh"], check=True)   # kit is generated, not stored
if use_sfx:
    MOTION = {"whip", "push", "punch", "glitch", "split", "bar", "rise"}
    prev = None
    for sh in t["shots"]:
        sp = by[sh["id"]]; k = sp.get("kind", "graphic"); at = sh["start"] / 30
        ov = (sp.get("overlay") or {}).get("type")
        if prev is not None and (k in ("graphic", "subscribe", "endcard") or sp.get("transition") in MOTION or prev in ("graphic", "intro")):
            events.append(("whoosh.mp3", at - 0.35, 0))
        if k == "intro":
            events += [("riser.mp3", at - 1.6, -2), ("impact.mp3", at + 0.05, 0)]
        if k == "graphic" and ov in ("stat", "compare", "bars"):
            events.append(("pop.mp3", at + 0.7, -3))
        if k == "graphic" and ov == "list":
            n = len((sp.get("overlay") or {}).get("items", []))
            events += [("tick.mp3", at + 0.9 + 0.55 * j, -4) for j in range(n)]
        if k == "photo":
            events.append(("shutter.mp3", at + 0.1, -4))
        for fr in shot_beats(sp, sh)[1:-1]:          # each new overlay beat inside the shot
            events.append(("tick.mp3" if k != "graphic" else "pop.mp3", at + fr / 30, -6))
        if sp.get("nudge"):
            events.append(("pop.mp3", at + (24 + 65) / 30, -5))
        prev = k
if events:
    sins, sfl = [], []
    for j, (f, at, g) in enumerate(events):
        ms = max(0, int(at * 1000)); sins += ["-i", f"{SFX}/{f}"]
        sfl.append(f"[{j}:a]adelay={ms}|{ms},volume={sfx_db + g:.1f}dB[s{j}]")
    sfl.append("".join(f"[s{j}]" for j in range(len(events))) + f"amix=inputs={len(events)}:normalize=0,apad[sx]")
    open(f"{film}/sfx_filter.txt", "w").write(";".join(sfl))
    subprocess.run(["ffmpeg", "-y", "-v", "error", *sins, "-filter_complex_script", f"{film}/sfx_filter.txt", "-map", "[sx]", "-t", f"{total:.2f}", "-ac", "2", "-ar", "48000", f"{film}/sfx.wav"], check=True)
    extra, fc = ["-i", f"{film}/sfx.wav"], "[1:a][0:a]sidechaincompress=threshold=0.012:ratio=12:attack=10:release=800[d];[0:a][d][2:a]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.95[a]"
else:
    extra, fc = [], "[1:a][0:a]sidechaincompress=threshold=0.012:ratio=12:attack=10:release=800[d];[0:a][d]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[a]"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{film}/vo_mix.wav", "-i", f"{film}/music_bed.wav", *extra, "-filter_complex", fc,
    "-map", "[a]", f"{film}/mix_raw.wav"], check=True)
# two-pass loudness normalisation so the film plays at YouTube's reference level
ln = f"loudnorm=I={lufs}:TP=-1.5:LRA=11"
r = subprocess.run(["ffmpeg", "-v", "info", "-i", f"{film}/mix_raw.wav", "-af", ln + ":print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
j = json.loads(r[r.rindex("{"):r.rindex("}") + 1])
ln2 = (f"{ln}:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
       f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{film}/mix_raw.wav", "-af", ln2, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", f"{film}/mix.m4a"], check=True)
print(f"mix ok: music from {off:.1f}s, {len(events)} sfx, music {mean:.1f} dB -> {bed} dB bed, loudness {j['input_i']} -> {lufs} LUFS, {total:.1f}s")
