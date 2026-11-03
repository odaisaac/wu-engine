import React, { useEffect, useState } from "react";
import { AbsoluteFill, Img, staticFile, delayRender, continueRender } from "remotion";

/** Bold "YouTube pop" thumbnail: photo full-bleed, heavy condensed caps, highlight block, sticker. */
export type ThumbPopProps = { img: string; top: string; hl: string; sticker?: string; hlBg?: string; hlFg?: string; stickerBg?: string; size?: number; side?: "right" | "left"; shade?: number };
const useAnton = () => {
  const [h] = useState(() => delayRender("anton"));
  useEffect(() => { const f = new FontFace("AntonPop", `url(${staticFile("fonts/anton-latin-400-normal.woff2")})`); f.load().then((ff) => { document.fonts.add(ff); continueRender(h); }).catch(() => continueRender(h)); }, [h]);
};
export const ThumbPop: React.FC<ThumbPopProps> = ({ img, top, hl, sticker, hlBg = "#FFD23F", hlFg = "#111", stickerBg = "#E63946", size = 210, side = "right", shade = 0.55 }) => {
  useAnton();
  const R = side === "right";
  const txt: React.CSSProperties = { fontFamily: "AntonPop", textTransform: "uppercase", lineHeight: 0.92, letterSpacing: "0.005em" };
  return (
    <AbsoluteFill style={{ background: "#111", overflow: "hidden" }}>
      <Img src={staticFile(img)} style={{ position: "absolute", inset: 0, width: 1920, height: 1080, objectFit: "cover" }} />
      <AbsoluteFill style={{ opacity: shade, background: `linear-gradient(${R ? 90 : 270}deg, transparent 35%, #000000AA 62%, #000000DD 100%)` }} />
      <div style={{ position: "absolute", top: 0, bottom: 0, [R ? "right" : "left"]: 70, width: 1000, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: R ? "flex-end" : "flex-start" }}>
        <div style={{ ...txt, fontSize: size * 0.82, color: "#fff", WebkitTextStroke: "6px #000", paintOrder: "stroke fill", textShadow: "0 10px 30px #000C" }}>{top}</div>
        <div style={{ ...txt, fontSize: size, color: hlFg, background: hlBg, padding: "4px 30px 10px", marginTop: 16, transform: "rotate(-3deg)", boxShadow: "0 18px 40px #000A", borderRadius: 6 }}>{hl}</div>
        {sticker ? <div style={{ ...txt, marginTop: 40, fontSize: 70, color: "#fff", background: stickerBg, padding: "10px 32px 14px", borderRadius: 999, transform: "rotate(2deg)", boxShadow: "0 12px 30px #0009", border: "5px solid #fff" }}>{sticker}</div> : null}
      </div>
    </AbsoluteFill>
  );
};
