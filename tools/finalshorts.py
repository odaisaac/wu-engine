#!/usr/bin/env python3
"""Vertical Shorts (1080x1920) cut straight from a finished film's final.mp4, for films whose stock
clips are no longer on disk. The 16:9 picture (with its own captions) sits in the middle on a blurred
copy of itself, with a big hook at the top and a closing line at the end.

  python3 tools/finalshorts.py FILM NAME --shots 12,12b,13b --hook "Is the ground under your home sinking?"
        [--end "Full documentary on the channel ▶"]

Output: FILM/shorts/NAME.mp4 at -14 LUFS. Shot ids come from FILM/timing.json (consecutive shots are
joined into one cut).
"""
import argparse, json, os, subprocess

FPS = 30
FONTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tale", "fonts")


def ass_time(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("film"); ap.add_argument("name")
    ap.add_argument("--shots", required=True); ap.add_argument("--hook", required=True)
    ap.add_argument("--end", default="Full documentary on the channel ▶")
    a = ap.parse_args()
    T = {s["id"]: s for s in json.load(open(f"{a.film}/timing.json"))["shots"]}
    ids = a.shots.split(",")
    segs = []
    for i in ids:
        s0, s1 = T[i]["start"] / FPS, (T[i]["start"] + T[i]["dur"]) / FPS
        if segs and abs(segs[-1][1] - s0) < 0.05:
            segs[-1][1] = s1
        else:
            segs.append([s0, s1])
    total = sum(b - a_ for a_, b in segs)
    os.makedirs(f"{a.film}/shorts", exist_ok=True)
    out = f"{a.film}/shorts/{a.name}.mp4"
    ass = out.replace(".mp4", ".ass")
    words = a.hook.upper().split(); hl = " ".join(words[-2:]); body = " ".join(words[:-2])
    hook = (body + " " if body else "") + "{\\c&H3DC8FF&}" + hl
    open(ass, "w", encoding="utf-8").write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Anton,104,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,0,0,1,6,4,8,70,70,330,1
Style: End,Inter,46,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,1,0,0,0,100,100,0,0,3,10,0,2,60,60,520,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,{ass_time(total)},Hook,,0,0,0,,{{\\fad(200,0)}}{hook}
Dialogue: 1,{ass_time(max(0, total - 3.2))},{ass_time(total)},End,,0,0,0,,{{\\fad(250,0)\\3c&H2B20C8&}}{a.end}
""")
    parts = "".join(f"[0:v]trim={s:.3f}:{e:.3f},setpts=PTS-STARTPTS[v{k}];[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS[a{k}];"
                    for k, (s, e) in enumerate(segs))
    cat = "".join(f"[v{k}][a{k}]" for k in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=1[cv][ca];"
    esc = ass.replace("\\", "/").replace(":", "\\:"); fd = FONTS.replace(":", "\\:")
    fc = (parts + cat +
          "[cv]split[bg][fg];[bg]scale=-2:1920,crop=1080:1920,boxblur=30:2,eq=brightness=-0.25[b];"
          "[fg]scale=1080:-2[f];[b][f]overlay=0:(H-h)/2,"
          f"subtitles='{esc}':fontsdir='{fd}',format=yuv420p[v];"
          "[ca]loudnorm=I=-14:TP=-1.5:LRA=11,aformat=channel_layouts=stereo[a]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{a.film}/final.mp4", "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                    "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", out], check=True)
    os.remove(ass)
    print(f"{out}  {total:.0f}s  {a.hook}")


if __name__ == "__main__":
    main()
