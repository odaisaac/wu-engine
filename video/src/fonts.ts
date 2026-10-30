import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

const f = (family: string, file: string, weight: string, style = "normal") =>
  loadFont({ family, url: staticFile(`fonts/${file}`), weight, style });

export const fontsReady = Promise.all([
  f("Playfair Display", "playfair-display-latin-400-normal.woff2", "400"),
  f("Playfair Display", "playfair-display-latin-700-normal.woff2", "700"),
  f("Playfair Display", "playfair-display-latin-400-italic.woff2", "400", "italic"),
  f("Inter", "inter-latin-400-normal.woff2", "400"),
  f("Inter", "inter-latin-500-normal.woff2", "500"),
  f("Inter", "inter-latin-600-normal.woff2", "600"),
  f("Inter", "inter-latin-700-normal.woff2", "700"),
]);
