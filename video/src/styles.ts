import { getInputProps } from "remotion";
import spec from "./spec.json";

/** A font family shipped in public/fonts as `${file}-latin-${weight}-normal.woff2`. */
export type FontDef = { family: string; file: string; weights: number[]; italic?: number[] };

export type CaptionStyle = "box" | "bar" | "shadow" | "highlight" | "pill" | "edge";

export type Style = {
  name: string;
  label: string;
  bestFor: string;
  display: FontDef;            // headings, big numbers, quotes (F.serif slot)
  body: FontDef;               // labels, captions, UI (F.sans slot)
  displayScale: number;        // wide/condensed display fonts need resizing to fit layouts
  displayUpper?: boolean;      // force uppercase display text (condensed poster faces)
  displayItalicOk?: boolean;   // false → never fake an italic
  accent: string;              // act tags, intro highlights
  looks: string[];             // graphic-scene theme rotation (themes.tsx keys)
  intro: string;               // theme for intro card
  endcard: string;             // theme behind end card blobs
  trans: ("bar" | "iris" | "rise" | "split")[];
  caption: CaptionStyle;
  captionFg: string;
  captionBg: string;
  grade: string;               // CSS filter on footage/photos
  tint?: string;               // optional colour wash over footage (mix-blend overlay)
  grain: number;
  vignette: number;            // 0..1 edge darkness
  music: string;               // mood hint for picking the bed
};

const FD = {
  playfair: { family: "Playfair Display", file: "playfair-display", weights: [400, 700], italic: [400] },
  inter: { family: "Inter", file: "inter", weights: [400, 500, 600, 700] },
  cormorant: { family: "Cormorant Garamond", file: "cormorant-garamond", weights: [500, 600, 700], italic: [400, 700] },
  plexSans: { family: "IBM Plex Sans", file: "ibm-plex-sans", weights: [400, 500, 600, 700] },
  plexMono: { family: "IBM Plex Mono", file: "ibm-plex-mono", weights: [400, 500, 600, 700] },
  anton: { family: "Anton", file: "anton", weights: [400] },
  manrope: { family: "Manrope", file: "manrope", weights: [400, 500, 600, 700, 800] },
  grotesk: { family: "Space Grotesk", file: "space-grotesk", weights: [400, 500, 600, 700] },
  jet: { family: "JetBrains Mono", file: "jetbrains-mono", weights: [400, 500, 600, 700, 800] },
  fraunces: { family: "Fraunces", file: "fraunces", weights: [400, 600, 700, 800, 900], italic: [400, 700] },
  work: { family: "Work Sans", file: "work-sans", weights: [400, 500, 600, 700, 800, 900] },
  archivo: { family: "Archivo Black", file: "archivo-black", weights: [400] },
  dmSerif: { family: "DM Serif Display", file: "dm-serif-display", weights: [400], italic: [400] },
  dmSans: { family: "DM Sans", file: "dm-sans", weights: [400, 500, 600, 700, 800, 900] },
  unbounded: { family: "Unbounded", file: "unbounded", weights: [400, 600, 700, 800, 900] },
  sora: { family: "Sora", file: "sora", weights: [400, 500, 600, 700, 800] },
} satisfies Record<string, FontDef>;

