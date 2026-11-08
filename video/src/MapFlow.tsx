import React from "react";
import { useCurrentFrame, useVideoConfig, spring, Easing, interpolate } from "remotion";
import { geoNaturalEarth1, geoPath, geoInterpolate, GeoProjection } from "d3-geo";
import { feature } from "topojson-client";
import world from "world-atlas/countries-50m.json";
import { F, DS } from "./theme";
import { STYLE } from "./styles";
import { useTh } from "./themes";
import { clamp, mix, Tag } from "./motion";

/* ------------------------------------------------------------------ */
/* Animated map: slow camera push, highlighted countries, pins, routes */
/* ------------------------------------------------------------------ */

export type MapOverlay = {
  type: "map";
  title?: string;
  note?: string;                                  // small caption bottom-left (e.g. "Illustrative routes")
  center?: [number, number];                      // [lon, lat]
  zoom?: number;                                  // 1 = whole world
  highlight?: string[];                           // country names as in world-atlas (e.g. "Vietnam", "Singapore")
  points?: { lon: number; lat: number; label?: string; big?: boolean }[];
  routes?: { from: [number, number]; to: [number, number] }[];
  equator?: boolean;                              // draw a band all the way round the globe
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const COUNTRIES = (feature(world as any, (world as any).objects.countries) as any).features as any[];

const useProj = (center: [number, number], zoom: number, t: number): GeoProjection => {
  const z = zoom * mix(0.9, 1.0, Easing.bezier(0.33, 0, 0.2, 1)(t));
  return geoNaturalEarth1().scale(330 * z).rotate([-center[0], 0]).center([0, center[1]]).translate([960, 560]);
};

export const MapScene: React.FC<{ o: MapOverlay; dur: number }> = ({ o, dur }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const T = useTh();
  const t = clamp(f / dur);
  const proj = useProj(o.center ?? [10, 15], o.zoom ?? 1, t);
  const path = geoPath(proj);
  const hl = new Set((o.highlight ?? []).map((s) => s.toLowerCase()));
  const reveal = clamp(f / 14);
  const hlIn = clamp((f - 12) / 18);
  const land = T.dark ? "#FFFFFF14" : "#00000012";
  const edge = T.dark ? "#FFFFFF30" : "#00000030";
  const acc = T.dark ? STYLE.accent : T.amber;
  return (
    <div style={{ position: "absolute", inset: 0 }}>
      <svg viewBox="0 0 1920 1080" width={1920} height={1080} style={{ position: "absolute", inset: 0, opacity: reveal }}>
        <defs>
          <radialGradient id="mapfade" cx="50%" cy="52%" r="62%"><stop offset="70%" stopColor="#fff" /><stop offset="100%" stopColor="#000" /></radialGradient>
          <mask id="mapmask"><rect width="1920" height="1080" fill="url(#mapfade)" /></mask>
        </defs>
        <g mask="url(#mapmask)">
          <path d={path({ type: "Sphere" }) ?? ""} fill="none" stroke={edge} strokeWidth={1.5} />
          {COUNTRIES.map((c, i) => {
            const on = hl.has(String(c.properties?.name ?? "").toLowerCase());
            return <path key={i} d={path(c) ?? ""} fill={on ? acc : land} fillOpacity={on ? 0.25 + 0.6 * hlIn : 1} stroke={on ? acc : edge} strokeWidth={on ? 2.2 : 0.8} />;
          })}
          {o.equator ? (() => {
            const pts = Array.from({ length: 361 }, (_, k) => proj([-180 + k, 0]));
            const k = clamp((f - 10) / Math.max(30, dur * 0.45));
            const n = Math.max(2, Math.round(pts.length * k));
            const d = pts.slice(0, n).filter(Boolean).map((p, j) => `${j ? "L" : "M"}${p![0]},${p![1]}`).join("");
            return <path d={d} fill="none" stroke={acc} strokeWidth={22} strokeLinecap="round" opacity={0.9} />;
          })() : null}
          {(o.routes ?? []).map((r, i) => {
            const at = 18 + i * 10;
            const k = Easing.bezier(0.45, 0, 0.2, 1)(clamp((f - at) / 45));
            if (k <= 0) return null;
            const interp = geoInterpolate(r.from, r.to);
            const pts = Array.from({ length: 41 }, (_, j) => proj(interp((j / 40) * k)));
            const d = pts.filter(Boolean).map((p, j) => `${j ? "L" : "M"}${p![0]},${p![1]}`).join("");
            const head = pts[pts.length - 1];
            return (
              <g key={i}>
                <path d={d} fill="none" stroke={acc} strokeWidth={4} strokeDasharray="2 12" strokeLinecap="round" />
                {head ? <circle cx={head[0]} cy={head[1]} r={9} fill={T.fg} stroke={acc} strokeWidth={4} /> : null}
              </g>
            );
          })}
          {(o.points ?? []).map((p, i) => {
            const xy = proj([p.lon, p.lat]); if (!xy) return null;
            const s = spring({ frame: f - 10 - i * 6, fps, config: { damping: 11, stiffness: 160 } });
            const pulse = (f * 0.03 + i * 0.3) % 1;
            const r = p.big ? 16 : 10;
            return (
              <g key={i} transform={`translate(${xy[0]} ${xy[1]})`} opacity={clamp(s * 2)}>
                <circle r={r + 40 * pulse} fill="none" stroke={acc} strokeWidth={3} opacity={(1 - pulse) * 0.8} />
                <circle r={r * s} fill={acc} stroke={T.dark ? "#000" : "#fff"} strokeWidth={3} />
              </g>
            );
          })}
        </g>
      </svg>
      {(o.points ?? []).map((p, i) => {
        const xy = proj([p.lon, p.lat]); if (!xy || !p.label) return null;
        const s = spring({ frame: f - 16 - i * 6, fps, config: { damping: 16, stiffness: 120 } });
        return (
          <div key={i} style={{ position: "absolute", left: xy[0] + 26, top: xy[1] - 26, opacity: clamp(s * 1.5), transform: `translateX(${(1 - s) * -20}px)`, fontFamily: F.sans, fontWeight: 700, fontSize: p.big ? 38 : 28, color: "#FFFFFF", background: "#0B0D12D9", padding: "6px 16px", borderRadius: 8, whiteSpace: "nowrap" }}>{p.label}</div>
        );
      })}
      {o.title ? <div style={{ position: "absolute", left: 110, top: 136, padding: "12px 22px", background: T.dark ? "#00000059" : "#FFFFFFB3", borderRadius: 10 }}><Tag at={4} color={acc} size={30}>{o.title}</Tag></div> : null}
      {o.note ? <div style={{ position: "absolute", left: 130, bottom: 150, fontFamily: F.mono, fontSize: 22, letterSpacing: "0.12em", textTransform: "uppercase", color: T.dim, opacity: clamp((f - 30) / 15) }}>{o.note}</div> : null}
    </div>
  );
};

/* ------------------------------------------------------------------ */
/* Process flow: icon stations connected by drawing lines              */
/* ------------------------------------------------------------------ */

export type FlowOverlay = { type: "flow"; title?: string; steps: { icon: IconName; label: string }[] };
export type IconName = "river" | "dredger" | "ship" | "truck" | "mixer" | "building" | "glass" | "chip" | "road" | "recycle" | "rock" | "mine" | "wave" | "sand" | "hourglass" | "phone" | "drawer" | "home" | "shredder" | "fire" | "magnet" | "gold" | "wrench" | "store" | "dump" | "eye" | "ad" | "money" | "heart" | "brain" | "bell" | "star" | "hand" | "share" | "repeat" | "wheat" | "factory" | "warehouse" | "cart" | "fuel" | "sun" | "tractor" | "bin" | "rain" | "well" | "drop" | "layers";

const ICONS: Record<IconName, React.ReactNode> = {
  river: <><path d="M10 30 C30 20 40 40 60 30 S90 20 90 20" /><path d="M10 55 C30 45 40 65 60 55 S90 45 90 45" /><path d="M10 80 C30 70 40 90 60 80 S90 70 90 70" /></>,
  dredger: <><path d="M8 70 L92 70 L82 86 L18 86 Z" /><path d="M30 70 L30 46 L58 46 L58 70" /><path d="M58 52 L86 26" /><path d="M86 26 L92 40 L80 44 Z" /><path d="M38 46 L38 34 L48 34 L48 46" /></>,
  ship: <><path d="M6 64 L94 64 L80 84 L18 84 Z" /><rect x="22" y="44" width="18" height="20" /><rect x="42" y="44" width="18" height="20" /><rect x="62" y="44" width="18" height="20" /><path d="M70 44 L70 26 L82 26 L82 44" /></>,
  truck: <><path d="M8 30 L60 30 L60 72 L8 72 Z" /><path d="M60 44 L80 44 L92 58 L92 72 L60 72" /><circle cx="26" cy="76" r="8" /><circle cx="76" cy="76" r="8" /><path d="M14 30 L24 18 L50 18 L58 30" /></>,
  mixer: <><path d="M14 30 L70 22 L84 52 L28 66 Z" /><path d="M28 66 L24 80 L80 80 L84 52" /><circle cx="32" cy="84" r="7" /><circle cx="72" cy="84" r="7" /><path d="M36 40 L66 34 M40 52 L72 46" /></>,
  building: <><rect x="16" y="20" width="34" height="68" /><rect x="50" y="40" width="34" height="48" /><path d="M24 30h6M36 30h6M24 42h6M36 42h6M24 54h6M36 54h6M24 66h6M36 66h6M58 50h6M70 50h6M58 62h6M70 62h6M58 74h6M70 74h6" /></>,
  glass: <><path d="M30 12 L70 12 L64 54 C62 64 38 64 36 54 Z" /><path d="M50 62 L50 84" /><path d="M34 88 L66 88" /><path d="M38 24 L62 24" /></>,
  chip: <><rect x="26" y="26" width="48" height="48" rx="4" /><rect x="38" y="38" width="24" height="24" /><path d="M34 14v12M50 14v12M66 14v12M34 74v12M50 74v12M66 74v12M14 34h12M14 50h12M14 66h12M74 34h12M74 50h12M74 66h12" /></>,
  road: <><path d="M36 10 L14 90" /><path d="M64 10 L86 90" /><path d="M50 14 L50 28 M50 42 L50 58 M50 72 L50 88" /></>,
  recycle: <><path d="M50 14 L66 40 L56 40" /><path d="M66 40 L76 30" /><path d="M84 66 L54 66 L58 58" /><path d="M54 66 L58 78" /><path d="M16 66 L32 40 L38 48" /><path d="M32 40 L20 40" /><path d="M50 14 L34 40 M84 66 L68 40 M16 66 L36 86 L64 86 L84 66" /></>,
  rock: <><path d="M14 74 L28 40 L52 28 L78 38 L88 70 L70 84 L30 84 Z" /><path d="M28 40 L44 58 L52 28 M44 58 L78 38 M44 58 L30 84 M44 58 L70 84" /></>,
  mine: <><path d="M10 84 L36 44 L52 64 L64 50 L90 84 Z" /><path d="M24 30 L46 14 M30 20 L40 34" /></>,
  wave: <><path d="M8 60 C22 40 34 40 46 60 S70 80 84 56" /><path d="M84 56 C88 48 94 46 94 46" /><path d="M8 80 L94 80" /><path d="M20 40 C30 26 44 24 52 34" /></>,
  sand: <><circle cx="30" cy="60" r="6" /><circle cx="50" cy="48" r="6" /><circle cx="68" cy="62" r="6" /><circle cx="42" cy="72" r="5" /><circle cx="60" cy="78" r="5" /><circle cx="24" cy="80" r="4" /><circle cx="78" cy="80" r="4" /></>,
  phone: <><rect x="30" y="8" width="40" height="84" rx="7" /><path d="M44 16h12" /><circle cx="50" cy="82" r="3" /><rect x="35" y="24" width="30" height="48" /></>,
  drawer: <><rect x="12" y="20" width="76" height="66" rx="3" /><path d="M12 52h76" /><path d="M42 36h16M42 68h16" /><rect x="24" y="8" width="20" height="12" /></>,
  home: <><path d="M12 48 L50 16 L88 48" /><path d="M22 40 L22 86 L78 86 L78 40" /><rect x="42" y="60" width="16" height="26" /></>,
  shredder: <><rect x="14" y="16" width="72" height="34" rx="3" /><path d="M14 50 L86 50" /><path d="M24 50v36M36 50v30M48 50v38M60 50v28M72 50v34" /><path d="M30 28h40" /></>,
  fire: <><path d="M50 10 C62 30 76 40 74 62 C72 80 60 90 50 90 C40 90 26 80 26 62 C26 46 38 40 40 26 C46 34 48 40 50 10 Z" /><path d="M50 56 C56 64 58 70 56 78 C54 84 46 84 44 78 C42 70 46 66 50 56 Z" /></>,
  magnet: <><path d="M22 18 L22 54 C22 72 34 84 50 84 C66 84 78 72 78 54 L78 18" /><path d="M38 18 L38 54 C38 62 44 68 50 68 C56 68 62 62 62 54 L62 18" /><path d="M22 18h16M62 18h16M22 30h16M62 30h16" /></>,
  gold: <><path d="M10 82 L22 62 L48 62 L58 82 Z" /><path d="M42 82 L54 62 L80 62 L90 82 Z" /><path d="M26 58 L38 38 L64 38 L74 58 Z" /><path d="M70 14 L72 22 L80 24 L72 26 L70 34 L68 26 L60 24 L68 22 Z" /></>,
  wrench: <><path d="M62 12 C50 12 42 22 44 34 L14 64 C10 68 10 76 14 80 C18 84 26 84 30 80 L60 50 C72 52 82 44 82 32 L72 40 L62 36 L60 26 L70 16 C68 13 65 12 62 12 Z" /></>,
  store: <><path d="M12 36 L20 14 L80 14 L88 36 Z" /><path d="M12 36 C12 44 24 44 26 36 C28 44 40 44 42 36 C44 44 56 44 58 36 C60 44 72 44 74 36 C76 44 88 44 88 36" /><path d="M18 44 L18 86 L82 86 L82 44" /><rect x="40" y="60" width="20" height="26" /></>,
  dump: <><path d="M8 86 L22 58 L34 66 L46 44 L60 60 L72 50 L92 86 Z" /><rect x="40" y="30" width="12" height="18" rx="2" transform="rotate(-20 46 39)" /><rect x="60" y="34" width="16" height="10" transform="rotate(15 68 39)" /><path d="M26 24 C30 18 34 18 36 12 M70 22 C74 16 78 16 80 10" /></>,
  eye: <><path d="M8 50 C24 24 76 24 92 50 C76 76 24 76 8 50 Z" /><circle cx="50" cy="50" r="14" /><circle cx="50" cy="50" r="4" /></>,
  ad: <><path d="M14 40 L14 60 L30 60 L66 80 L66 20 L30 40 Z" /><path d="M30 60 L36 84 L46 84 L42 62" /><path d="M76 38 C82 44 82 56 76 62 M84 30 C94 42 94 58 84 70" /></>,
  money: <><rect x="10" y="28" width="80" height="44" rx="4" /><circle cx="50" cy="50" r="12" /><path d="M20 38 C24 38 26 36 26 32 M80 38 C76 38 74 36 74 32 M20 62 C24 62 26 64 26 68 M80 62 C76 62 74 64 74 68" /></>,
  heart: <><path d="M50 84 C20 62 10 48 10 34 C10 22 20 14 31 14 C40 14 46 20 50 28 C54 20 60 14 69 14 C80 14 90 22 90 34 C90 48 80 62 50 84 Z" /></>,
  brain: <><path d="M48 16 C38 10 24 16 24 28 C14 30 10 42 16 50 C10 58 14 72 26 74 C28 86 42 90 48 82 Z" /><path d="M52 16 C62 10 76 16 76 28 C86 30 90 42 84 50 C90 58 86 72 74 74 C72 86 58 90 52 82 Z" /><path d="M30 40 C36 40 38 46 38 50 M70 40 C64 40 62 46 62 50 M28 60 C34 58 40 62 40 66 M72 60 C66 58 60 62 60 66" /></>,
  bell: <><path d="M26 70 L26 46 C26 30 36 20 50 20 C64 20 74 30 74 46 L74 70 L82 78 L18 78 Z" /><path d="M42 84 C44 90 56 90 58 84" /><path d="M50 12 L50 20" /></>,
  star: <><path d="M50 10 L61 37 L90 39 L67 57 L75 86 L50 70 L25 86 L33 57 L10 39 L39 37 Z" /></>,
  hand: <><path d="M38 52 L38 20 C38 14 46 14 46 20 L46 46 M46 40 C46 34 54 34 54 40 L54 46 M54 42 C54 36 62 36 62 42 L62 48 M62 46 C62 40 70 40 70 46 L70 64 C70 80 60 90 46 90 C36 90 30 84 26 76 L16 58 C14 52 20 48 26 52 L38 62" /></>,
  share: <><circle cx="26" cy="50" r="10" /><circle cx="74" cy="24" r="10" /><circle cx="74" cy="76" r="10" /><path d="M35 45 L65 29 M35 55 L65 71" /></>,
  repeat: <><path d="M20 44 C20 28 32 20 46 20 L76 20" /><path d="M66 10 L78 20 L66 30" /><path d="M80 56 C80 72 68 80 54 80 L24 80" /><path d="M34 70 L22 80 L34 90" /></>,
  wheat: <><path d="M50 92 L50 22" /><path d="M50 30 C40 26 36 18 38 10 C46 14 50 20 50 30 Z M50 30 C60 26 64 18 62 10 C54 14 50 20 50 30 Z" /><path d="M50 50 C40 46 34 38 36 30 C44 34 50 40 50 50 Z M50 50 C60 46 66 38 64 30 C56 34 50 40 50 50 Z" /><path d="M50 70 C40 66 34 58 36 50 C44 54 50 60 50 70 Z M50 70 C60 66 66 58 64 50 C56 54 50 60 50 70 Z" /></>,
  factory: <><path d="M10 88 L10 44 L32 56 L32 44 L54 56 L54 44 L76 56 L76 20 L90 20 L90 88 Z" /><path d="M22 72h8M42 72h8M62 72h8" /></>,
  warehouse: <><path d="M8 40 L50 14 L92 40 L92 88 L8 88 Z" /><rect x="28" y="54" width="44" height="34" /><path d="M28 64h44M28 74h44" /></>,
  cart: <><path d="M6 16 L20 16 L30 64 L80 64 L90 30 L24 30" /><circle cx="36" cy="80" r="7" /><circle cx="74" cy="80" r="7" /><path d="M40 42h40M44 52h32" /></>,
  fuel: <><path d="M50 10 C38 30 24 44 24 62 C24 78 36 90 50 90 C64 90 76 78 76 62 C76 44 62 30 50 10 Z" /><path d="M40 66 C40 74 46 78 52 78" /></>,
  sun: <><circle cx="50" cy="50" r="18" /><path d="M50 8v14M50 78v14M8 50h14M78 50h14M20 20l10 10M70 70l10 10M80 20L70 30M30 70L20 80" /></>,
  tractor: <><circle cx="30" cy="68" r="20" /><circle cx="30" cy="68" r="6" /><circle cx="78" cy="76" r="12" /><path d="M48 62 L48 30 L72 30 L80 56 L90 58 L90 72" /><path d="M48 30 L36 30 L36 48" /><path d="M58 30 L58 18" /></>,
  bin: <><path d="M18 26 L82 26" /><path d="M40 26 L42 14 L58 14 L60 26" /><path d="M24 26 L30 90 L70 90 L76 26" /><path d="M42 40 L44 78M58 40 L56 78" /></>,
  rain: <><path d="M26 52 C12 52 10 34 24 32 C26 18 46 14 52 26 C62 18 78 24 76 38 C88 40 88 52 76 52 Z" /><path d="M34 64 L30 76M50 64 L46 76M66 64 L62 76M42 80 L38 92M58 80 L54 92" /></>,
  well: <><path d="M20 40 L80 40 M24 40 L24 90 M76 40 L76 90 M20 90 L80 90" /><path d="M50 40 L50 60" /><path d="M30 26 L50 12 L70 26 Z" /><path d="M44 60 h12 v10 h-12 Z" /><path d="M24 76 C40 72 60 80 76 76" /></>,
  drop: <><path d="M50 10 C38 32 24 46 24 62 C24 78 36 90 50 90 C64 90 76 78 76 62 C76 46 62 32 50 10 Z" /><path d="M36 64 C36 74 42 80 50 80" /></>,
  layers: <><path d="M8 30 C30 22 70 38 92 30" /><path d="M8 48 C30 40 70 56 92 48" /><path d="M8 66 C30 58 70 74 92 66" /><circle cx="30" cy="57" r="3" /><circle cx="50" cy="59" r="3" /><circle cx="70" cy="56" r="3" /><circle cx="40" cy="76" r="3" /><circle cx="62" cy="77" r="3" /><path d="M8 84 L92 84" /></>,
  hourglass: <><path d="M24 10 L76 10 M24 90 L76 90" /><path d="M30 10 C30 40 70 40 70 10 M30 90 C30 60 70 60 70 90" /><path d="M30 10 C30 36 48 46 50 50 C52 46 70 36 70 10" /><path d="M50 50 L50 78" /></>,
};

export const FlowScene: React.FC<{ o: FlowOverlay; dur: number }> = ({ o, dur }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const T = useTh();
  const ACC = T.dark ? STYLE.accent : T.amber;
  const n = o.steps.length;
  const W = 1660, x0 = 130, gap = W / n;
  const step = Math.min(26, Math.max(10, Math.round((dur * 0.55) / n)));
  const R = 128;
  return (
    <div style={{ position: "absolute", inset: 0 }}>
      {o.title ? <div style={{ position: "absolute", left: 130, top: 190 }}><Tag at={4} color={ACC} size={30}>{o.title}</Tag></div> : null}
      <svg viewBox="0 0 1920 1080" width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {o.steps.slice(0, -1).map((_, i) => {
          const a = x0 + gap * (i + 0.5) + R + 14, b = x0 + gap * (i + 1.5) - R - 14;
          const k = Easing.bezier(0.6, 0, 0.3, 1)(clamp((f - 10 - i * step - step * 0.6) / (step * 0.8)));
          return (
            <g key={i}>
              <line x1={a} y1={520} x2={mix(a, b, k)} y2={520} stroke={ACC} strokeWidth={5} strokeLinecap="round" strokeDasharray="1 14" />
              {k > 0.95 ? <path d={`M${b - 16},${508} L${b},${520} L${b - 16},${532}`} fill="none" stroke={ACC} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" /> : null}
            </g>
          );
        })}
        {o.steps.map((s, i) => {
          const cx = x0 + gap * (i + 0.5);
          const sp = spring({ frame: f - 10 - i * step, fps, config: { damping: 13, stiffness: 140 } });
          const draw = clamp((f - 12 - i * step) / 22);
          return (
            <g key={i} transform={`translate(${cx} 520) scale(${0.6 + 0.4 * sp})`} opacity={clamp(sp * 2)}>
              <circle r={R} fill={T.panel} stroke={T.line} strokeWidth={3} />
              <circle r={R} fill="none" stroke={ACC} strokeWidth={6} strokeDasharray={2 * Math.PI * R} strokeDashoffset={2 * Math.PI * R * (1 - draw)} transform="rotate(-90)" strokeLinecap="round" />
              <g transform="translate(-72 -72) scale(1.44)" fill="none" stroke={T.fg} strokeWidth={4.5} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={600} strokeDashoffset={600 * (1 - draw)}>{ICONS[s.icon]}</g>
            </g>
          );
        })}
      </svg>
      {o.steps.map((s, i) => {
        const cx = x0 + gap * (i + 0.5);
        const sp = spring({ frame: f - 18 - i * step, fps, config: { damping: 16, stiffness: 120 } });
        return (
          <div key={i} style={{ position: "absolute", left: cx - gap / 2, width: gap, top: 520 + R + 34, textAlign: "center", opacity: clamp(sp * 1.5), transform: `translateY(${(1 - sp) * 20}px)` }}>
            <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.2em", color: ACC, marginBottom: 8 }}>{String(i + 1).padStart(2, "0")}</div>
            <div style={{ fontFamily: F.serif, fontWeight: 700, fontSize: 44 * DS, lineHeight: 1.05, color: T.fg, textTransform: STYLE.displayUpper ? "uppercase" : undefined }}>{s.label}</div>
          </div>
        );
      })}
    </div>
  );
};

export { interpolate };
