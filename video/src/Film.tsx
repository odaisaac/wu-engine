import React from "react";
import { AbsoluteFill, Easing, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { F, DS } from "./theme";
import { STYLE } from "./styles";
import { THEMES, ThemeCtx, Theme } from "./themes";
import { Bg, Logo, KText, Tag, clamp, useSpr, IO, mix, Deco } from "./motion";
import { OverlayView, Overlay } from "./Overlays";
import { SubMid, EndCard } from "./Subscribe";
import { Mover, TransFX, MBDefs } from "./transitions";
import spec from "./spec.json";
import timing from "./timing.json";

type Shot = { id: string; text?: string; kind?: "footage" | "photo" | "graphic" | "subscribe" | "endcard" | "intro"; overlay?: Overlay; look?: string; act?: { label: string; title: string }; source?: string; transition?: "fade" | "bar" | "iris" | "rise" | "split"; title?: string };
const SHOTS = (spec as { shots: Shot[] }).shots;
const LOOKS = STYLE.looks;
const FOOT: Theme = { ...THEMES.night, amber: STYLE.accent, fg: "#FFFFFF", dim: "#D5DCE6", panel: "#0A0D14B3", line: "#FFFFFF33" };
const lookOf = (s: Shot, i: number) => THEMES[s.look ?? LOOKS[i % LOOKS.length]] ?? THEMES.night;
const bgOf = (s: Shot | undefined, i: number) => !s ? "#0A0D14" : s.kind === "footage" || s.kind === "photo" ? "#0A0D14" : s.kind === "subscribe" ? THEMES.sun.bg : s.kind === "endcard" ? (THEMES[STYLE.endcard] ?? THEMES.night).bg : s.kind === "intro" ? (THEMES[STYLE.intro] ?? THEMES.night).bg : lookOf(s, i).bg;

const Footage: React.FC<{ s: Shot; dur: number; i: number }> = ({ s, dur, i }) => {
  const f = useCurrentFrame();
  const t = IO(clamp(f / dur));
  const isPhoto = s.kind === "photo";
  const z = isPhoto ? mix(1.06, 1.18, t) : mix(1.0, 1.06, t);
  const dx = isPhoto ? mix(i % 2 ? -30 : 30, i % 2 ? 30 : -30, t) : 0;
  const heavy = s.overlay && s.overlay.type !== "lower" && s.overlay.type !== "none";
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <AbsoluteFill style={{ transform: `scale(${z}) translateX(${dx}px)`, filter: STYLE.grade }}>
        {isPhoto ? <Img src={staticFile(`film/stock/${s.id}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          : <OffthreadVideo src={staticFile(`film/stock/${s.id}.mp4`)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />}
      </AbsoluteFill>
      {STYLE.tint ? <AbsoluteFill style={{ background: STYLE.tint, mixBlendMode: "soft-light", opacity: 0.55 }} /> : null}
      <AbsoluteFill style={{ background: heavy ? "linear-gradient(90deg, #05070CE6 0%, #05070CB3 40%, #05070C33 75%, #05070C1A 100%)" : "linear-gradient(0deg, #05070C99 0%, transparent 35%)" }} />
      <ThemeCtx.Provider value={FOOT}>{s.overlay ? <OverlayView o={s.overlay} dur={dur} onFootage /> : null}</ThemeCtx.Provider>
    </AbsoluteFill>
  );
};

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

const Graphic: React.FC<{ s: Shot; dur: number; i: number }> = ({ s, dur, i }) => (
  <ThemeCtx.Provider value={lookOf(s, i)}>
    <AbsoluteFill><Bg seed={i} /><Deco ghost={ghostOf(s.overlay)} dur={dur} seed={i} />{s.overlay ? <OverlayView o={s.overlay} dur={dur} onFootage={false} /> : null}</AbsoluteFill>
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
  const base: React.CSSProperties = { fontFamily: STYLE.name === "tech" ? F.mono : F.sans, fontWeight: 600, fontSize: 38, lineHeight: 1.35, color: STYLE.captionFg };
  switch (STYLE.caption) {
    case "shadow": return { ...base, fontWeight: 600, fontSize: 40, textShadow: "0 2px 6px #000, 0 0 22px #000C" };
    case "highlight": return { ...base, fontWeight: 800, fontSize: 40, background: STYLE.captionBg, padding: "4px 16px", boxDecorationBreak: "clone", WebkitBoxDecorationBreak: "clone", lineHeight: 1.5 };
    case "pill": return { ...base, fontWeight: 600, background: STYLE.captionBg, padding: "10px 30px", borderRadius: 999, boxShadow: "0 8px 24px #0004" };
    case "edge": return { ...base, fontWeight: 500, fontSize: 34, background: STYLE.captionBg, padding: "10px 24px", borderLeft: `6px solid ${STYLE.accent}`, borderRadius: 4 };
    case "bar": return { ...base, background: STYLE.captionBg, borderTop: `5px solid ${STYLE.accent}`, padding: "14px 160px 18px", fontSize: 36 };
    default: return { ...base, background: STYLE.captionBg, padding: "8px 22px", borderRadius: 10 };
  }
};

/** Split narration into readable caption chunks: break on sentence/clause ends, ~4–9 words, never a 1–2 word orphan. */
export const chunkText = (text: string): string[] => {
  const words = text.split(/\s+/).filter(Boolean);
  const out: string[][] = []; let cur: string[] = [];
  words.forEach((w, i) => {
    cur.push(w);
    const end = /[.!?]$/.test(w), clause = /[,;:—]$/.test(w);
    const left = words.length - i - 1;
    const weak = /^(a|an|the|to|of|and|or|in|on|for|with|at|by|from|that|their|his|her|its|is|was|it)$/i.test(w.replace(/[^\w]/g, ""));
    if ((end && cur.length >= 3) || (clause && cur.length >= 5) || (cur.length >= 9 && !weak) || cur.length >= 12) {
      if (left > 0 && left <= 2) return; // keep the tail with this chunk
      out.push(cur); cur = [];
    }
  });
  if (cur.length) { if (cur.length <= 2 && out.length) out[out.length - 1].push(...cur); else out.push(cur); }
  return out.map((c) => c.join(" "));
};

const Caption: React.FC<{ text: string; dur: number }> = ({ text, dur }) => {
  const f = useCurrentFrame();
  const chunks = React.useMemo(() => chunkText(text), [text]);
  const weights = chunks.map((c) => c.length + 12);
  const total = weights.reduce((a, b) => a + b, 0);
  const speak = Math.max(1, dur - 18); // vo ends ~0.6s before the shot does
  let acc = 0, idx = chunks.length - 1, local = 0;
  for (let i = 0; i < chunks.length; i++) { const len = (weights[i] / total) * speak; if (f < acc + len) { idx = i; local = f - acc; break; } acc += len; }
  const fade = clamp(f / 6) * (1 - clamp((f - (dur - 6)) / 6));
  const pop = idx === 0 ? 1 : clamp(local / 4);
  return (
    <div style={{ position: "absolute", left: STYLE.caption === "bar" ? 0 : 160, right: STYLE.caption === "bar" ? 0 : 160, bottom: STYLE.caption === "bar" ? 0 : 50, textAlign: "center", opacity: fade }}>
      <span style={{ ...capCss(), display: STYLE.caption === "bar" ? "block" : "inline", opacity: 0.4 + 0.6 * pop }}>{chunks[idx]}</span>
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

const BG = (j: number) => bgOf(SHOTS[j], j);

export const Film: React.FC = () => (
  <AbsoluteFill style={{ background: "#000" }}>
    <MBDefs />
    {timing.shots.map((t, i) => {
      const s = SHOTS[i];
      const k = s.kind ?? "graphic";
      return (
        <Sequence key={s.id} from={t.start} durationInFrames={t.dur} premountFor={30}>
          <Mover i={i} dur={t.dur} shots={SHOTS} bg={BG}>
            {k === "footage" || k === "photo" ? <Footage s={s} dur={t.dur} i={i} /> : k === "subscribe" ? <SubMid dur={t.dur} /> : k === "endcard" ? <EndCard dur={t.dur} /> : k === "intro" ? <Intro s={s} dur={t.dur} /> : <Graphic s={s} dur={t.dur} i={i} />}
            {s.act ? <ActTag label={s.act.label} title={s.act.title} /> : null}
            {s.source ? <SourceTag text={s.source} /> : null}
          </Mover>
          <TransFX i={i} dur={t.dur} shots={SHOTS} bg={BG} />
          {s.text && k !== "endcard" && k !== "subscribe" ? <Caption text={s.text} dur={t.dur} /> : null}
        </Sequence>
      );
    })}
    <Finish />
  </AbsoluteFill>
);
export const TOTAL = timing.total;