export const STYLES: Record<string, Style> = {
  editorial: {
    name: "editorial", label: "Editorial", bestFor: "general documentaries, society, housing, work",
    display: FD.playfair, body: FD.inter, displayScale: 1, displayItalicOk: true,
    accent: "#FFB547", looks: ["paper", "volt", "sun", "coral", "mint", "night"], intro: "night", endcard: "night",
    trans: ["bar", "iris", "rise", "split"], caption: "box", captionFg: "#F4ECDD", captionBg: "#05070CCC",
    grade: "contrast(1.02)", grain: 0.06, vignette: 0.33, music: "hopeful cinematic piano/strings",
  },
  noir: {
    name: "noir", label: "Documentary Noir", bestFor: "true crime, scams, mysteries, investigations, dark history",
    display: FD.cormorant, body: FD.plexSans, displayScale: 1.08, displayItalicOk: true,
    accent: "#E23B3B", looks: ["blood", "ash", "night", "blood", "ink"], intro: "ink", endcard: "ink",
    trans: ["iris", "split", "rise"], caption: "shadow", captionFg: "#F1EEE8", captionBg: "transparent",
    grade: "saturate(0.55) contrast(1.15) brightness(0.92)", tint: "#3A0A0A", grain: 0.11, vignette: 0.6,
    music: "dark low drones, pulses, sparse piano",
  },
  bold: {
    name: "bold", label: "Bold Explainer", bestFor: "top-10 lists, fast explainers, 'why X' videos, shorts",
    display: FD.anton, body: FD.manrope, displayScale: 1.12, displayUpper: true,
    accent: "#FFE14D", looks: ["sun", "coral", "volt", "mint", "pop"], intro: "pop", endcard: "night",
    trans: ["bar", "split", "bar", "rise"], caption: "highlight", captionFg: "#111111", captionBg: "#FFE14D",
    grade: "saturate(1.25) contrast(1.08)", grain: 0.04, vignette: 0.2, music: "upbeat percussive, claps, bright synths",
  },
  tech: {
    name: "tech", label: "Tech Signal", bestFor: "AI, tech, internet, cyber, startups, the future of work",
    display: FD.grotesk, body: FD.jet, displayScale: 1,
    accent: "#38E1FF", looks: ["grid", "volt", "night", "grid", "mint"], intro: "grid", endcard: "grid",
    trans: ["rise", "bar", "split"], caption: "edge", captionFg: "#E8F7FF", captionBg: "#04121BD9",
    grade: "saturate(0.9) contrast(1.08) hue-rotate(-6deg)", tint: "#06263A", grain: 0.05, vignette: 0.35,
    music: "electronic pulse, arpeggiated synths, minimal",
  },
  warm: {
    name: "warm", label: "Warm Stories", bestFor: "human stories, culture, history, food, family, travel",
    display: FD.fraunces, body: FD.work, displayScale: 1, displayItalicOk: true,
    accent: "#FFD9A0", looks: ["cream", "clay", "paper", "mint", "clay"], intro: "clay", endcard: "cream",
    trans: ["iris", "rise", "bar"], caption: "pill", captionFg: "#2A1D14", captionBg: "#FFF3E3EE",
    grade: "sepia(0.18) saturate(1.1) contrast(1.02)", grain: 0.08, vignette: 0.3, music: "acoustic guitar, warm strings",
  },
  news: {
    name: "news", label: "News Desk", bestFor: "current affairs, politics explainers, economy, breaking topics",
    display: FD.archivo, body: FD.plexSans, displayScale: 0.92,
    accent: "#E3262E", looks: ["paper", "press", "night", "volt", "press"], intro: "press", endcard: "night",
    trans: ["bar", "bar", "split"], caption: "bar", captionFg: "#FFFFFF", captionBg: "#0B0F16F0",
    grade: "contrast(1.06) saturate(1.02)", grain: 0.03, vignette: 0.18, music: "tense news underscore, ticking pulses",
  },
  finance: {
    name: "finance", label: "Money Matters", bestFor: "money, markets, salaries, cost of living, business stories",
    display: FD.dmSerif, body: FD.dmSans, displayScale: 1.04, displayItalicOk: true,
    accent: "#E9C46A", looks: ["forest", "paper", "night", "forest", "cream"], intro: "forest", endcard: "forest",
    trans: ["rise", "bar", "iris"], caption: "box", captionFg: "#F6F1E4", captionBg: "#06130ECC",
    grade: "contrast(1.05) saturate(1.05) sepia(0.06)", grain: 0.05, vignette: 0.3, music: "confident corporate, light piano",
  },
  cosmic: {
    name: "cosmic", label: "Cinematic Future", bestFor: "space, science, climate, big-picture 'what happens next' films",
    display: FD.unbounded, body: FD.sora, displayScale: 0.8,
    accent: "#7CF0DD", looks: ["deep", "night", "volt", "deep", "mint"], intro: "deep", endcard: "deep",
    trans: ["iris", "rise", "split"], caption: "shadow", captionFg: "#FFFFFF", captionBg: "transparent",
    grade: "contrast(1.1) saturate(1.15)", tint: "#0B1E3A", grain: 0.05, vignette: 0.45, music: "epic ambient, swelling pads",
  },
};

const pick = (): string => {
  let p: { style?: string } = {};
  try { p = getInputProps() as { style?: string }; } catch { /* not in render */ }
  return p.style ?? (spec as { style?: string }).style ?? "editorial";
};
export const STYLE: Style = STYLES[pick()] ?? STYLES.editorial;
export const STYLE_NAMES = Object.keys(STYLES);
