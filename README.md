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

## Style presets
Set `"style"` in spec.json (or `--props='{"style":"noir"}'`). Leave shot `look` fields out so the style's palette rotation applies.

| key | name | best for |
|---|---|---|
| editorial | Editorial | general documentaries, society, housing, work |
| noir | Documentary Noir | true crime, scams, mysteries, investigations |
| bold | Bold Explainer | top-10 lists, fast explainers, shorts |
| tech | Tech Signal | AI, tech, internet, cyber, future of work |
| warm | Warm Stories | human stories, culture, history, travel |
| news | News Desk | current affairs, politics explainers, economy |
| finance | Money Matters | money, markets, salaries, cost of living |
| cosmic | Cinematic Future | space, science, climate, big-picture futures |

Each preset sets display + body fonts, palette rotation, intro/end themes, accent, transitions, caption style, footage grade/tint, grain, vignette and a music mood. Defined in `video/src/styles.ts`; preview sheet: `style-presets.jpg`.

## Retention rules (built in since Nov 2026)
Measured against small-channel breakout documentaries, our films changed picture every ~10 s; theirs change every 3–5 s. The engine now enforces that:
- **Cuts:** footage shots cut every ~4.5 s (`"cutEvery"` in spec.json). `stock.py` / `match.py` take one clip per ~4.5 s and re-use a clip with a punch-in when there are too few.
- **Overlay beats:** any shot can carry `"then": [overlay, …]`. The overlays play in turn, cut on the narration's sentence starts (or an explicit `"cue": sentenceIndex`), with a small punch and flash. Use them so no graphic sits still for more than ~8 s.
- **Cold open:** no logo card and no "This is The World Unpacked" line. Show the title as `{"type": "title"}` on an early footage shot (usually as a `then` beat).
- **Subscribe:** `"nudge": true` on a story shot plays a corner subscribe prompt over the film; the full-screen `subscribe` kind is kept only for old films.
- **Narration:** `vo.py` sends the neighbouring shots' text with each request, so short shots still read as one take.
- **Plan check:** `plancheck.py` scores hook, title, pace (seconds per picture), re-hooks every 75 s, viewer stakes ("you"), sentence length, length target (`"targetMin"`, default 11), subscribe nudge and the end card.

## Packaging
- `tools/pack.py FILM` builds `youtube-pack.md` and `captions.srt` from `FILM/pack.json` plus the film itself (chapters, end-screen time and footage credits are computed) and checks every YouTube limit.
- `ThumbBig` (Remotion still): subject one side, small lead-in, one giant word, pill, channel badge. `ThumbPop` and `ThumbHero` remain.
- `tools/thumbcheck.py FILM a.png b.png` shows each thumbnail at phone-feed and suggested-video size with the duration badge drawn in.
