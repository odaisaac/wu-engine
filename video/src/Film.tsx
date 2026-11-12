import React from "react";
import { AbsoluteFill, Easing, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { F, DS } from "./theme";
import { STYLE } from "./styles";
import { THEMES, ThemeCtx, Theme } from "./themes";
import { Bg, Logo, KText, Tag, clamp, useSpr, IO, mix, Deco, Cam } from "./motion";
import { OverlayView, Overlay } from "./Overlays";
import { SubMid, EndCard, SubNudge } from "./Subscribe";
import { Mover, TransFX, MBDefs } from "./transitions";
import spec from "./spec.json";
import timing from "./timing.json";

type Shot = { id: string; text?: string; kind?: "footage" | "photo" | "graphic" | "subscribe" | "endcard" | "intro"; overlay?: Overlay; look?: string; act?: { label: string; title: string }; source?: string; transition?: "fade" | "bar" | "iris" | "rise" | "split"; title?: string; then?: Beat[]; nudge?: boolean };
/** An overlay beat: starts at sentence "cue" (0-based) or when the word "on" is spoken. */
type Beat = Overlay & { cue?: number; on?: string };
type Word = [string, number, number];
const SHOTS = (spec as { shots: Shot[] }).shots;
/** true inside the vertical Short: footage overlays are hidden (the Short draws its own big captions). */
export const ShortMode = React.createContext(false);
const LOOKS = STYLE.looks;
const FOOT: Theme = { ...THEMES.night, amber: STYLE.accent, fg: "#FFFFFF", dim: "#D5DCE6", panel: "#0A0D14B3", line: "#FFFFFF33" };
const lookOf = (s: Shot, i: number) => THEMES[s.look ?? LOOKS[i % LOOKS.length]] ?? THEMES.night;
const bgOf = (s: Shot | undefined, i: number) => !s ? "#0A0D14" : s.kind === "footage" || s.kind === "photo" ? "#0A0D14" : s.kind === "subscribe" ? THEMES.sun.bg : s.kind === "endcard" ? (THEMES[STYLE.endcard] ?? THEMES.night).bg : s.kind === "intro" ? (THEMES[STYLE.intro] ?? THEMES.night).bg : lookOf(s, i).bg;

const ghostOf = (o?: Overlay): string | undefined => {
  if (!o) return undefined;
  const n = (v: number, p = "", x = "") => `${p}${v >= 10000 ? Math.round(v / 1000) + "K" : v}${x}`;
  switch (o.type) {
    case "stat": return n(o.value, o.prefix, o.suffix);
    case "compare": case "bars": return undefined; // full-width layouts: a ghost would fight the data
    case "list": return String(o.items.length).padStart(2, "0");
    case "quote": return "\u201C";
    case "kinetic": return (o.hl?.[0] ?? o.text.split(" ")[0]).toUpperCase();
    default: return undefined;
  }
};

/** Frame (shot-local) at which each narration sentence starts: exact when word timings exist, else by text position. */
export const sentenceCues = (text: string | undefined, dur: number, words?: Word[]): number[] => {
  const ws = (text ?? "").split(/\s+/).filter(Boolean);
  if (!ws.length) return [0];
  const starts = [0];
  ws.forEach((w, i) => { if (/[.!?]["')\]]?$/.test(w) && i < ws.length - 1) starts.push(i + 1); });
  if (words && words.length === ws.length) return starts.map((i) => words[i][1]);
  const pos: number[] = []; let acc = 0; ws.forEach((w) => { pos.push(acc); acc += w.length + 1; });
  return starts.map((i) => Math.round((pos[i] / acc) * Math.max(1, dur - 18)));
};
/** Frame at which a given word is spoken ("on": "thirty-nine" → first word starting with it), or undefined. */
export const wordFrame = (needle: string, text: string | undefined, dur: number, words?: Word[]): number | undefined => {
  const ws = (text ?? "").split(/\s+/).filter(Boolean);
  const norm = (x: string) => x.toLowerCase().replace(/[^a-z0-9]/g, "");
  const i = ws.findIndex((w) => norm(w).startsWith(norm(needle)));
  if (i < 0) return undefined;
  if (words && words.length === ws.length) return words[i][1];
  let acc = 0; const pos = ws.map((w) => { const p = acc; acc += w.length + 1; return p; });
  return Math.round((pos[i] / acc) * Math.max(1, dur - 18));
};
/** Where each overlay beat of a shot begins. A beat starts at its explicit frame ("on" word or "cue" sentence),
 *  otherwise beats spread over the sentence starts; mirrored in tools/cues.py. */
export const beatBounds = (n: number, cues: number[], dur: number, explicit: (number | undefined)[] = []): number[] => {
  const b = [0]; const m = cues.length;
  for (let k = 1; k < n; k++) {
    const ci = m >= n ? Math.round((k * m) / n) : -1;
    let fr = explicit[k] !== undefined ? (explicit[k] as number) - 3 : ci >= 0 && ci < m ? cues[ci] - 3 : Math.round((k * dur) / n);
    fr = Math.min(Math.max(fr, b[k - 1] + 24), dur - 24);
    b.push(fr);
  }
  b.push(dur);
  return b;
};
type Cue = { sent: number[]; word: (needle: string) => number | undefined };
const CueCtx = React.createContext<Cue>({ sent: [0], word: () => undefined });
const wordsOf = (t: unknown) => (t as { words?: Word[] }).words;

/** A shot's overlays in sequence: the main overlay, then each "then" beat, cut on the narration. */
const Beats: React.FC<{ s: Shot; dur: number; onFootage: boolean; i: number }> = ({ s, dur, onFootage, i }) => {
  const f = useCurrentFrame();
  const cue = React.useContext(CueCtx);
  const list = [s.overlay, ...(s.then ?? [])].filter(Boolean) as Beat[];
  if (!list.length) return null;
  const b = beatBounds(list.length, cue.sent, dur, list.map((o) => (o.on ? cue.word(o.on) : o.cue !== undefined ? cue.sent[o.cue] : undefined)));
  let k = 0; for (let j = 0; j < list.length; j++) if (f >= b[j]) k = j;
  const local = f - b[k];
  const punch = k > 0 ? 1 + 0.035 * (1 - OUTQ(clamp(local / 9))) : 1;
  const flash = k > 0 ? 0.22 * (1 - clamp(local / 5)) : 0;
  return (
    <>
      {list.map((o, j) => (
        <Sequence key={j} from={b[j]} durationInFrames={Math.max(1, b[j + 1] - b[j])} layout="none">
          <AbsoluteFill style={{ transform: j === k ? `scale(${punch})` : undefined }}>
            {!onFootage ? <Deco ghost={ghostOf(o)} dur={b[j + 1] - b[j]} seed={i + j} /> : null}
            <OverlayView o={o} dur={b[j + 1] - b[j]} onFootage={onFootage} />
          </AbsoluteFill>
        </Sequence>
      ))}
      {flash > 0 ? <AbsoluteFill style={{ background: STYLE.accent, opacity: flash, mixBlendMode: "screen", pointerEvents: "none" }} /> : null}
    </>
  );
};
const OUTQ = Easing.out(Easing.cubic);

const Footage: React.FC<{ s: Shot; dur: number; i: number }> = ({ s, dur, i }) => {
  const f = useCurrentFrame();
  const t = IO(clamp(f / dur));
  const isPhoto = s.kind === "photo";
  const z = isPhoto ? mix(1.06, 1.18, t) : mix(1.0, 1.06, t);
  const dx = isPhoto ? mix(i % 2 ? -30 : 30, i % 2 ? 30 : -30, t) : 0;
  const heavy = [s.overlay, ...(s.then ?? [])].some((o) => o && o.type !== "lower" && o.type !== "none");
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <AbsoluteFill style={{ transform: `scale(${z}) translateX(${dx}px)`, filter: STYLE.grade }}>
        {isPhoto ? <Img src={staticFile(`film/stock/${s.id}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          : <OffthreadVideo src={staticFile(`film/stock/${s.id}.mp4`)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />}
      </AbsoluteFill>
      {STYLE.tint ? <AbsoluteFill style={{ background: STYLE.tint, mixBlendMode: "soft-light", opacity: 0.55 }} /> : null}
      <AbsoluteFill style={{ background: heavy ? "linear-gradient(90deg, #05070CC4 0%, #05070C8C 38%, #05070C1F 72%, transparent 100%)" : "linear-gradient(0deg, #05070C99 0%, transparent 35%)" }} />
      <ThemeCtx.Provider value={FOOT}>{s.overlay && !React.useContext(ShortMode) ? <Beats s={s} dur={dur} onFootage i={i} /> : null}</ThemeCtx.Provider>
    </AbsoluteFill>
  );
};


const Graphic: React.FC<{ s: Shot; dur: number; i: number }> = ({ s, dur, i }) => (
  <ThemeCtx.Provider value={lookOf(s, i)}>
    <AbsoluteFill><Bg seed={i} /><Cam dur={dur} z={[1, 1.035]}><Beats s={s} dur={dur} onFootage={false} i={i} /></Cam></AbsoluteFill>
  </ThemeCtx.Provider>
);

const Intro: React.FC<{ s: Shot; dur: number }> = ({ s, dur }) => {
  const lg = useSpr(4, { damping: 11, stiffness: 90 });
  const ov = s.overlay as any;
  return (
    <ThemeCtx.Provider value={THEMES[STYLE.intro] ?? THEMES.night}>
      <AbsoluteFill><Bg seed={7} />
        <div style={{ position: "absolute", left: 220, top: 300, transform: `scale(${0.3 + 0.7 * lg}) rotate(${(1 - lg) * -40}deg)`, opacity: clamp(lg * 2) }}><Logo size={440} /></div>
        <div style={{ position: "absolute", left: 800, top: 300, width: 1000 }}>
          <Tag at={26} color={STYLE.accent}>{ov?.tag ?? "The World Unpacked"}</Tag>
          <div style={{ height: 24 }} />
          <KText words={(ov?.text ?? "").split(" ").map((w: string) => [w, (ov?.hl ?? []).includes(w.replace(/[^\w]/g, "")) ? STYLE.accent : undefined])} size={100 * (STYLE.displayUpper ? 1 : 0.92)} at={32} font="serif" weight={800} stagger={4} />
        </div>
      </AbsoluteFill>
    </ThemeCtx.Provider>
  );
};

const capCss = (): React.CSSProperties => {
  const base: React.CSSProperties = { fontFamily: STYLE.name === "tech" ? F.mono : F.sans, fontWeight: 600, fontSize: 46, lineHeight: 1.3, color: STYLE.captionFg };
  switch (STYLE.caption) {
    case "shadow": return { ...base, fontWeight: 700, fontSize: 48, textShadow: "0 2px 6px #000, 0 0 22px #000C", background: "rgba(8,6,6,0.5)", padding: "6px 22px", borderRadius: 6 }; // soft backing keeps it readable on light scenes
    case "highlight": return { ...base, fontWeight: 800, fontSize: 48, background: STYLE.captionBg, padding: "4px 16px", boxDecorationBreak: "clone", WebkitBoxDecorationBreak: "clone", lineHeight: 1.5 };
    case "pill": return { ...base, fontWeight: 600, background: STYLE.captionBg, padding: "10px 30px", borderRadius: 999, boxShadow: "0 8px 24px #0004" };
    case "edge": return { ...base, fontWeight: 600, fontSize: 42, background: STYLE.captionBg, padding: "10px 24px", borderLeft: `6px solid ${STYLE.accent}`, borderRadius: 4 };
    case "bar": return { ...base, background: STYLE.captionBg, borderTop: `5px solid ${STYLE.accent}`, padding: "14px 160px 18px", fontSize: 44 };
    default: return { ...base, background: STYLE.captionBg, padding: "8px 22px", borderRadius: 10 };
  }
};

/** Split narration into readable caption chunks: break on sentence/clause ends, ~3–7 words, never a 1–2 word orphan. */
export const chunkText = (text: string): string[] => {
  const words = text.split(/\s+/).filter(Boolean);
  const out: string[][] = []; let cur: string[] = [];
  words.forEach((w, i) => {
    cur.push(w);
    const end = /[.!?]$/.test(w), clause = /[,;:—]$/.test(w);
    const left = words.length - i - 1;
    const weak = /^(a|an|the|to|of|and|or|in|on|for|with|at|by|from|that|their|his|her|its|is|was|it)$/i.test(w.replace(/[^\w]/g, ""));
    if ((end && cur.length >= 3) || (clause && cur.length >= 4) || (cur.length >= 7 && !weak) || cur.length >= 9) {
      if (left > 0 && left <= 2) return; // keep the tail with this chunk
      out.push(cur); cur = [];
    }
  });
  if (cur.length) { if (cur.length <= 2 && out.length) out[out.length - 1].push(...cur); else out.push(cur); }
  return out.map((c) => c.join(" "));
};

/** Chunks with word ranges, so exact word timings (tools/words.py) can drive them. */
export const chunkWords = (text: string): number[][] => {
  const chunks = chunkText(text); let k = 0;
  return chunks.map((c) => { const n = c.split(/\s+/).length; const r = [k, k + n]; k += n; return r; });
};
const WORD_HL = (spec as { captionWords?: boolean }).captionWords === true;

const Caption: React.FC<{ text: string; dur: number; words?: Word[] }> = ({ text, dur, words }) => {
  const f = useCurrentFrame();
  const chunks = React.useMemo(() => chunkText(text), [text]);
  const ranges = React.useMemo(() => chunkWords(text), [text]);
  let idx = chunks.length - 1, local = 0;
  if (words && words.length === text.split(/\s+/).filter(Boolean).length) {
    // exact timing: a chunk appears when its first word is spoken (2 frames early)
    idx = 0;
    for (let i = 0; i < ranges.length; i++) if (f >= words[ranges[i][0]][1] - 2) idx = i;
    local = f - (words[ranges[idx][0]][1] - 2);
  } else {
    const weights = chunks.map((c) => c.length + 12);
    const total = weights.reduce((a, b) => a + b, 0);
    const speak = Math.max(1, dur - 18); // vo ends ~0.6s before the shot does
    let acc = 0;
    for (let i = 0; i < chunks.length; i++) { const len = (weights[i] / total) * speak; if (f < acc + len) { idx = i; local = f - acc; break; } acc += len; }
  }
  const fade = clamp(f / 6) * (1 - clamp((f - (dur - 6)) / 6));
  const pop = idx === 0 ? 1 : clamp(local / 4);
  const ws = chunks[idx].split(/\s+/);
  return (
    <div style={{ position: "absolute", left: STYLE.caption === "bar" ? 0 : 160, right: STYLE.caption === "bar" ? 0 : 160, bottom: STYLE.caption === "bar" ? 0 : 50, textAlign: "center", opacity: fade }}>
      <span style={{ ...capCss(), display: STYLE.caption === "bar" ? "block" : "inline", opacity: 0.4 + 0.6 * pop }}>
        {WORD_HL && words ? ws.map((w, j) => { const W = words[ranges[idx][0] + j]; const on = W && f >= W[1] - 1; return <span key={j} style={{ color: on ? STYLE.captionFg : `${STYLE.captionFg}88`, transition: "none" }}>{w}{j < ws.length - 1 ? " " : ""}</span>; }) : chunks[idx]}
      </span>
    </div>
  );
};

const ActTag: React.FC<{ label: string; title: string }> = ({ label, title }) => {
  const f = useCurrentFrame();
  const t = clamp((f - 14) / 16) * (1 - clamp((f - 100) / 16));
  return (
    <div style={{ position: "absolute", right: 70, top: 46, textAlign: "right", opacity: t, transform: `translateX(${(1 - t) * 40}px)`, background: "#0A0D14E6", padding: "14px 26px", borderRadius: 16 }}>
      <div style={{ fontFamily: F.sans, fontWeight: 800, fontSize: 22, letterSpacing: "0.3em", color: STYLE.accent, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontFamily: F.serif, fontStyle: STYLE.displayItalicOk ? "italic" : "normal", fontWeight: 600, fontSize: 40 * DS, textTransform: STYLE.displayUpper ? "uppercase" : undefined, color: "#F4ECDD" }}>{title}</div>
    </div>
  );
};

const SourceTag: React.FC<{ text: string }> = ({ text }) => (
  <div style={{ position: "absolute", left: 90, top: 50, background: "#0A0D14B3", padding: "8px 16px", borderRadius: 10, fontFamily: F.mono, fontWeight: 700, fontSize: 20, letterSpacing: STYLE.mono ? "0.08em" : "0.16em", textTransform: "uppercase", color: "#D5DCE6" }}>{text}</div>
);

const Finish: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <>
      <AbsoluteFill style={{ backgroundImage: `url(${staticFile("grain.png")})`, backgroundSize: "512px 512px", backgroundPosition: `${(f * 37) % 512}px ${(f * 91) % 512}px`, opacity: STYLE.grain, mixBlendMode: "overlay" }} />
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, transparent 58%, rgba(0,0,0,${STYLE.vignette}) 100%)` }} />
    </>
  );
};

/** Act tags are planning structure only — never shown on screen unless a spec explicitly sets "showActs": true. */
const SHOW_ACTS = (spec as { showActs?: boolean }).showActs === true;
const BG = (j: number) => bgOf(SHOTS[j], j);

export const FilmBody: React.FC<{ captions?: boolean }> = ({ captions = true }) => (
  <AbsoluteFill style={{ background: "#000" }}>
    <MBDefs />
    {timing.shots.map((t, i) => {
      const s = SHOTS[i];
      const k = s.kind ?? "graphic";
      return (
        <Sequence key={s.id} from={t.start} durationInFrames={t.dur} premountFor={30}>
          <CueCtx.Provider value={{ sent: sentenceCues(s.text, t.dur, wordsOf(t)), word: (n) => wordFrame(n, s.text, t.dur, wordsOf(t)) }}>
          <Mover i={i} dur={t.dur} shots={SHOTS} bg={BG}>
            {k === "footage" || k === "photo" ? <Footage s={s} dur={t.dur} i={i} /> : k === "subscribe" ? <SubMid dur={t.dur} /> : k === "endcard" ? <EndCard dur={t.dur} /> : k === "intro" ? <Intro s={s} dur={t.dur} /> : <Graphic s={s} dur={t.dur} i={i} />}
            {s.act && SHOW_ACTS ? <ActTag label={s.act.label} title={s.act.title} /> : null}
            {s.source ? <SourceTag text={s.source} /> : null}
          </Mover>
          </CueCtx.Provider>
          <TransFX i={i} dur={t.dur} shots={SHOTS} bg={BG} />
          {s.nudge && captions ? <SubNudge /> : null}
          {captions && s.text && k !== "endcard" && k !== "subscribe" ? <Caption text={s.text} dur={t.dur} words={wordsOf(t)} /> : null}
        </Sequence>
      );
    })}
    <Finish />
  </AbsoluteFill>
);
export const Film: React.FC = () => <FilmBody />;
export const TOTAL = timing.total;
export const SHOT_LIST = SHOTS;
