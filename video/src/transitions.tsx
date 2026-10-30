import React from "react";
import { AbsoluteFill, Easing, useCurrentFrame } from "remotion";
import { STYLE } from "./styles";
import { rand } from "./motion";

/**
 * Premium transitions + directional motion blur.
 * Motion blur uses SVG feGaussianBlur with a one-axis stdDeviation (true directional blur, unlike CSS blur()).
 * Filters are only applied on frames where something is actually moving, so render cost stays low.
 */
export type TType = "bar" | "iris" | "rise" | "split" | "whip" | "push" | "punch" | "leak" | "glitch" | "dip";
const MOTION: TType[] = ["whip", "push", "punch", "leak", "glitch"];
const MAXB = 60;

export const MBDefs: React.FC = () => (
  <svg width={0} height={0} style={{ position: "absolute" }}>
    <defs>
      {Array.from({ length: MAXB }, (_, k) => k + 1).map((n) => (
        <React.Fragment key={n}>
          <filter id={`mbx-${n}`} x="-20%" y="-5%" width="140%" height="110%" colorInterpolationFilters="sRGB"><feGaussianBlur stdDeviation={`${n} 0`} /></filter>
          <filter id={`mby-${n}`} x="-5%" y="-30%" width="110%" height="160%" colorInterpolationFilters="sRGB"><feGaussianBlur stdDeviation={`0 ${n}`} /></filter>
        </React.Fragment>
      ))}
    </defs>
  </svg>
);
/** CSS filter for a horizontal / vertical motion blur of `px` (≈ distance moved this frame). Empty string when still. */
export const mbx = (px: number) => { const n = Math.min(MAXB, Math.round(Math.abs(px) * 0.35)); return n >= 1 ? `url(#mbx-${n})` : ""; };
export const mby = (px: number) => { const n = Math.min(MAXB, Math.round(Math.abs(px) * 0.35)); return n >= 1 ? `url(#mby-${n})` : ""; };

type ShotLite = { kind?: string; transition?: string };
const real = (s?: ShotLite) => !!s && (s.kind === "footage" || s.kind === "photo");

/** The transition used on the cut AFTER shot i. */
export const cutType = (shots: ShotLite[], i: number): TType | null => {
  const cur = shots[i], nxt = shots[i + 1];
  if (!nxt) return null;
  if (nxt.transition) return nxt.transition === "fade" ? "dip" : (nxt.transition as TType);
  const list = STYLE.trans as TType[];
  if (real(cur) && real(nxt)) {
    // Footage → footage: mostly clean cuts, a motion transition every other cut. Premium edits don't wipe every shot.
    const mo = list.filter((t) => MOTION.includes(t));
    return i % 2 === 0 && mo.length ? mo[(i / 2) % mo.length] : "dip";
  }
  return list[i % list.length];
};
export const lenOf = (t: TType | null, exit: boolean) => (!t ? 0 : t === "dip" ? 8 : ["bar", "iris", "rise", "split"].includes(t) ? (exit ? 12 : 8) : t === "glitch" ? (exit ? 8 : 6) : 10);

const EIN = Easing.bezier(0.55, 0, 1, 0.45);
const EOUT = Easing.bezier(0, 0.55, 0.45, 1);
const EIO = Easing.bezier(0.7, 0, 0.25, 1);

