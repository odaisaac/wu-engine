import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";
import { STYLE, FontDef } from "./styles";

const nearest = (ws: number[], w: number) => ws.reduce((a, b) => (Math.abs(b - w) < Math.abs(a - w) ? b : a));
/** Register every weight 100–900 against the nearest real file, so the browser never fakes bold. */
const load = (d: FontDef) => {
  const jobs: Promise<void>[] = [];
  for (let w = 100; w <= 900; w += 100) {
    jobs.push(loadFont({ family: d.family, url: staticFile(`fonts/${d.file}-latin-${nearest(d.weights, w)}-normal.woff2`), weight: String(w), style: "normal" }));
    if (d.italic?.length) jobs.push(loadFont({ family: d.family, url: staticFile(`fonts/${d.file}-latin-${nearest(d.italic, w)}-italic.woff2`), weight: String(w), style: "italic" }));
  }
  return Promise.all(jobs);
};
export const fontsReady = Promise.all([load(STYLE.display), load(STYLE.body), ...(STYLE.mono ? [load(STYLE.mono)] : [])]);
