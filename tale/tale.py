#!/usr/bin/env python3
"""Plain Tale engine: slow-English story videos from a script, stills and narration.

  tale.py parse  FILM            script.md -> plan.json (one paragraph = one picture)
  tale.py vo     FILM [--voice ID] [--only 1-12]   ElevenLabs narration with timestamps (ELEVEN_KEY in env)
  tale.py fake   FILM [--only 1-12]   silent stand-in audio + numbered stand-in pictures (engine tests)
  tale.py build  FILM [--only 1-12] [--music FILE] [--out NAME]   render clips, captions, mix, final mp4

FILM folder: script.md, img/001.png..., vo/001.mp3 + vo/001.json, clips/, final.mp4
Keys are read from the environment only. Never write them to files.
"""
import argparse, base64, json, os, re, subprocess, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

FPS = 30
W, H = 1920, 1080
GAP = 0.75            # silence after each paragraph (speech is trimmed to its true end first)
CHAPTER_GAP = 1.1     # extra silence before a new chapter
FONT = "Inter"
HL = "&H4DC9FF&"      # amber, ASS is BGR
STOP = set("a an the and or but of to in on at for with from by as is are was were be been it its this that these those he she they we you i his her their our your him them not no so if then than there here had has have did do does will would could can very more most only just about into over after before again when while who what how why one two".split())


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def dur_of(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout.strip())


