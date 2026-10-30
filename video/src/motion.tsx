import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig, Img, staticFile } from "remotion";
import { C, F, DS } from "./theme";
import { STYLE } from "./styles";
import { useTh } from "./themes";

export const OUT = Easing.bezier(0.16, 1, 0.3, 1);
export const IO = Easing.bezier(0.65, 0, 0.35, 1);
export const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const mix = (a: number, b: number, t: number) => a + (b - a) * t;
export const rand = (n: number) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

export const useSpr = (delay = 0, cfg: { damping?: number; stiffness?: number; mass?: number } = {}) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  return spring({ frame: f - delay, fps, config: { damping: 16, stiffness: 120, mass: 0.9, ...cfg } });
};
export const useT = (start: number, dur: number, e: (x: number) => number = OUT) => {
  const f = useCurrentFrame();
  return interpolate(f, [start, start + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: e });
};

/** Slow camera push / drift over the whole shot. */
export const Cam: React.FC<{ dur: number; z?: [number, number]; x?: [number, number]; y?: [number, number]; children?: React.ReactNode }> = ({ dur, z = [1.0, 1.07], x = [0, 0], y = [0, 0], children }) => {
  const f = useCurrentFrame();
  const t = clamp(f / dur);
  const e = IO(t);
  const zz: [number, number] = [Math.min(z[0], 1.05), Math.min(z[1], 1.05)];
  return (
    <AbsoluteFill style={{ transform: `translate(${mix(x[0], x[1], e) * 0.4}px, ${mix(y[0], y[1], e)}px) scale(${mix(zz[0], zz[1], e)})`, transformOrigin: "50% 50%" }}>
      {children}
    </AbsoluteFill>
  );
};

/** Animated backdrop: drifting soft colour blobs on ink. */
export const Bg: React.FC<{ a?: string; b?: string; seed?: number }> = ({ seed = 1 }) => {
  const f = useCurrentFrame(); const T = useTh();
  return (
    <AbsoluteFill style={{ background: T.bg, overflow: "hidden" }}>
      <div style={{ position: "absolute", width: 1800, height: 1800, background: `radial-gradient(circle at 50% 50%, ${T.blobA} 0%, transparent 60%)`, opacity: T.dark ? 0.2 : 0.3, left: -550 + Math.sin(f / 90 + seed) * 120, top: -650 + Math.cos(f / 110 + seed) * 90 }} />
      <div style={{ position: "absolute", width: 1600, height: 1600, background: `radial-gradient(circle at 50% 50%, ${T.blobB} 0%, transparent 60%)`, opacity: T.dark ? 0.18 : 0.26, right: -600 + Math.cos(f / 100 + seed * 2) * 120, bottom: -700 + Math.sin(f / 80 + seed) * 100 }} />
      <AbsoluteFill style={{ backgroundImage: T.pattern, backgroundSize: T.patSize, backgroundPosition: `${(f * 0.4) % 400}px ${(f * 0.2) % 400}px` }} />
    </AbsoluteFill>
  );
};

/** Word-by-word masked rise with spring. words: string or [text,color][] */
export const KText: React.FC<{ words: string | [string, string?][]; size?: number; at?: number; stagger?: number; color?: string; italic?: boolean; weight?: number; align?: "left" | "center"; font?: "serif" | "sans"; maxW?: number; lh?: number }> = ({ words, size = 110, at = 0, stagger = 5, color, italic, weight = 700, align = "left", font = "serif", maxW, lh = 1.08 }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const T = useTh();
  const arr: [string, string?][] = typeof words === "string" ? words.split(" ").map((w) => [w]) : words;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: align === "center" ? "center" : "flex-start", columnGap: size * 0.26, rowGap: 0, maxWidth: maxW }}>
      {arr.map(([w, c], i) => {
        const s = spring({ frame: f - at - i * stagger, fps, config: { damping: 15, stiffness: 140, mass: 0.8 } });
        return (
          <span key={i} style={{ display: "inline-block", overflow: "hidden", paddingBottom: size * 0.12, marginBottom: -size * 0.12, lineHeight: lh }}>
            <span style={{ display: "inline-block", fontFamily: font === "serif" ? F.serif : F.sans, fontWeight: weight, fontStyle: italic && (font === "sans" || STYLE.displayItalicOk) ? "italic" : "normal", fontSize: font === "serif" ? size * DS : size, textTransform: font === "serif" && STYLE.displayUpper ? "uppercase" : undefined, color: c ?? color ?? T.fg, transform: `translateY(${(1 - s) * 115}%) rotate(${(1 - s) * 4}deg)`, opacity: clamp(s * 1.6), transformOrigin: "0 100%" }}>{w}</span>
          </span>
        );
      })}
    </div>
  );
};

