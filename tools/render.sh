#!/usr/bin/env bash
# Chunked render + audio mux. Usage: render.sh FILM_DIR [CHUNKS]
set -e
FILM=$(cd "$1" && pwd); N=${2:-4}; ENG=$(cd "$(dirname "$0")/.." && pwd); V=$ENG/video
cp "$FILM/spec.json" "$FILM/timing.json" "$V/src/"
rm -rf "$V/public/film"; mkdir -p "$V/public/film"; ln -sfn "$FILM/stock" "$V/public/film/stock"; ln -sfn "$FILM/vo" "$V/public/film/vo"
[ -d "$FILM/extra" ] && ln -sfn "$FILM/extra" "$V/public/film/extra"
cd "$V" && npx remotion bundle src/index.ts --out-dir="$FILM/bundle" >/dev/null 2>&1
T=$(python3 -c "import json;print(json.load(open('$FILM/timing.json'))['total'])"); S=$(( (T + N - 1) / N )); mkdir -p "$FILM/chunks"
for i in $(seq 0 $((N-1))); do a=$((i*S)); b=$(( (i+1)*S - 1 )); [ $b -ge $T ] && b=$((T-1)); [ -s "$FILM/chunks/c$i.mp4" ] && continue
  npx remotion render --browser-executable=/opt/google/chrome/chrome --serve-url="$FILM/bundle" Film "$FILM/chunks/c$i.mp4" --muted --frames=$a-$b --crf=21 --concurrency=2 --log=error; echo "chunk $i done $(date +%T)"; done
ls "$FILM"/chunks/c*.mp4 | sort -V | sed "s|^|file '|;s|$|'|" > "$FILM/chunks/list.txt"
ffmpeg -y -v error -f concat -safe 0 -i "$FILM/chunks/list.txt" -c copy "$FILM/silent.mp4"
ffmpeg -y -v error -i "$FILM/silent.mp4" -i "$FILM/mix.m4a" -map 0:v -map 1:a -c:v libx264 -preset medium -crf 24 -c:a copy -movflags +faststart -shortest "$FILM/final.mp4"
ls -la "$FILM/final.mp4"
