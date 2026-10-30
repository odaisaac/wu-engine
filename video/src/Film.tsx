import React from "react";
import { AbsoluteFill, Easing, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { F } from "./theme";
import { THEMES, ThemeCtx, Theme } from "./themes";
import { Bg, Logo, KText, Tag, clamp, useSpr, IO, mix } from "./motion";
import { OverlayView, Overlay } from "./Overlays";
import { SubMid, EndCard } from "./Subscribe";
import spec from "./spec.json";
import timing from "./timing.json";

type Shot = { id: string; text?: string; kind?: "footage" | "photo" | "graphic" | "subscribe" | "endcard" | "intro"; overlay?: Overlay; look?: string; act?: { label: string; title: string }; source?: string; transition?: "fade" | "bar" | "iris" | "rise" | "split"; title?: string };
const SHOTS = (spec as { shots: Shot[] }).shots;
const LOOKS = ["paper", "volt", "sun", "coral", "mint", "night"];
const FOOT: Theme = { ...THEMES.night, fg: "#FFFFFF", dim: "#D5DCE6", panel: "#0A0D14B3", line: "#FFFFFF33" };
const lookOf = (s: Shot, i: number) => THEMES[s.look ?? LOOKS[i % LOOKS.length]];
const bgOf = (s: Shot | undefined, i: number) => !s ? "#0A0D14" : s.kind === "footage" || s.kind === "photo" ? "#0A0D14" : s.kind === "subscribe" ? THEMES.sun.bg : s.kind === "endcard" || s.kind === "intro" ? THEMES.night.bg : lookOf(s, i).bg;

const Footage: React.FC<{ s: Shot; dur: number; i: number }> = ({ s, dur, i }) => {
  const f = useCurrentFrame();
  const t = IO(clamp(f / dur));
  const isPhoto = s.kind === "photo";
  const z = isPhoto ? mix(1.06, 1.18, t) : mix(1.0, 1.06, t);
  const dx = isPhoto ? mix(i % 2 ? -30 : 30, i % 2 ? 30 : -30, t) : 0;
  const heavy = s.overlay && s.overlay.type !== "lower" && s.overlay.type !== "none";
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <AbsoluteFill style={{ transform: `scale(${z}) translateX(${dx}px)` }}>
        {isPhoto ? <Img src={staticFile(`film/stock/${s.id}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          : <OffthreadVideo src={staticFile(`film/stock/${s.id}.mp4`)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />}
      </AbsoluteFill>
      <AbsoluteFill style={{ background: heavy ? "linear-gradient(90deg, #05070CE6 0%, #05070CB3 40%, #05070C33 75%, #05070C1A 100%)" : "linear-gradient(0deg, #05070C99 0%, transparent 35%)" }} />
      <ThemeCtx.Provider value={FOOT}>{s.overlay ? <OverlayView o={s.overlay} dur={dur} onFootage /> : null}</ThemeCtx.Provider>
    </AbsoluteFill>
  );
};

const Graphic: React.FC<{ s: Shot; dur: number; i: number }> = ({ s, dur, i }) => (
  <ThemeCtx.Provider value={lookOf(s, i)}>
    <AbsoluteFill><Bg seed={i} />{s.overlay ? <OverlayView o={s.overlay} dur={dur} onFootage={false} /> : null}</AbsoluteFill>
  </ThemeCtx.Provider>
);

const Intro: React.FC<{ s: Shot; dur: number }> = ({ s, dur }) => {
  const lg = useSpr(4, { damping: 11, stiffness: 90 });
  const ov = s.overlay as any;
  return (
    <ThemeCtx.Provider value={THEMES.night}>
      <AbsoluteFill><Bg seed={7} />
        <div style={{ position: "absolute", left: 220, top: 300, transform: `scale(${0.3 + 0.7 * lg}) rotate(${(1 - lg) * -40}deg)`, opacity: clamp(lg * 2) }}><Logo size={440} /></div>
        <div style={{ position: "absolute", left: 800, top: 300, width: 1000 }}>
          <Tag at={26} color="#FFB547">{ov?.tag ?? "The World Unpacked"}</Tag>
          <div style={{ height: 24 }} />
          <KText words={(ov?.text ?? "").split(" ").map((w: string) => [w, (ov?.hl ?? []).includes(w.replace(/[^\w]/g, "")) ? "#FFB547" : undefined])} size={100} at={32} font="sans" weight={900} stagger={4} />
        </div>
      </AbsoluteFill>
    </ThemeCtx.Provider>
  );
};

const Caption: React.FC<{ text: string; dur: number }> = ({ text, dur }) => {
  const f = useCurrentFrame();
  const w = text.split(" "); const per = 9; const chunks: string[] = [];
  for (let i = 0; i < w.length; i += per) chunks.push(w.slice(i, i + per).join(" "));
  const idx = Math.min(chunks.length - 1, Math.floor((f / Math.max(1, dur - 14)) * chunks.length));
  const fade = clamp(f / 8) * (1 - clamp((f - (dur - 8)) / 8));
  return (
    <div style={{ position: "absolute", left: 140, right: 140, bottom: 46, textAlign: "center", opacity: fade }}>
      <span style={{ fontFamily: F.sans, fontWeight: 600, fontSize: 38, lineHeight: 1.35, color: "#F4ECDD", background: "#05070CCC", padding: "8px 22px", borderRadius: 10 }}>{chunks[idx]}</span>
    </div>
  );
};

const ActTag: React.FC<{ label: string; title: string }> = ({ label, title }) => {
  const f = useCurrentFrame();
  const t = clamp((f - 14) / 16) * (1 - clamp((f - 100) / 16));
  return (
    <div style={{ position: "absolute", right: 70, top: 46, textAlign: "right", opacity: t, transform: `translateX(${(1 - t) * 40}px)`, background: "#0A0D14E6", padding: "14px 26px", borderRadius: 16 }}>
      <div style={{ fontFamily: F.sans, fontWeight: 800, fontSize: 22, letterSpacing: "0.3em", color: "#FFB547", textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontFamily: F.serif, fontStyle: "italic", fontSize: 40, color: "#F4ECDD" }}>{title}</div>
    </div>
  );
};

const SourceTag: React.FC<{ text: string }> = ({ text }) => (
  <div style={{ position: "absolute", left: 90, top: 50, background: "#0A0D14B3", padding: "8px 16px", borderRadius: 10, fontFamily: F.sans, fontWeight: 700, fontSize: 20, letterSpacing: "0.16em", textTransform: "uppercase", color: "#D5DCE6" }}>{text}</div>
);

const VAR = ["bar", "iris", "rise", "split"];
const panel = (v: string, t: number, color: string) => {
  const base: React.CSSProperties = { position: "absolute", inset: 0, background: color };
  if (v === "bar") return <div style={{ ...base, clipPath: `inset(0 ${100 - t * 100}% 0 0)` }} />;
  if (v === "rise") return <div style={{ ...base, clipPath: `inset(${100 - t * 100}% 0 0 0)` }} />;
  if (v === "iris") return <div style={{ ...base, WebkitMaskImage: `radial-gradient(circle at 50% 50%, black ${t * 80}%, transparent ${t * 80 + 0.5}%)` }} />;
  const h = t * 50;
  return <><div style={{ ...base, bottom: `${100 - h}%` }} /><div style={{ ...base, top: `${100 - h}%` }} /></>;
};
/** Footage-to-footage: quick dip. Anything involving graphics: coloured wipe in the next shot's colour. */
const Trans: React.FC<{ dur: number; i: number }> = ({ dur, i }) => {
  const f = useCurrentFrame();
  const cur = SHOTS[i], nxt = SHOTS[i + 1], prev = SHOTS[i - 1];
  const real = (s?: Shot) => !!s && (s.kind === "footage" || s.kind === "photo");
  const E = Easing.bezier(0.7, 0, 0.25, 1);
  if (prev && f < 8) {
    if (real(prev) && real(cur) && cur.transition !== "bar" && cur.transition !== "iris") return <AbsoluteFill style={{ background: "#000", opacity: 0.55 * (1 - f / 8) }} />;
    return <AbsoluteFill style={{ background: bgOf(cur, i), opacity: 1 - f / 8 }} />;
  }
  if (nxt) {
    const wipe = !(real(cur) && real(nxt)) || nxt.transition && nxt.transition !== "fade";
    const L = wipe ? 12 : 8;
    if (f >= dur - L) {
      const t = interpolate(f, [dur - L, dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: E });
      if (!wipe) return <AbsoluteFill style={{ background: "#000", opacity: 0.55 * t }} />;
      return <AbsoluteFill>{panel(nxt.transition && nxt.transition !== "fade" ? nxt.transition : VAR[i % 4], t, bgOf(nxt, i + 1))}</AbsoluteFill>;
    }
  }
  return null;
};

const Finish: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <>
      <AbsoluteFill style={{ backgroundImage: `url(${staticFile("grain.png")})`, backgroundSize: "512px 512px", backgroundPosition: `${(f * 37) % 512}px ${(f * 91) % 512}px`, opacity: 0.06, mixBlendMode: "overlay" }} />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 50%, transparent 62%, #00000055 100%)" }} />
    </>
  );
};

export const Film: React.FC = () => (
  <AbsoluteFill style={{ background: "#000" }}>
    {timing.shots.map((t, i) => {
      const s = SHOTS[i];
      const k = s.kind ?? "graphic";
      return (
        <Sequence key={s.id} from={t.start} durationInFrames={t.dur} premountFor={30}>
          {k === "footage" || k === "photo" ? <Footage s={s} dur={t.dur} i={i} /> : k === "subscribe" ? <SubMid dur={t.dur} /> : k === "endcard" ? <EndCard dur={t.dur} /> : k === "intro" ? <Intro s={s} dur={t.dur} /> : <Graphic s={s} dur={t.dur} i={i} />}
          {s.act ? <ActTag label={s.act.label} title={s.act.title} /> : null}
          {s.source ? <SourceTag text={s.source} /> : null}
          {s.text && k !== "endcard" && k !== "subscribe" ? <Caption text={s.text} dur={t.dur} /> : null}
          <Trans dur={t.dur} i={i} />
        </Sequence>
      );
    })}
    <Finish />
  </AbsoluteFill>
);
export const TOTAL = timing.total;
