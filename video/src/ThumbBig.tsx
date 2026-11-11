import React, { useEffect, useState } from "react";
import { AbsoluteFill, Img, staticFile, delayRender, continueRender } from "remotion";

/** "One giant word" thumbnail: full-bleed picture with the subject on one side, a small lead-in line,
 *  one huge coloured word, a pill underneath and the channel badge. Built to read at phone size. */
export type ThumbBigProps = { img: string; small?: string; big: string; pill?: string; side?: "right" | "left"; bigColor?: string; pillBg?: string; bigSize?: number; shade?: number; badge?: boolean; tilt?: number };
const useFace = (name: string, file: string, weight = "400") => {
  const [h] = useState(() => delayRender(name));
  useEffect(() => { const f = new FontFace(name, `url(${staticFile(file)})`, { weight }); f.load().then((ff) => { document.fonts.add(ff); continueRender(h); }).catch(() => continueRender(h)); }, [h]);
};
export const ThumbBig: React.FC<ThumbBigProps> = ({ img, small, big, pill, side = "right", bigColor = "#FFD23F", pillBg = "#E63946", bigSize, shade = 0.5, badge = true, tilt = -3 }) => {
  useFace("ThumbAnton", "fonts/anton-latin-400-normal.woff2");
  useFace("ThumbInter", "fonts/inter-latin-700-normal.woff2", "700");
  const R = side === "right";
  const W = 1120;                                                       // text column
  const longest = Math.max(...big.split("\n").map((l) => l.length));
  const size = bigSize ?? Math.min(360, Math.floor(W / (0.5 * Math.max(3, longest))));
  const caps: React.CSSProperties = { fontFamily: "ThumbAnton", textTransform: "uppercase", lineHeight: 0.92, WebkitTextStroke: "10px #000", paintOrder: "stroke fill", textShadow: "0 12px 0 #000, 0 20px 44px #000A", whiteSpace: "pre" };
  return (
    <AbsoluteFill style={{ background: "#111", overflow: "hidden" }}>
      <Img src={staticFile(img)} style={{ position: "absolute", inset: 0, width: 1920, height: 1080, objectFit: "cover" }} />
      <AbsoluteFill style={{ opacity: shade, background: `linear-gradient(${R ? 90 : 270}deg, transparent 42%, #000000B0 78%, #000000D0 100%)` }} />
      {badge ? (
        <div style={{ position: "absolute", [R ? "left" : "right"]: 34, top: 30, display: "flex", alignItems: "center", gap: 18, background: "#111", border: "6px solid #fff", borderRadius: 24, padding: "12px 28px 12px 14px" }}>
          <Img src={staticFile("logo.png")} style={{ width: 88, height: 88, borderRadius: 44 }} />
          <div style={{ fontFamily: "ThumbInter", fontWeight: 700, fontSize: 42, lineHeight: 1, color: "#fff" }}>THE WORLD<br /><span style={{ color: bigColor }}>UNPACKED</span></div>
        </div>
      ) : null}
      <div style={{ position: "absolute", top: 0, bottom: 0, [R ? "right" : "left"]: 60, width: W, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: R ? "flex-end" : "flex-start", transform: `rotate(${tilt}deg)` }}>
        {small ? <div style={{ ...caps, fontSize: Math.min(150, size * 0.46), color: "#fff", WebkitTextStroke: "8px #000" }}>{small}</div> : null}
        <div style={{ ...caps, fontSize: size, color: bigColor, textAlign: R ? "right" : "left" }}>{big}</div>
        {pill ? <div style={{ marginTop: 40, background: pillBg, color: "#fff", fontFamily: "ThumbInter", fontWeight: 700, fontSize: 86, lineHeight: 1, padding: "18px 46px 20px", borderRadius: 999, border: "8px solid #fff", boxShadow: "0 16px 36px #000A", textTransform: "uppercase" }}>{pill}</div> : null}
      </div>
    </AbsoluteFill>
  );
};
