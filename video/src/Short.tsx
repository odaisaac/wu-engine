import React, { useEffect, useState } from "react";
import { AbsoluteFill, Img, Sequence, staticFile, useCurrentFrame, delayRender, continueRender, CalculateMetadataFunction } from "remotion";
import { FilmBody, ShortMode } from "./Film";
import { STYLE } from "./styles";
import { clamp } from "./motion";
import timing from "./timing.json";
import spec from "./spec.json";

/**
 * Vertical 1080x1920 Short cut from the current film (same bundle as Film).
 * props.segs = film frame ranges [{from, to}] (built by tools/shorts.py from shot ids).
 * Footage shots fill the frame (centre crop); graphic shots sit as a 16:9 card so charts stay whole.
 * Captions: big word-by-word (1–3 words), current word highlighted, kept inside the platform safe zone.
 */
export type Seg = { from: number; to: number };
export type ShortProps = { segs: Seg[]; hook: string; title?: string; cta?: string; hl?: string };
const END = 75; // end card frames
type T = { id: string; start: number; dur: number; words?: [string, number, number][] };
const TS = (timing as unknown as { shots: T[] }).shots;
const KIND: Record<string, string> = Object.fromEntries((spec as { shots: { id: string; kind?: string }[] }).shots.map((s) => [s.id, s.kind ?? "graphic"]));
const shotAt = (g: number) => TS.find((t) => g >= t.start && g < t.start + t.dur) ?? TS[TS.length - 1];

export const shortMeta: CalculateMetadataFunction<ShortProps> = ({ props }) => ({ durationInFrames: props.segs.reduce((a, s) => a + s.to - s.from, 0) + END });

const useAnton = () => {
  const [h] = useState(() => delayRender("anton-short"));
  useEffect(() => { const f = new FontFace("AntonPop", `url(${staticFile("fonts/anton-latin-400-normal.woff2")})`); f.load().then((ff) => { document.fonts.add(ff); continueRender(h); }).catch(() => continueRender(h)); }, [h]);
};
const A: React.CSSProperties = { fontFamily: "AntonPop", textTransform: "uppercase", lineHeight: 1.0 };

/** One segment: the film, framed by shot kind, plus word captions. */
const Piece: React.FC<{ seg: Seg; hl: string }> = ({ seg, hl }) => {
  const f = useCurrentFrame();
  const g = seg.from + f;
  const t = shotAt(g);
  const fill = ["footage", "photo"].includes(KIND[t.id]);
  const film = (
    <div style={{ position: "absolute", width: 1920, height: 1080, transformOrigin: "0 0", ...(fill
      ? { transform: `translate(${(1080 - 1920 * 1.7778) / 2}px, 0px) scale(1.7778)` }
      : { transform: `translate(0px, 520px) scale(0.5625)` }) }}>
      <ShortMode.Provider value={true}><Sequence from={-seg.from} layout="none"><FilmBody captions={false} /></Sequence></ShortMode.Provider>
    </div>
  );
  // word captions
  const local = g - t.start;
  const W = t.words ?? [];
  let cur = -1;
  for (let i = 0; i < W.length; i++) if (local >= W[i][1] - 1) cur = i;
  let cap: React.ReactNode = null;
  if (cur >= 0 && local <= W[W.length - 1][2] + 8) {
    // group words into 1–3-word bursts that break on punctuation
    const groups: number[][] = []; let gcur: number[] = [];
    W.forEach((w, i) => { gcur.push(i); if (gcur.length === 3 || /[.,!?;:—]$/.test(w[0])) { groups.push(gcur); gcur = []; } });
    if (gcur.length) groups.push(gcur);
    const grp = groups.find((x) => x.includes(cur)) ?? [cur];
    const since = local - W[grp[0]][1];
    const pop = 0.85 + 0.15 * clamp(since / 4);
    cap = (
      <div style={{ position: "absolute", left: 70, right: 150, top: fill ? 1180 : 1260, textAlign: "center", transform: `scale(${pop})` }}>
        {grp.map((i) => (
          <span key={i} style={{ ...A, fontSize: 104, color: i === cur ? hl : "#FFFFFF", WebkitTextStroke: "10px #000", paintOrder: "stroke fill", textShadow: "0 8px 24px #000C", margin: "0 12px", display: "inline-block" }}>
            {W[i][0].replace(/[,;:—]$/, "")}
          </span>
        ))}
      </div>
    );
  }
  return (
    <AbsoluteFill>
      {!fill ? <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, ${STYLE.accent}33, #07080B 70%)` }} /> : null}
      {film}
      {fill ? <AbsoluteFill style={{ background: "linear-gradient(180deg, #000A 0%, transparent 22%, transparent 55%, #000B 100%)" }} /> : null}
      {cap}
    </AbsoluteFill>
  );
};

const Hook: React.FC<{ hook: string; title?: string; hl: string }> = ({ hook, title, hl }) => {
  const f = useCurrentFrame();
  const big = 1 - clamp((f - 95) / 12);           // big hook for ~3 s, then a small persistent title
  const words = hook.split(" ");
  return (
    <>
      <div style={{ position: "absolute", left: 60, right: 60, top: 230, textAlign: "center", opacity: big, transform: `scale(${0.9 + 0.1 * clamp(f / 8)})` }}>
        <div style={{ ...A, fontSize: 112, color: "#fff", WebkitTextStroke: "10px #000", paintOrder: "stroke fill", textShadow: "0 10px 30px #000" }}>
          {words.map((w, i) => <span key={i} style={{ color: i >= words.length - 2 ? hl : "#fff" }}>{w}{i < words.length - 1 ? " " : ""}</span>)}
        </div>
      </div>
      {title ? (
        <div style={{ position: "absolute", left: 0, right: 0, top: 150, textAlign: "center", opacity: 1 - big }}>
          <span style={{ ...A, fontSize: 52, color: "#111", background: hl, padding: "6px 22px", borderRadius: 8 }}>{title}</span>
        </div>
      ) : null}
    </>
  );
};

const End: React.FC<{ cta: string; hl: string }> = ({ cta, hl }) => {
  const f = useCurrentFrame();
  const t = clamp(f / 10);
  return (
    <AbsoluteFill style={{ background: "#07080B", alignItems: "center", justifyContent: "center", opacity: t }}>
      <Img src={staticFile("logo.png")} style={{ width: 300, height: 300, objectFit: "contain", marginBottom: 50, transform: `scale(${0.8 + 0.2 * t})` }} />
      <div style={{ ...A, fontSize: 92, color: "#fff", textAlign: "center", padding: "0 80px" }}>{cta}</div>
      <div style={{ ...A, marginTop: 40, fontSize: 64, color: "#111", background: hl, padding: "10px 36px", borderRadius: 999 }}>▶ The World Unpacked</div>
    </AbsoluteFill>
  );
};

export const Short: React.FC<ShortProps> = ({ segs, hook, title, cta = "Watch the full documentary", hl = "#FFD23F" }) => {
  useAnton();
  let acc = 0;
  const pieces = segs.map((s, i) => { const from = acc; acc += s.to - s.from; return <Sequence key={i} from={from} durationInFrames={s.to - s.from}><Piece seg={s} hl={hl} /></Sequence>; });
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {pieces}
      <Sequence from={0} durationInFrames={acc}><Hook hook={hook} title={title} hl={hl} /></Sequence>
      <Sequence from={acc} durationInFrames={END}><End cta={cta} hl={hl} /></Sequence>
    </AbsoluteFill>
  );
};
