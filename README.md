# wu-engine — The World Unpacked documentary engine

Topic → finished YouTube documentary. See the `world-unpacked-documentary` skill for the full workflow.

```
cd video && npm ci
ELEVEN_KEY=... python3 tools/vo.py FILM
python3 tools/timing.py FILM
PIXABAY_KEY=... COVERR_KEY=... python3 tools/stock.py FILM
python3 tools/mix.py FILM music.mp3 --bed -31
tools/render.sh FILM 4
```
Keys are passed as environment variables only — never commit them.
