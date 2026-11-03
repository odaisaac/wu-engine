import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { F } from "./theme";

/** Generic hero thumbnail: photo on one side, heavy headline on the other. */
export type ThumbHeroProps = { img: string; imgX?: number; imgScale?: number; small: string; big: string; chip?: string; accent?: string; grade?: string; bigSize?: number };
export const ThumbHero: React.FC<ThumbHeroProps> = ({ img, imgX = -80, imgScale = 1.25, small, big, chip, accent = "#FFB13B", grade = "saturate(1.25) contrast(1.12) brightness(1.05)", bigSize = 330 }) => (
  <AbsoluteFill style={{ background: "#0B0705", overflow: "hidden" }}>
    <Img src={staticFile(img)} style={{ position: "absolute", width: 1920 * imgScale, height: 1080 * imgScale, left: imgX, top: -(1080 * (imgScale - 1)) / 2, objectFit: "cover", filter: grade }} />
    <AbsoluteFill style={{ background: "linear-gradient(90deg, transparent 0%, transparent 38%, #0B0705D9 58%, #0B0705 78%)" }} />
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 30% 60%, transparent 40%, #00000088 100%)" }} />
    <div style={{ position: "absolute", right: 70, top: 0, bottom: 0, width: 900, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "flex-end", textAlign: "right" }}>
      <div style={{ fontFamily: F.serif, fontWeight: 900, fontSize: 150, lineHeight: 0.95, color: "#FFFFFF", letterSpacing: "-0.02em", textShadow: "0 8px 40px #000" }}>{small}</div>
      <div style={{ fontFamily: F.serif, fontWeight: 900, fontSize: bigSize, lineHeight: 0.9, color: accent, letterSpacing: "-0.03em", textShadow: "0 10px 50px #000" }}>{big}</div>
      {chip ? <div style={{ marginTop: 34, background: "#FFFFFF", color: "#0B0705", fontFamily: F.sans, fontWeight: 900, fontSize: 64, padding: "10px 34px", borderRadius: 14, letterSpacing: "0.04em" }}>{chip}</div> : null}
    </div>
  </AbsoluteFill>
);