export const Tag: React.FC<{ children: React.ReactNode; at?: number; color?: string; size?: number }> = ({ children, at = 0, color, size = 30 }) => {
  const s = useSpr(at); const T = useTh();
  return <div style={{ fontFamily: F.mono, fontWeight: 700, fontSize: size, letterSpacing: STYLE.mono ? "0.12em" : "0.22em", textTransform: "uppercase", color: color ?? T.amber, opacity: s, transform: `translateX(${(1 - s) * -40}px)` }}>{children}</div>;
};

export const Count: React.FC<{ to: number; from?: number; at?: number; d?: number; dec?: number; pre?: string; suf?: string; size?: number; color?: string; sep?: boolean; weight?: number }> = ({ to, from = 0, at = 0, d = 40, dec = 0, pre = "", suf = "", size = 200, color, sep = true, weight = 700 }) => {
  const T = useTh();
  const t = useT(at, d, Easing.out(Easing.cubic));
  const v = mix(from, to, t);
  const txt = sep ? v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec }) : v.toFixed(dec);
  return <span style={{ fontFamily: F.serif, fontWeight: weight, fontSize: size * DS, color: color ?? T.fg, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>{pre}{txt}{suf}</span>;
};

export const Ring: React.FC<{ cx: number; cy: number; r: number; v: number; at?: number; d?: number; color?: string; w?: number }> = ({ cx, cy, r, v, at = 0, d = 50, color = C.amber, w = 26 }) => {
  const T = useTh();
  const t = useT(at, d, Easing.out(Easing.cubic));
  const L = 2 * Math.PI * r;
  return (
    <g transform={`rotate(-90 ${cx} ${cy})`}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={T.line} strokeWidth={w} />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={w} strokeLinecap="round" strokeDasharray={L} strokeDashoffset={L * (1 - v * t)} />
    </g>
  );
};

export const BarRow: React.FC<{ x: number; y: number; w: number; h?: number; v: number; label: string; val: string; color: string; at: number; d?: number; labW?: number }> = ({ x, y, w, h = 56, v, label, val, color, at, d = 40, labW = 330 }) => {
  const T = useTh();
  const t = useT(at, d);
  const s = useSpr(at);
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, display: "flex", alignItems: "center", gap: 28, opacity: clamp(s * 2) }}>
      <div style={{ width: labW, fontFamily: F.sans, fontWeight: 600, fontSize: 40, color: T.fg }}>{label}</div>
      <div style={{ flex: 1, height: h, background: T.panel, borderRadius: h / 2, position: "relative", overflow: "hidden" }}>
        <div style={{ width: `${v * t * 100}%`, height: "100%", background: color, borderRadius: h / 2 }} />
      </div>
      <div style={{ minWidth: 230, textAlign: "right", whiteSpace: "nowrap", fontFamily: F.serif, fontWeight: 700, fontSize: 56 * DS, color, fontVariantNumeric: "tabular-nums" }}>{val}</div>
    </div>
  );
};

export const Card: React.FC<{ x: number; y: number; w: number; h: number; at?: number; children?: React.ReactNode; color?: string }> = ({ x, y, w, h, at = 0, children, color = C.line }) => {
  const T = useTh();
  const s = useSpr(at, { damping: 14, stiffness: 110 });
  return <div style={{ position: "absolute", left: x, top: y, width: w, height: h, background: T.panel, border: `3px solid ${color}`, borderRadius: 28, opacity: clamp(s * 2), transform: `translateY(${(1 - s) * 60}px) scale(${0.94 + 0.06 * s})`, boxShadow: "0 30px 80px #0008", padding: 40 }}>{children}</div>;
};

