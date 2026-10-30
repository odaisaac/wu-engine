import React from "react";
import { Composition, delayRender, continueRender } from "remotion";
import { Film, TOTAL } from "./Film";
import { fontsReady } from "./fonts";
import { Thumb } from "./Thumb";

export const RemotionRoot: React.FC = () => {
  const [h] = React.useState(() => delayRender("fonts"));
  React.useEffect(() => { fontsReady.then(() => continueRender(h)); }, [h]);
  return <><Composition id="Film" component={Film} width={1920} height={1080} fps={30} durationInFrames={TOTAL} /><Composition id="Thumb" component={Thumb} width={1920} height={1080} fps={30} durationInFrames={1} /></>;
};
