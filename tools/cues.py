#!/usr/bin/env python3
"""Sentence cues and overlay-beat boundaries for a shot — the Python mirror of sentenceCues/beatBounds in Film.tsx.
Used by plancheck.py (how long each visual holds) and mix.py (a tick on each beat)."""
import math, re

END = re.compile(r"[.!?][\"')\]]?$")


def sentence_cues(text, dur, words=None):
    ws = (text or "").split()
    if not ws:
        return [0]
    starts = [0] + [i + 1 for i, w in enumerate(ws) if END.search(w) and i < len(ws) - 1]
    if words and len(words) == len(ws):
        return [words[i][1] for i in starts]
    pos, acc = [], 0
    for w in ws:
        pos.append(acc); acc += len(w) + 1
    return [round(pos[i] / acc * max(1, dur - 18)) for i in starts]


def beat_bounds(n, cues, dur, explicit=None):
    explicit = explicit or []
    b, m = [0], len(cues)
    for k in range(1, n):
        ci = explicit[k] if k < len(explicit) and explicit[k] is not None else (math.floor(k * m / n + 0.5) if m >= n else -1)
        fr = cues[ci] - 3 if 0 <= ci < m else math.floor(k * dur / n + 0.5)
        b.append(min(max(fr, b[k - 1] + 24), dur - 24))
    return b + [dur]


def shot_beats(shot, t):
    """Frame offsets (shot-local) where each overlay beat starts, for a spec shot and its timing entry."""
    lst = [o for o in [shot.get("overlay")] + list(shot.get("then") or []) if o]
    if not lst:
        return [0, t["dur"]]
    return beat_bounds(len(lst), sentence_cues(shot.get("text"), t["dur"], t.get("words")), t["dur"], [o.get("cue") for o in lst])


def clips_for(secs, cut=4.5):
    """How many different clips a footage shot of this length should cut between."""
    return max(1, min(6, math.ceil(secs / cut - 0.15)))