/** Little house icon, built from paths. */
export const House: React.FC<{ x: number; y: number; s?: number; color?: string; roof?: string; lit?: number; at?: number; crack?: number }> = ({ x, y, s = 1, color, roof, lit = 1, at = 0, crack = 0 }) => {
  const T = useTh();
  const k = useSpr(at, { damping: 12, stiffness: 150 });
  return (
    <g transform={`translate(${x} ${y}) scale(${s * (0.6 + 0.4 * k)})`} opacity={clamp(k * 2)}>
      <rect x={-90} y={-110} width={180} height={110} rx={6} fill={color ?? T.house} stroke={T.dark ? "none" : "#15171E"} strokeWidth={6} />
      <path d="M-120,-105 L0,-200 L120,-105 Z" fill={roof ?? (T.name === "coral" ? "#15171E" : T.coral)} stroke={T.dark ? "none" : "#15171E"} strokeWidth={6} strokeLinejoin="round" />
      <rect x={-24} y={-70} width={48} height={70} rx={4} fill="#15171E" />
      <rect x={-72} y={-92} width={34} height={34} rx={4} fill={C.amber} opacity={0.35 + 0.65 * lit} />
      <rect x={38} y={-92} width={34} height={34} rx={4} fill={C.amber} opacity={0.35 + 0.65 * lit} />
      {crack > 0 ? <path d="M10,-200 L-6,-150 L14,-120 L-8,-80 L8,-40 L-4,0" stroke={C.ink} strokeWidth={9} fill="none" strokeDasharray={260} strokeDashoffset={260 * (1 - crack)} strokeLinecap="round" /> : null}
    </g>
  );
};

export const Skyline: React.FC<{ x0?: number; w?: number; base?: number; n?: number; seed?: number; build?: number; color?: string; lit?: number }> = ({ x0 = 0, w = 1920, base = 900, n = 16, seed = 1, build = 1, color, lit = 0.5 }) => {
  const f = useCurrentFrame(); const T = useTh();
  const bw = w / n;
  return (
    <g>
      {Array.from({ length: n }, (_, i) => {
        const h = 160 + rand(i + seed) * 520;
        const t = clamp(build * (n + 4) - i * 0.9, 0, 1);
        const e = OUT(t);
        const cols = Math.max(2, Math.floor((bw - 20) / 26));
        const rows = Math.floor(h / 48);
        return (
          <g key={i}>
            <rect x={x0 + i * bw + 6} y={base - h * e} width={bw - 12} height={h * e + 400} fill={color ?? T.sky} />
            {e > 0.95 ? Array.from({ length: rows * cols }, (_, k) => {
              const on = rand(k + i * 31 + seed + Math.floor(f / 45) * (rand(k) < 0.04 ? 1 : 0)) < lit;
              return on ? <rect key={k} x={x0 + i * bw + 18 + (k % cols) * 26} y={base - h + 20 + Math.floor(k / cols) * 48} width={14} height={22} fill={T.win} opacity={0.8} /> : null;
            }) : null}
          </g>
        );
      })}
    </g>
  );
};

export const Person: React.FC<{ x: number; y: number; s?: number; color?: string; walk?: number }> = ({ x, y, s = 1, color: col, walk = 0 }) => {
  const T = useTh(); const color = col ?? T.fg;
  const sw = Math.sin(walk) * 22;
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <ellipse cx={0} cy={6} rx={60} ry={9} fill="#000" opacity={0.35} />
      <line x1={-8} y1={-70} x2={-8 - sw} y2={0} stroke={color} strokeWidth={14} strokeLinecap="round" />
      <line x1={8} y1={-70} x2={8 + sw} y2={0} stroke={color} strokeWidth={14} strokeLinecap="round" />
      <rect x={-24} y={-170} width={48} height={110} rx={22} fill={color} />
      <line x1={-20} y1={-150} x2={-34 + sw * 0.6} y2={-90} stroke={color} strokeWidth={12} strokeLinecap="round" />
      <line x1={20} y1={-150} x2={34 - sw * 0.6} y2={-90} stroke={color} strokeWidth={12} strokeLinecap="round" />
      <circle cx={0} cy={-202} r={28} fill={color} />
    </g>
  );
};

