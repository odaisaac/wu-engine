import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { F } from "./theme";
import { THEMES, ThemeCtx } from "./themes";
import { Bg, KText, Logo, Particles, clamp, useSpr } from "./motion";

const Thumb: React.FC<{ s: number; color: string }> = ({ s, color }) => (
  <svg viewBox="0 0 100 100" width={s} height={s}><path d="M8 44h18v48H8zM32 90V46l18-34c3-6 13-4 13 4v20h22c6 0 10 6 9 11l-6 32c-1 6-6 11-12 11z" fill={color} /></svg>
);
const Bell: React.FC<{ s: number; color: string; rot: number }> = ({ s, color, rot }) => (
  <svg viewBox="0 0 100 100" width={s} height={s} style={{ transform: `rotate(${rot}deg)`, transformOrigin: "50% 10%" }}><path d="M50 8c-4 0-6 3-6 6v3c-14 3-22 15-22 29v18L12 76v4h76v-4L78 64V46c0-14-8-26-22-29v-3c0-3-2-6-6-6zM40 84a10 10 0 0 0 20 0z" fill={color} /></svg>
);
const Cursor: React.FC<{ x: number; y: number; press: number }> = ({ x, y, press }) => (
  <svg viewBox="0 0 40 60" width={60} height={90} style={{ position: "absolute", left: x, top: y, transform: `scale(${1 - press * 0.15})`, filter: "drop-shadow(0 6px 10px #0006)" }}><path d="M2 2 L2 46 L13 36 L21 56 L29 52 L21 33 L36 33 Z" fill="#FFFFFF" stroke="#15171E" strokeWidth={3} strokeLinejoin="round" /></svg>
);

const SubButton: React.FC<{ clicked: number; scale: number }> = ({ clicked, scale }) => (
  <div style={{ display: "inline-flex", alignItems: "center", gap: 18, background: clicked > 0.5 ? "#D9D9D9" : "#E62117", color: clicked > 0.5 ? "#15171E" : "#FFFFFF", fontFamily: F.sans, fontWeight: 900, fontSize: 64, padding: "26px 56px", borderRadius: 999, transform: `scale(${scale})`, boxShadow: "0 20px 60px #0005", letterSpacing: "0.04em" }}>
    {clicked > 0.5 ? "✓ SUBSCRIBED" : "SUBSCRIBE"}
  </div>
);

export const SubMid: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const T = THEMES.sun;
  const clickF = 150;
  const press = f >= clickF && f < clickF + 8 ? 1 : 0;
  const clicked = f >= clickF + 4 ? 1 : 0;
  const pop = useSpr(clickF + 4, { damping: 8, stiffness: 220 });
  const away = interpolate(f, [clickF + 14, clickF + 40], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.4, 0, 0.2, 1) });
  const cx = away * 340 + interpolate(f, [70, clickF], [1550, 1000], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.6, 0, 0.2, 1) });
  const cy = away * 260 + interpolate(f, [70, clickF], [1000, 640], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.6, 0, 0.2, 1) });
  const bellOn = clamp((f - 200) / 10);
  const ring = f > 200 ? Math.sin((f - 200) / 2.2) * 22 * Math.max(0, 1 - (f - 200) / 60) : 0;
  const like = useSpr(240, { damping: 9, stiffness: 200 });
  const btn = useSpr(30, { damping: 11, stiffness: 140 });
  const out = 1;
  return (
    <ThemeCtx.Provider value={T}>
      <AbsoluteFill style={{ opacity: out }}>
        <Bg seed={3} />
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", paddingBottom: 80 }}>
          <KText words={[["Enjoying"], ["this?", "#D6281F"]]} size={150} at={4} align="center" font="sans" weight={900} />
          <div style={{ height: 30 }} />
          <div style={{ fontFamily: F.sans, fontWeight: 600, fontSize: 48, color: "#15171E", opacity: clamp((f - 20) / 15) }}>Like the video and subscribe to The World Unpacked</div>
          <div style={{ height: 70 }} />
          <div style={{ display: "flex", alignItems: "center", gap: 40, opacity: clamp(btn * 2), transform: `translateY(${(1 - btn) * 60}px)` }}>
            <Logo size={150} />
            <div style={{ transform: `scale(${1 + (clicked ? (pop - 1) * 0.15 : 0)})` }}><SubButton clicked={clicked} scale={1} /></div>
            <div style={{ opacity: bellOn, transform: `scale(${0.5 + 0.5 * bellOn})` }}><Bell s={120} color="#15171E" rot={ring} /></div>
            <div style={{ opacity: clamp(like * 2), transform: `scale(${0.4 + 0.6 * like}) rotate(${(1 - like) * -30}deg)` }}><Thumb s={120} color="#2346E8" /></div>
          </div>
        </AbsoluteFill>
        {f < dur - 20 ? <Cursor x={cx} y={cy} press={press} /> : null}
        {clicked ? <Particles n={30} color="#D6281F" /> : null}
      </AbsoluteFill>
    </ThemeCtx.Provider>
  );
};

