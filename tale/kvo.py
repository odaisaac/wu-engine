#!/usr/bin/env python3
"""Free narration for Plain Tale videos with Kokoro (open source, Apache 2.0). No key, no limit.

  kvo.py FILM [--voice am_michael] [--speed 0.88] [--only 1-12] [--models DIR]
Writes vo/NNN.mp3 and vo/NNN.json (per-character timing) in the same shape tale.py expects.
Each sentence is spoken on its own, so sentence timing is exact; timing inside a sentence is spread by length.
Model files (kokoro-v1.0.onnx, voices-v1.0.bin) come from the kokoro-onnx GitHub releases.
"""
import argparse, json, os, re, subprocess, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tale

PAUSE = 0.34          # silence between sentences inside a paragraph
COMMA = 0.0


def trim(x, sr, thr=0.004):
    """Cut leading and trailing silence, keep a small cushion."""
    w = sr // 100; n = len(x) // w
    if n < 5:
        return x
    rms = np.sqrt((x[:n * w].reshape(n, w) ** 2).mean(axis=1))
    idx = np.where(rms > thr)[0]
    if not len(idx):
        return x
    a = max(0, idx[0] * w - int(0.03 * sr)); b = min(len(x), (idx[-1] + 1) * w + int(0.09 * sr))
    y = x[a:b].copy(); k = int(0.03 * sr)
    y[-k:] *= np.linspace(1, 0, k)
    return y


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("film"); ap.add_argument("--voice", default="am_michael")
    ap.add_argument("--speed", type=float, default=0.88); ap.add_argument("--only")
    ap.add_argument("--models", default=os.path.expanduser("~/skillwork/models/kokoro"))
    a = ap.parse_args()
    from kokoro_onnx import Kokoro
    k = Kokoro(f"{a.models}/kokoro-v1.0.onnx", f"{a.models}/voices-v1.0.bin")
    lang = "en-gb" if a.voice.startswith("b") else "en-us"
    items = tale.load(a.film)["items"]; want = tale.pick(a.only, len(items))
    os.makedirs(f"{a.film}/vo", exist_ok=True)
    for it in items:
        n = it["i"]; mp3, js = f"{a.film}/vo/{n:03d}.mp3", f"{a.film}/vo/{n:03d}.json"
        if n not in want or (os.path.exists(mp3) and os.path.exists(js)):
            continue
        text = it["text"]
        sents = [m for m in re.finditer(r"[^.!?]+[.!?]+[\"'”’]?|[^.!?]+$", text) if m.group().strip()]
        audio, starts, ends, sr, t = [], [0.0] * len(text), [0.0] * len(text), 24000, 0.0
        for si, m in enumerate(sents):
            s = m.group(); lead = len(s) - len(s.lstrip())
            x, sr = k.create(s.strip(), voice=a.voice, speed=a.speed, lang=lang)
            x = trim(np.asarray(x, dtype=np.float32), sr); d = len(x) / sr
            a0, b0 = m.start() + lead, m.start() + len(s.rstrip())
            for c in range(m.start(), a0):
                starts[c] = ends[c] = t
            L = max(1, b0 - a0)
            for c in range(a0, b0):
                starts[c] = t + d * (c - a0) / L; ends[c] = t + d * (c - a0 + 1) / L
            for c in range(b0, m.end()):
                starts[c] = ends[c] = t + d
            audio.append(x); t += d
            if si + 1 < len(sents):
                audio.append(np.zeros(int(PAUSE * sr), dtype=np.float32)); t += PAUSE
        y = np.concatenate(audio)
        p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-", "-ar", "44100", "-b:a", "160k", mp3], input=y.tobytes())
        if p.returncode:
            sys.exit(f"could not write {mp3}")
        json.dump({"chars": list(text), "starts": [round(v, 3) for v in starts], "ends": [round(v, 3) for v in ends]}, open(js, "w"))
        print(f"{n:03d} {len(y) / sr:.1f}s", flush=True)


if __name__ == "__main__":
    main()
