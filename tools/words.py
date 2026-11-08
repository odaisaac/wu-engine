#!/usr/bin/env python3
"""Word-level timings for every narration clip (free, local).

  python3 tools/words.py FILM [--only 03,07] [--model base.en]

Runs faster-whisper with word timestamps on FILM/vo/<id>.mp3, then aligns the
recognised words to the SCRIPT words (so spelling and numbers match the spec,
not the recogniser). Words the recogniser missed get times interpolated from
their neighbours. Result is written into FILM/timing.json as
  shots[i].words = [[word, startFrame, endFrame], ...]   (frames from shot start, 30 fps)
Film.tsx uses these for exact caption timing; the Short composition uses them for
word-by-word captions. Re-run after re-recording any narration.
"""
import argparse, difflib, json, os, re, subprocess
import numpy as np

FPS = 30


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def align(script, rec):
    """script: [word]; rec: [(word, start, end)] -> [(word, start, end)] for script words."""
    a, b = [norm(w) for w in script], [norm(w) for w, _, _ in rec]
    out = [None] * len(script)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            _, s, e = rec[blk.b + k]
            out[blk.a + k] = [s, e]
    # interpolate gaps (numbers spelled differently, names, etc.)
    known = [i for i, v in enumerate(out) if v]
    if not known:
        return []
    for i in range(len(out)):
        if out[i]:
            continue
        prev = max([k for k in known if k < i], default=None)
        nxt = min([k for k in known if k > i], default=None)
        t0 = out[prev][1] if prev is not None else rec[0][1]
        t1 = out[nxt][0] if nxt is not None else rec[-1][2]
        lo, hi = (prev if prev is not None else -1), (nxt if nxt is not None else len(out))
        n = hi - lo - 1
        j = i - lo - 1
        step = (t1 - t0) / max(n, 1)
        out[i] = [t0 + j * step, t0 + (j + 1) * step]
    return [(w, s, e) for w, (s, e) in zip(script, out)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film"); ap.add_argument("--only", default=""); ap.add_argument("--model", default="base.en")
    a = ap.parse_args()
    from faster_whisper import WhisperModel
    m = WhisperModel(a.model, device="cpu", compute_type="int8")
    spec = {s["id"]: s for s in json.load(open(os.path.join(a.film, "spec.json")))["shots"]}
    tp = os.path.join(a.film, "timing.json")
    timing = json.load(open(tp))
    only = set(filter(None, a.only.split(",")))
    for t in timing["shots"]:
        s = spec.get(t["id"], {})
        mp3 = os.path.join(a.film, "vo", f"{t['id']}.mp3")
        if not s.get("text") or not os.path.exists(mp3) or (only and t["id"] not in only):
            continue
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", mp3, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
        segs, _ = m.transcribe(np.frombuffer(pcm, np.float32), word_timestamps=True, beam_size=5, language="en")
        rec = [(w.word.strip(), w.start, w.end) for sg in segs for w in (sg.words or [])]
        al = align(s["text"].split(), rec)
        t["words"] = [[w, round(st * FPS), max(round(en * FPS), round(st * FPS) + 2)] for w, st, en in al]
        hit = sum(1 for w in s["text"].split() if norm(w) in {norm(r[0]) for r in rec})
        print(t["id"], f"{len(al)} words, {hit / max(1, len(al)):.0%} matched")
    json.dump(timing, open(tp, "w"), indent=1)


if __name__ == "__main__":
    main()
