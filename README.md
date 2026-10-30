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