def speech_end(path):
    """Where the spoken words really end. ElevenLabs sometimes adds the start of a breath or of the
    next word after a short silence at the end of a file; cut inside that silence so it is never heard."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(float) / 32768
    n = len(x) // 160
    if n < 30:
        return len(x) / 16000
    db = 20 * np.log10(np.sqrt((x[:n * 160].reshape(n, 160) ** 2).mean(axis=1) + 1e-12))
    loud = db > -40
    end, run, L = n, 0, None
    for k in range(n):                                  # L = last frame of the last solid stretch of speech (120 ms or more)
        run = run + 1 if loud[k] else 0
        if run >= 12:
            L = k
    if L is None:
        return n * 0.01
    while L + 1 < n and loud[L + 1]:
        L += 1
    after = db[L + 1:]
    q = 0; has_gap = False
    for v in after:                                     # is there real silence (60 ms or more) after it?
        q = q + 1 if v < -55 else 0
        if q >= 6:
            has_gap = True; break
    if not has_gap:
        return n * 0.01                                 # speech runs to the end of the file: keep everything
    return min((L + 1) * 0.01 + 0.14, n * 0.01)


def pick(only, n):
    if not only:
        return set(range(1, n + 1))
    out = set()
    for part in only.split(","):
        a, _, b = part.partition("-")
        out |= set(range(int(a), int(b or a) + 1))
    return out


# ---------- parse ----------
def parse(film):
    items, chapter, title = [], None, None
    for line in open(f"{film}/script.md", encoding="utf-8").read().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            title = line[2:].strip(); continue
        if line.startswith("## "):
            chapter = line[3:].strip(); continue
        host = line.startswith("[host]")
        text = line.replace("[host]", "").strip()
        first = chapter is not None and (not items or items[-1]["chapter"] != chapter)
        items.append({"i": len(items) + 1, "chapter": chapter, "first": first, "host": host, "text": text})
    plan = {"title": title, "items": items}
    json.dump(plan, open(f"{film}/plan.json", "w"), indent=1, ensure_ascii=False)
    words = sum(len(x["text"].split()) for x in items)
    print(f"{len(items)} paragraphs, {words} words, about {words / 125:.0f} min of narration")
    return plan


def load(film):
    if not os.path.exists(f"{film}/plan.json") or os.path.getmtime(f"{film}/plan.json") < os.path.getmtime(f"{film}/script.md"):
        return parse(film)
    return json.load(open(f"{film}/plan.json"))


# ---------- narration ----------
def vo(film, voice, only, speed):
    key = os.environ.get("ELEVEN_KEY")
    if not key:
        sys.exit("ELEVEN_KEY is not set")
    items = load(film)["items"]
    os.makedirs(f"{film}/vo", exist_ok=True)
    want = pick(only, len(items))
    for k, it in enumerate(items):
        n = it["i"]
        mp3, js = f"{film}/vo/{n:03d}.mp3", f"{film}/vo/{n:03d}.json"
        if n not in want or (os.path.exists(mp3) and os.path.exists(js)):
            continue
        body = {"text": it["text"], "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.55, "similarity_boost": 0.8, "style": 0.0, "speed": speed},
                "previous_text": items[k - 1]["text"] if k else None}
        body = {a: b for a, b in body.items() if b is not None}
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128",
            data=json.dumps(body).encode(), headers={"xi-api-key": key, "Content-Type": "application/json"})
        try:
            res = json.load(urllib.request.urlopen(req, timeout=120))
        except urllib.error.HTTPError as e:
            sys.exit(f"paragraph {n}: ElevenLabs said {e.code}: {e.read().decode()[:300]}")
        open(mp3, "wb").write(base64.b64decode(res["audio_base64"]))
        al = res.get("alignment") or {}
        json.dump({"chars": al.get("characters", []), "starts": al.get("character_start_times_seconds", []),
                   "ends": al.get("character_end_times_seconds", [])}, open(js, "w"))
        print(f"{n:03d} ok {dur_of(mp3):.1f}s")


def fake(film, only):
    items = load(film)["items"]
    os.makedirs(f"{film}/vo", exist_ok=True); os.makedirs(f"{film}/img", exist_ok=True)
    cols = ["0x6b4f2a", "0x2f4a5c", "0x4d5b3a", "0x5a3a44"]
    for it in items:
        n = it["i"]
        if n not in pick(only, len(items)):
            continue
        d = len(it["text"].split()) / 125 * 60
        if not os.path.exists(f"{film}/vo/{n:03d}.mp3"):
            run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{d:.2f}", f"{film}/vo/{n:03d}.mp3"])
        if not any(os.path.exists(f"{film}/img/{n:03d}.{e}") for e in ("png", "jpg", "jpeg", "webp")):
            run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                 f"gradients=s=1920x1080:c0={cols[n % 4]}:c1=0x111111:x0=0:y0=0:x1=1920:y1=1080", "-frames:v", "1",
                 "-vf", f"drawtext=text='picture {n}':fontsize=140:fontcolor=white@0.5:x=(w-tw)/2:y=(h-th)/2", f"{film}/img/{n:03d}.png"])
    print("stand-ins ready")


# ---------- captions ----------
def chunks(text, maxc=44):
    """Split into caption lines at clause breaks, each at most ~maxc characters."""
    out = []
    for sent in re.findall(r"[^.!?]+[.!?]+[\"'”’]?|[^.!?]+$", text):
        sent = sent.strip()
        if not sent:
            continue
        parts = re.split(r"(?<=[,;:])\s+", sent)
        cur = ""
        for p in parts:
            if cur and len(cur) + 1 + len(p) > maxc:
                out.append(cur); cur = p
            else:
                cur = (cur + " " + p).strip()
        if cur:
            out.append(cur)
    fin = []
    for c in out:
        while len(c) > maxc + 10:                     # still too long: break near the middle on a space
            ws = c.split(" "); mid = len(ws) // 2
            fin.append(" ".join(ws[:mid])); c = " ".join(ws[mid:])
        fin.append(c)
    merged = []
    for c in fin:                                     # never leave a one-word line on its own
        if merged and (len(c.split()) < 2 or len(merged[-1].split()) < 2) and len(merged[-1]) + len(c) < maxc + 14:
            merged[-1] += " " + c
        else:
            merged.append(c)
    return merged


def chunk_times(text, parts, align, total):
    """Start and end time of each caption line, from character timestamps when present."""
    spans, pos = [], 0
    for p in parts:
        a = text.find(p, pos)
        a = pos if a < 0 else a
        spans.append((a, a + len(p))); pos = a + len(p)
    st = (align or {}).get("starts") or []
    en = (align or {}).get("ends") or []
    out = []
    for a, b in spans:
        if st and len(st) >= len(text) - 2:
            s = st[min(a, len(st) - 1)]; e = en[min(b - 1, len(en) - 1)]
        else:
            s = total * a / max(1, len(text)); e = total * b / max(1, len(text))
        out.append([s, e])
    for k in range(len(out) - 1):                     # hold each line until the next begins
        out[k][1] = out[k + 1][0]
    if out:
        out[-1][1] = max(out[-1][1], total)
    return out


def keyword(line):
    ws = [(len(re.sub(r"\W", "", w)), k) for k, w in enumerate(line.split()) if re.sub(r"\W", "", w).lower() not in STOP]
    return max(ws)[1] if ws else -1


def ass_time(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def write_ass(path, text, align, vdur, chapter, brand, lead=0.0):
    parts = chunks(text)
    times = [[s + lead, e + lead + (GAP if k == len(parts) - 1 else 0)] for k, (s, e) in enumerate(chunk_times(text, parts, align, vdur))]
    parts and times[0].__setitem__(0, max(0.0, times[0][0]))
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},74,&H00FFFFFF,&H00FFFFFF,&H00141414,&H96000000,1,0,0,0,100,100,0,0,1,5,3,2,160,160,96,1
Style: Chap,{FONT},44,&H00E9F4FF,&H00FFFFFF,&H00141414,&H96000000,1,0,0,0,100,100,3,0,1,3,2,9,70,70,56,1
Style: Brand,DejaVu Serif,58,&H005CC8FF,&H00FFFFFF,&H00101010,&H96000000,1,0,0,0,100,100,0,0,1,4,2,7,56,56,44,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = [f"Dialogue: 0,0:00:00.00,{ass_time(9999)},Brand,,0,0,0,,{brand}"]
    if chapter:
        ev.append(f"Dialogue: 1,0:00:00.20,0:00:04.80,Chap,,0,0,0,,{{\\fad(400,500)}}{chapter.upper()}")
    for p, (s, e) in zip(parts, times):
        ws = p.split(); k = keyword(p)
        if k >= 0:
            ws[k] = f"{{\\c{HL}}}{ws[k]}{{\\c&HFFFFFF&}}"
        ev.append(f"Dialogue: 2,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{{\\fad(120,0)}}{' '.join(ws)}")
    open(path, "w", encoding="utf-8").write(head + "\n".join(ev) + "\n")
    return parts, times


# ---------- build ----------
MOVES = ["in", "left", "out", "right", "in", "out"]
SRC_W, SRC_H = 2400, 1350     # working size of every picture (1.25x the frame)
FADE = 14                     # frames of dissolve from the previous picture


def load_src(path):
    import cv2
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    h, w = img.shape[:2]; k = max(SRC_W / w, SRC_H / h)
    img = cv2.resize(img, (round(w * k), round(h * k)), interpolation=cv2.INTER_LANCZOS4 if k > 1 else cv2.INTER_AREA)
    h, w = img.shape[:2]; y0 = (h - SRC_H) // 2; x0 = (w - SRC_W) // 2
    img = img[y0:y0 + SRC_H, x0:x0 + SRC_W]
    if k > 1.3:                                       # enlarged a lot: bring back some edge definition
        blur = cv2.GaussianBlur(img, (0, 0), 1.6)
        img = cv2.addWeighted(img, 1.55, blur, -0.55, 0)
    return img


def frame_at(src, move, t):
    """One frame of the slow camera move at progress t (0..1). Sub-pixel exact, so it never jitters."""
    import cv2, numpy as np
    z0, z1 = 1.0, 1.085
    if move == "in":
        z, cx, cy = z0 + (z1 - z0) * t, 0.5, 0.5
    elif move == "out":
        z, cx, cy = z1 - (z1 - z0) * t, 0.5, 0.5
    else:
        z = 1.07; span = (1 - 1 / z) / 2
        cx = 0.5 + span * (1 - 2 * t) * (1 if move == "left" else -1); cy = 0.5
    vw, vh = SRC_W / z, SRC_H / z                      # visible window in source pixels
    x0, y0 = cx * SRC_W - vw / 2, cy * SRC_H - vh / 2
    k = W / vw
    M = np.float32([[k, 0, -x0 * k], [0, k, -y0 * k]])
    return cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_AREA if k < 0.6 else cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def move_of(n, host):
    return "in" if host else MOVES[n % len(MOVES)]


def render_clip(img, prev, n, host, frames, ass, audio, lead, clip, adur):
    import cv2
    src = load_src(img)
    last = frame_at(load_src(prev[0]), move_of(prev[1], prev[2]), 1.0) if prev else None
    esc = ass.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-vf", f"subtitles='{esc}',format=yuv420p", "-frames:v", str(frames), "-an", "-c:v", "libx264", "-preset", "veryfast",
                          "-crf", "18", clip], stdin=subprocess.PIPE)
    mv = move_of(n, host)
    for f in range(frames):
        fr = frame_at(src, mv, f / max(1, frames - 1))
        if last is not None and f < FADE:
            a = (f + 1) / (FADE + 1)
            fr = cv2.addWeighted(fr, a, last, 1 - a, 0)
        p.stdin.write(fr.tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError(f"ffmpeg failed on clip {n}")


def find_img(film, n):
    for e in ("png", "jpg", "jpeg", "webp"):
        p = f"{film}/img/{n:03d}.{e}"
        if os.path.exists(p):
            return p
    return None


def build(film, only, music, out, brand, workers):
    plan = load(film); items = plan["items"]
    want = sorted(pick(only, len(items)))
    os.makedirs(f"{film}/clips", exist_ok=True)
    missing = [n for n in want if not find_img(film, n) or not os.path.exists(f"{film}/vo/{n:03d}.mp3")]
    if missing:
        sys.exit(f"missing picture or narration for paragraphs: {missing[:20]}")
    jobs, cues, t0 = [], [], 0.0
    for idx, n in enumerate(want):
        it = items[n - 1]
        a = speech_end(f"{film}/vo/{n:03d}.mp3")
        lead = CHAPTER_GAP if (it["first"] and idx) else 0.0
        frames = round((lead + a + GAP) * FPS)
        pv = want[idx - 1] if idx else None
        prev = (find_img(film, pv), pv, items[pv - 1]['host']) if pv else None
        jobs.append((n, it, a, lead, frames, prev)); cues.append((n, t0 + lead, it)); t0 += frames / FPS

    def one(job):
        n, it, a, lead, frames, prev = job
        clip, ass = f"{film}/clips/{n:03d}.mp4", f"{film}/clips/{n:03d}.ass"
        aj = f"{film}/vo/{n:03d}.json"
        align = json.load(open(aj)) if os.path.exists(aj) else None
        text = it["text"]
        write_ass(ass, text, align, a, it["chapter"] if it["first"] else None, brand, lead)
        sig = f"v4|{a:.3f}|{frames}|{os.path.getmtime(find_img(film, n))}|{prev and os.path.getmtime(prev[0])}|{open(ass).read()}"
        sigf = clip + ".sig"
        if os.path.exists(clip) and os.path.exists(sigf) and open(sigf).read() == sig:
            return n
        render_clip(find_img(film, n), prev, n, it['host'], frames, ass, f"{film}/vo/{n:03d}.mp3", lead, clip, a)
        open(sigf, "w").write(sig)
        return n

    with ThreadPoolExecutor(workers) as ex:
        for k, n in enumerate(ex.map(one, jobs)):
            if (k + 1) % 10 == 0 or k + 1 == len(jobs):
                print(f"clips {k + 1}/{len(jobs)}", flush=True)

    lst = f"{film}/clips/list.txt"
    open(lst, "w").write("".join(f"file '{n:03d}.mp4'\n" for n in want))
    raw = f"{film}/clips/_joined.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", raw])
    total = dur_of(raw)
    # voice: every paragraph placed at its exact sample position, so sound never drifts from the picture
    import numpy as np, wave
    SR = 48000
    track = np.zeros(int(sum(j[4] for j in jobs) / FPS * SR) + SR, dtype=np.float32)
    pos = 0
    for n, it, a, lead, frames, prev in jobs:
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", f"{film}/vo/{n:03d}.mp3", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
        x = np.frombuffer(pcm, dtype=np.float32)[:int(a * SR)].copy()
        k = min(len(x), int(0.06 * SR))
        if k:
            x[-k:] *= np.linspace(1, 0, k, dtype=np.float32)
        s0 = int(round((pos / FPS + lead) * SR)); track[s0:s0 + len(x)] += x
        pos += frames
    track = track[:int(pos / FPS * SR)]
    voice = f"{film}/clips/_voice.wav"
    with wave.open(voice, "wb") as wv:
        wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes((np.clip(track, -1, 1) * 32767).astype("<i2").tobytes())
    # mix: voice (+ quiet music bed, ducked), two-pass loudness to -14 LUFS
    if music:
        graph = (f"[2:a]aloop=loop=-1:size=2e9,atrim=0:{total:.2f},volume=-27dB,afade=t=in:d=3,afade=t=out:st={max(0, total - 5):.2f}:d=5[m];"
                 f"[1:a]asplit[v1][v2];[m][v2]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=600[md];[v1][md]amix=inputs=2:normalize=0[mix]")
        ins = ["-i", raw, "-i", voice, "-i", music]
    else:
        graph = "[1:a]anull[mix]"; ins = ["-i", raw, "-i", voice]
    p = subprocess.run(["ffmpeg", "-hide_banner", *ins, "-filter_complex", graph + ";[mix]aformat=channel_layouts=stereo,loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json[o]",
                        "-map", "[o]", "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    if "inf" in str(m["input_i"]):                      # silent test audio: nothing to normalise
        ln = "anull"
    dst = f"{film}/{out}"
    run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", graph + f";[mix]aformat=channel_layouts=stereo,{ln}[o]", "-map", "0:v", "-map", "[o]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-t", f"{total:.3f}", "-movflags", "+faststart", dst])
    # chapters for the description
    ch = [(t, it["chapter"]) for n, t, it in cues if it["first"]]
    if ch:
        ch[0] = (0.0, ch[0][1])
    open(f"{film}/chapters.txt", "w").write("".join(f"{int(t // 60)}:{int(t % 60):02d} {c}\n" for t, c in ch))
    print(f"done: {dst}  {total / 60:.1f} min, {len(want)} pictures")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["parse", "vo", "fake", "build"]); ap.add_argument("film")
    ap.add_argument("--only"); ap.add_argument("--voice", default="onwK4e9ZLuTAKqWW03F9"); ap.add_argument("--speed", type=float, default=0.9)
    ap.add_argument("--music"); ap.add_argument("--out", default="final.mp4"); ap.add_argument("--brand", default="Plain Tale English")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    if a.cmd == "parse": parse(a.film)
    elif a.cmd == "vo": vo(a.film, a.voice, a.only, a.speed)
    elif a.cmd == "fake": fake(a.film, a.only)
    else: build(a.film, a.only, a.music, a.out, a.brand, a.workers)