export const EndCard: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const T = THEMES.night;
  const lg = useSpr(4, { damping: 11, stiffness: 90 });
  const ring = f > 120 ? Math.sin((f - 120) / 2.2) * 20 * Math.max(0, 1 - (f - 120) / 60) : 0;
  const box = (i: number) => useSpr(40 + i * 10, { damping: 13, stiffness: 120 });
  const b0 = box(0), b1 = box(1);
  return (
    <ThemeCtx.Provider value={T}>
      <AbsoluteFill>
        <Bg seed={8} />
        <Particles n={40} />
        <div style={{ position: "absolute", left: 110, top: 150, width: 760 }}>
          <div style={{ transform: `scale(${0.4 + 0.6 * lg})`, transformOrigin: "0 50%", opacity: clamp(lg * 2) }}><Logo size={220} /></div>
          <div style={{ height: 36 }} />
          <KText words={[["Thanks"], ["for"], ["watching.", "#FFB547"]]} size={96} at={14} />
          <div style={{ height: 40 }} />
          <div style={{ display: "flex", gap: 30, alignItems: "center", opacity: clamp((f - 60) / 15) }}>
            <Thumb s={90} color="#FFFFFF" />
            <SubButton clicked={0} scale={0.8} />
            <Bell s={90} color="#FFFFFF" rot={ring} />
          </div>
          <div style={{ height: 34 }} />
          <div style={{ fontFamily: F.sans, fontWeight: 600, fontSize: 38, color: "#9AA6B8", opacity: clamp((f - 80) / 15) }}>New documentaries from The World Unpacked</div>
        </div>
        {[b0, b1].map((b, i) => (
          <div key={i} style={{ position: "absolute", left: 1040, top: 160 + i * 400, width: 640, height: 360, borderRadius: 24, border: "4px dashed #FFFFFF55", background: "#FFFFFF0D", opacity: clamp(b * 2), transform: `scale(${0.9 + 0.1 * b})`, display: "grid", placeItems: "center" }}>
            <div style={{ fontFamily: F.sans, fontWeight: 800, fontSize: 34, letterSpacing: "0.2em", color: "#FFFFFF99" }}>{i === 0 ? "WATCH NEXT" : "MORE FROM THE CHANNEL"}</div>
          </div>
        ))}
        <AbsoluteFill style={{ background: "#0A0D14", opacity: clamp((f - (dur - 20)) / 20) }} />
      </AbsoluteFill>
    </ThemeCtx.Provider>
  );
};

/** Corner subscribe prompt that plays over the running film (shot flag "nudge": true) — no full-screen pause. ~5 s. */
export const SubNudge: React.FC<{ at?: number }> = ({ at = 24 }) => {
  const f = useCurrentFrame() - at;
  const inn = useSpr(at, { damping: 14, stiffness: 130 });
  const clickF = 62;
  const clicked = f >= clickF + 3;
  const pop = useSpr(at + clickF + 3, { damping: 8, stiffness: 240 });
  const out = clamp((f - 138) / 12);
  const ring = f > clickF + 14 ? Math.sin((f - clickF - 14) / 2.2) * 20 * Math.max(0, 1 - (f - clickF - 14) / 44) : 0;
  const cx = interpolate(f, [14, clickF], [330, 196], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.6, 0, 0.2, 1) });
  const cy = interpolate(f, [14, clickF], [170, 64], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.6, 0, 0.2, 1) });
  if (f < 0 || f > 152) return null;
  return (
    <div style={{ position: "absolute", right: 56, top: 48, opacity: clamp(inn * 2) * (1 - out), transform: `translateX(${(1 - inn) * 140 + out * 60}px) scale(1.25)`, transformOrigin: "100% 0", display: "flex", alignItems: "center", gap: 18, background: "#0A0D14E8", padding: "14px 22px 14px 14px", borderRadius: 999, boxShadow: "0 14px 40px #0008", border: "2px solid #FFFFFF22" }}>
      <Logo size={78} />
      <div style={{ transform: `scale(${clicked ? 1 + (pop - 1) * 0.12 : 1})`, background: clicked ? "#E4E4E4" : "#E62117", color: clicked ? "#15171E" : "#FFFFFF", fontFamily: F.sans, fontWeight: 900, fontSize: 34, letterSpacing: "0.04em", padding: "14px 30px", borderRadius: 999, minWidth: 250, textAlign: "center" }}>{clicked ? "✓ SUBSCRIBED" : "SUBSCRIBE"}</div>
      <div style={{ opacity: clicked ? 1 : 0.35 }}><Bell s={54} color="#FFFFFF" rot={ring} /></div>
      {f > 12 && f < clickF + 30 ? <svg viewBox="0 0 40 60" width={38} height={57} style={{ position: "absolute", left: cx, top: cy, transform: `scale(${f >= clickF && f < clickF + 7 ? 0.85 : 1})`, filter: "drop-shadow(0 4px 8px #0008)" }}><path d="M2 2 L2 46 L13 36 L21 56 L29 52 L21 33 L36 33 Z" fill="#FFFFFF" stroke="#15171E" strokeWidth={3} strokeLinejoin="round" /></svg> : null}
    </div>
  );
};
