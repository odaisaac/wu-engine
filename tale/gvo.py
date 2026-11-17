#!/usr/bin/env python3
"""Narration with Google's Gemini voices (the same voices as "Generate speech" in Google AI Studio).

  python tale/gvo.py FILM [--voice Charon] [--model gemini-3.8-flash-tts] [--pace "..."] [--only 1-12]

Needs a free API key from https://aistudio.google.com/apikey, saved as GEMINI_API_KEY in .env
(python setup.py asks for it) or set in your environment.

One request per paragraph, so caption timing is exact per paragraph and spread by length inside it.
The free tier has a small daily request limit. When it is reached the script stops cleanly:
run it again later (finished paragraphs are kept), or switch --model to the lite model, which has its own limit.

Voices (name: character): Charon informative, Kore firm, Orus firm, Iapetus clear, Algieba smooth,
Sadaltager knowledgeable, Gacrux mature, Schedar even, Sulafat warm, Achird friendly, Vindemiatrix gentle,
Achernar soft, Puck upbeat, Zephyr bright, Aoede breezy, Leda youthful, Despina smooth, Erinome clear,
Algenib gravelly, Rasalgethi informative, Alnilam firm, Enceladus breathy, Umbriel easy-going,
Callirrhoe easy-going, Zubenelgenubi casual, Autonoe bright, Laomedeia upbeat, Pulcherrima forward,
Sadachbia lively, Fenrir excitable.
"""
import argparse, base64, io, json, os, re, subprocess, sys, time, urllib.error, urllib.request, wave
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env
import tale
from kvo import trim

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
PACE = "Calm storyteller for English learners, speaking slowly and clearly, with short natural pauses between sentences."


def request(model, key, text, voice, pace, old_style):
    part = {"text": text}
    voice_cfg = {"prebuiltVoiceConfig": {"voiceName": voice}} if old_style else {"voice": voice}
    if not old_style:                               # older preview models have no speech_metadata; they just read the text
        part["speech_metadata"] = {"style": pace}
    body = {"contents": [{"role": "user", "parts": [part]}],
            "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": voice_cfg}}}
    req = urllib.request.Request(API.format(model=model), data=json.dumps(body).encode(),
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    res = json.load(urllib.request.urlopen(req, timeout=180))
    parts = res["candidates"][0]["content"]["parts"]
    data = next(p["inlineData"] for p in parts if "inlineData" in p)
    return base64.b64decode(data["data"]), data.get("mimeType", "")


def to_float(raw, mime):
    """WAV (with header) or raw 16-bit PCM at 24 kHz mono -> float32 array, sample rate."""
    if raw[:4] == b"RIFF":
        with wave.open(io.BytesIO(raw)) as w:
            sr, ch, frames = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
        x = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768
        return (x.reshape(-1, ch).mean(axis=1) if ch > 1 else x), sr
    m = re.search(r"rate=(\d+)", mime or "")
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768, int(m.group(1)) if m else 24000


def main():
    env.load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("film")
    ap.add_argument("--voice", default=os.environ.get("T2F_GEMINI_VOICE") or "Charon")
    ap.add_argument("--model", default=os.environ.get("T2F_GEMINI_TTS_MODEL") or "gemini-3.8-flash-tts")
    ap.add_argument("--pace", default=PACE, help="how the voice should read (style only, it is not spoken)")
    ap.add_argument("--only")
    a = ap.parse_args()
    key = env.key("GEMINI_API_KEY")
    if not key:
        sys.exit("No GEMINI_API_KEY. Get a free key at https://aistudio.google.com/apikey and run: python setup.py --keys")
    old_style = "preview" in a.model and ("2.5" in a.model or "3.1" in a.model)
    items = tale.load(a.film)["items"]; want = tale.pick(a.only, len(items))
    os.makedirs(f"{a.film}/vo", exist_ok=True)
    made = 0
    for it in items:
        n = it["i"]; mp3, js = f"{a.film}/vo/{n:03d}.mp3", f"{a.film}/vo/{n:03d}.json"
        if n not in want or (os.path.exists(mp3) and os.path.exists(js)):
            continue
        text = it["text"]
        for attempt in range(4):
            try:
                raw, mime = request(a.model, key, text, a.voice, a.pace, old_style); break
            except urllib.error.HTTPError as e:
                msg = e.read().decode(errors="replace")[:400]
                if e.code == 429:
                    if "PerDay" in msg or "per day" in msg.lower() or attempt == 3:
                        sys.exit(f"\nDaily limit reached after {made} paragraphs. Finished ones are kept.\n"
                                 f"Run the same command again tomorrow, or try --model gemini-3.8-flash-lite-tts.\n{msg}")
                    time.sleep(30 * (attempt + 1)); continue          # per-minute limit: wait and retry
                if e.code in (500, 502, 503) and attempt < 3:
                    time.sleep(10); continue
                sys.exit(f"paragraph {n}: Google said {e.code}: {msg}")
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt == 3: sys.exit(f"paragraph {n}: network problem: {e}")
                time.sleep(10)
        x, sr = to_float(raw, mime)
        y = trim(x, sr)
        d = len(y) / sr
        p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-", "-ar", "44100", "-b:a", "160k", mp3],
                           input=y.astype(np.float32).tobytes())
        if p.returncode:
            sys.exit(f"could not write {mp3}")
        L = max(1, len(text))
        json.dump({"engine": "gemini", "chars": list(text), "starts": [round(d * i / L, 3) for i in range(L)],
                   "ends": [round(d * (i + 1) / L, 3) for i in range(L)]}, open(js, "w"))
        made += 1
        print(f"{n:03d} {d:.1f}s", flush=True)
    print(f"done: {made} paragraphs narrated with {a.voice}")


if __name__ == "__main__":
    main()