/** Moves/blurs the shot's content on exit and entry. Backdrop fills any revealed area with the neighbouring shot's colour. */
export const Mover: React.FC<{ i: number; dur: number; shots: ShotLite[]; bg: (i: number) => string; children: React.ReactNode }> = ({ i, dur, shots, bg, children }) => {
  const f = useCurrentFrame();
  const out = cutType(shots, i), inn = i > 0 ? cutType(shots, i - 1) : null;
  const Lo = lenOf(out, true), Li = lenOf(inn, false);
  let tf = "", filt = "", back: string | undefined;
  if (out && f >= dur - Lo) {
    const t = (f - (dur - Lo)) / Lo, tp = Math.max(0, (f - 1 - (dur - Lo)) / Lo);
    if (out === "whip") { const x = -EIN(t) * 1100, xp = -EIN(tp) * 1100; tf = `translateX(${x}px)`; filt = mbx(x - xp); back = bg(i + 1); }
    if (out === "push") { const x = -EIO(t) * 1920, xp = -EIO(tp) * 1920; tf = `translateX(${x}px)`; filt = mbx(x - xp); back = bg(i + 1); }
    if (out === "punch") tf = `scale(${1 + 0.4 * EIN(t)})`;
    if (out === "leak") filt = `brightness(${1 + 1.1 * t * t}) saturate(${1 + 0.4 * t})`;
    if (out === "glitch") tf = `translateX(${(rand(f * 7.3) - 0.5) * 70 * t}px)`;
  } else if (inn && f < Li) {
    const e = 1 - f / Li, ep = 1 - (f - 1) / Li;
    if (inn === "whip") { const x = EOUT(e) * 1100, xp = EOUT(Math.min(1, ep)) * 1100; tf = `translateX(${x}px)`; filt = mbx(xp - x); back = bg(i - 1); }
    if (inn === "push") { const x = EIO(e) * 1920, xp = EIO(Math.min(1, ep)) * 1920; tf = `translateX(${x}px)`; filt = mbx(xp - x); back = bg(i - 1); }
    if (inn === "punch") tf = `scale(${1 + 0.14 * EOUT(e)})`;
    if (inn === "leak") filt = `brightness(${1 + 1.1 * e * e}) saturate(${1 + 0.4 * e})`;
    if (inn === "glitch") tf = `translateX(${(rand(f * 5.1 + 3) - 0.5) * 70 * e}px)`;
  }
  return (
    <AbsoluteFill>
      {back ? <AbsoluteFill style={{ background: back }} /> : null}
      <AbsoluteFill style={{ transform: tf || undefined, filter: filt || undefined }}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};

const panel = (v: string, t: number, color: string) => {
  const base: React.CSSProperties = { position: "absolute", inset: 0, background: color };
  if (v === "bar") return <div style={{ ...base, clipPath: `inset(0 ${100 - t * 100}% 0 0)` }} />;
  if (v === "rise") return <div style={{ ...base, clipPath: `inset(${100 - t * 100}% 0 0 0)` }} />;
  if (v === "iris") return <div style={{ ...base, WebkitMaskImage: `radial-gradient(circle at 50% 50%, black ${t * 80}%, transparent ${t * 80 + 0.5}%)` }} />;
  const h = t * 50;
  return <><div style={{ ...base, bottom: `${100 - h}%` }} /><div style={{ ...base, top: `${100 - h}%` }} /></>;
};

const Leak: React.FC<{ k: number; f: number }> = ({ k, f }) => (
  <AbsoluteFill style={{ mixBlendMode: "screen", opacity: k }}>
    <AbsoluteFill style={{ background: `radial-gradient(ellipse 60% 80% at ${20 + f * 2.2 % 60}% 40%, ${STYLE.accent} 0%, transparent 60%)` }} />
    <AbsoluteFill style={{ background: "radial-gradient(ellipse 50% 70% at 75% 65%, #FF7A2F 0%, transparent 65%)" }} />
    <AbsoluteFill style={{ background: "#FFF4E0", opacity: Math.max(0, k - 0.6) * 1.6 }} />
  </AbsoluteFill>
);

const Glitch: React.FC<{ k: number; f: number }> = ({ k, f }) => {
  const cols = [STYLE.accent, "#00F0FF", "#FF2E63", "#FFFFFF"];
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: 9 }, (_, n) => {
        const r = rand(f * 17.7 + n * 3.1);
        if (r > 0.35 + 0.65 * k) return null;
        const y = rand(f * 3.3 + n) * 1080, h = 4 + rand(f + n * 9) * 70, x = (rand(f * 1.7 + n) - 0.5) * 300 * k;
        return <div key={n} style={{ position: "absolute", left: x, right: -x, top: y, height: h, background: cols[n % 4], mixBlendMode: "screen", opacity: 0.25 + 0.5 * k }} />;
      })}
      <AbsoluteFill style={{ background: "repeating-linear-gradient(0deg, #00000055 0 2px, transparent 2px 4px)", opacity: k }} />
      {k > 0.85 && rand(f) > 0.5 ? <AbsoluteFill style={{ background: "#FFFFFF", mixBlendMode: "difference", opacity: 0.9 }} /> : null}
    </AbsoluteFill>
  );
};

/** Overlay effects drawn above the shot: colour wipes, dips, flashes, light leaks, glitch bars. */
export const TransFX: React.FC<{ i: number; dur: number; shots: ShotLite[]; bg: (i: number) => string }> = ({ i, dur, shots, bg }) => {
  const f = useCurrentFrame();
  const out = cutType(shots, i), inn = i > 0 ? cutType(shots, i - 1) : null;
  const Lo = lenOf(out, true), Li = lenOf(inn, false);
  if (inn && f < Li) {
    const e = 1 - f / Li;
    if (inn === "dip") return <AbsoluteFill style={{ background: "#000", opacity: 0.55 * e }} />;
    if (["bar", "iris", "rise", "split"].includes(inn)) return <AbsoluteFill style={{ background: bg(i), opacity: e }} />;
    if (inn === "punch") return <AbsoluteFill style={{ background: "#FFFFFF", opacity: 0.85 * Math.max(0, e * 1.6 - 0.6) }} />;
    if (inn === "leak") return <Leak k={e * e} f={f + 40} />;
    if (inn === "glitch") return <Glitch k={e} f={f + 101} />;
    return null;
  }
  if (out && f >= dur - Lo) {
    const t = (f - (dur - Lo)) / Lo;
    if (out === "dip") return <AbsoluteFill style={{ background: "#000", opacity: 0.55 * t }} />;
    if (["bar", "iris", "rise", "split"].includes(out)) return <AbsoluteFill>{panel(out, EIO(t), bg(i + 1))}</AbsoluteFill>;
    if (out === "punch") return <AbsoluteFill style={{ background: "#FFFFFF", opacity: 0.85 * Math.max(0, t * 2 - 1) }} />;
    if (out === "leak") return <Leak k={t * t} f={f} />;
    if (out === "glitch") return <Glitch k={t} f={f} />;
  }
  return null;
};
