import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { F } from "./theme";

/** Split face: left half untouched "REAL", right half glitched "FAKE?" */
export const Thumb: React.FC = () => {
  const src = staticFile("thumb_face.jpg");
  const face: React.CSSProperties = { position: "absolute", width: 1920 * 1.25, height: 1072 * 1.25, left: -470, top: -110, objectFit: "cover" };
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <AbsoluteFill style={{ clipPath: "inset(0 50% 0 0)" }}>
        <Img src={src} style={{ ...face, filter: "saturate(1.2) contrast(1.1) brightness(1.1)" }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ clipPath: "inset(0 0 0 50%)" }}>
        <Img src={src} style={{ ...face, left: 470, filter: "saturate(1.5) hue-rotate(150deg) contrast(1.2) brightness(1.35)" }} />
        <Img src={src} style={{ ...face, left: 470 + 26, mixBlendMode: "screen", opacity: 0.6, filter: "grayscale(1) sepia(1) hue-rotate(-50deg) saturate(6) brightness(1.2)" }} />
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} style={{ position: "absolute", left: 960, width: 960, top: 90 + i * 140 + (i % 3) * 13, height: 14 + (i % 4) * 8, overflow: "hidden" }}>
            <Img src={src} style={{ ...face, top: -110 - (90 + i * 140 + (i % 3) * 13), left: 470 - 960 + (i % 2 ? 60 : -45), filter: "saturate(2) hue-rotate(160deg) brightness(1.4)" }} />
          </div>
        ))}
        <AbsoluteFill style={{ background: "repeating-linear-gradient(0deg, #00FFE014 0 3px, transparent 3px 7px)" }} />
      </AbsoluteFill>
      <div style={{ position: "absolute", left: 950, top: 0, width: 20, height: 1080, background: "#FFE14D" }} />
      <div style={{ position: "absolute", left: 50, top: 40, background: "#18C964", color: "#0B0F16", fontFamily: F.sans, fontWeight: 900, fontSize: 80, padding: "6px 28px", borderRadius: 14 }}>REAL</div>
      <div style={{ position: "absolute", right: 50, top: 40, background: "#FF2D2D", color: "#FFFFFF", fontFamily: F.sans, fontWeight: 900, fontSize: 80, padding: "6px 28px", borderRadius: 14 }}>FAKE?</div>
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 250, background: "#0B0F16", display: "grid", placeItems: "center" }}>
        <div style={{ fontFamily: F.sans, fontWeight: 900, fontSize: 170, color: "#FFFFFF", letterSpacing: "-0.02em", lineHeight: 1 }}>WHO IS <span style={{ color: "#FFE14D" }}>REAL?</span></div>
      </div>
    </AbsoluteFill>
  );
};