export const Particles: React.FC<{ n?: number; color?: string }> = ({ n = 40, color }) => {
  const f = useCurrentFrame(); const T = useTh(); color = color ?? T.amber;
  return (
    <svg viewBox="0 0 1920 1080" width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
      {Array.from({ length: n }, (_, i) => (
        <circle key={i} cx={rand(i) * 1920 + Math.sin(f / 50 + i) * 25} cy={(rand(i + 9) * 1200 - f * (0.3 + rand(i + 4) * 0.7) + 3600) % 1200} r={1.5 + rand(i + 7) * 3} fill={color} opacity={0.12 + rand(i + 2) * 0.3} />
      ))}
    </svg>
  );
};

export const Logo: React.FC<{ size: number; style?: React.CSSProperties }> = ({ size, style }) => (
  <Img src={staticFile("logo.png")} style={{ width: size, height: size, borderRadius: size / 2, ...style }} />
);


/** Editorial chrome for graphic scenes: corner registration marks, a giant outlined "ghost" of the key figure drifting on the right, and a hairline that draws in. Fills dead space the way a designed broadcast frame does. */
export const Deco: React.FC<{ ghost?: string; dur: number; seed?: number }> = ({ ghost, dur, seed = 0 }) => {
  const f = useCurrentFrame(); const T = useTh();
  const t = clamp(f / dur);
  const s = useSpr(4, { damping: 20, stiffness: 80 });
  const line = T.dark ? "#FFFFFF" : "#000000";
  const mark = (x: number, y: number, sx: number, sy: number) => (
    <div style={{ position: "absolute", left: x, top: y, width: 34, height: 34, borderLeft: sx > 0 ? `2px solid ${line}` : undefined, borderRight: sx < 0 ? `2px solid ${line}` : undefined, borderTop: sy > 0 ? `2px solid ${line}` : undefined, borderBottom: sy < 0 ? `2px solid ${line}` : undefined, opacity: 0.28 * s, transform: `translate(${(1 - s) * -sx * 18}px, ${(1 - s) * -sy * 18}px)` }} />
  );
  const g = ghost ? ghost.slice(0, 8) : "";
  const gSize = g.length <= 3 ? 760 : g.length <= 5 ? 560 : 400;
  return (
    <AbsoluteFill style={{ pointerEvents: "none", overflow: "hidden" }}>
      {g ? <div style={{ position: "absolute", right: -60 + mix(0, 70, IO(t)), top: "50%", transform: `translateY(-52%) scale(${0.96 + 0.04 * s})`, fontFamily: F.serif, fontWeight: 800, fontSize: gSize * DS, lineHeight: 0.9, color: "transparent", WebkitTextStroke: `3px ${T.fg}`, opacity: 0.1 * s, whiteSpace: "nowrap", letterSpacing: "-0.02em", textTransform: STYLE.displayUpper ? "uppercase" : undefined }}>{g}</div> : null}
      {mark(28, 28, 1, 1)}{mark(1920 - 62, 28, -1, 1)}{mark(28, 1080 - 62, 1, -1)}{mark(1920 - 62, 1080 - 62, -1, -1)}
      <div style={{ position: "absolute", left: 130, top: 112, height: 2, width: 1660 * OUT(clamp((f - 6) / 40)), background: line, opacity: 0.14 }} />
      <div style={{ position: "absolute", right: 130, top: 124, fontFamily: F.sans, fontWeight: 600, fontSize: 18, letterSpacing: "0.3em", color: T.dim, opacity: 0.8 * clamp((f - 120) / 15) }}>{String(seed + 1).padStart(2, "0")}</div>
    </AbsoluteFill>
  );
};
