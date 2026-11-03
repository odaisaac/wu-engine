import React from "react";
import { Composition, delayRender, continueRender } from "remotion";
import { Film, TOTAL } from "./Film";
import { fontsReady } from "./fonts";
import { Thumb } from "./Thumb";
import { ThumbHero } from "./ThumbHero";
import { ThumbPop } from "./ThumbPop";

export const RemotionRoot: React.FC = () => {
  const [h] = React.useState(() => delayRender("fonts"));
  React.useEffect(() => { fontsReady.then(() => continueRender(h)); }, [h]);
  return <><Composition id="Film" component={Film} width={1920} height={1080} fps={30} durationInFrames={TOTAL} /><Composition id="Thumb" component={Thumb} width={1920} height={1080} fps={30} durationInFrames={1} /><Composition id="ThumbHero" component={ThumbHero} width={1920} height={1080} fps={30} durationInFrames={1} defaultProps={{ img: "thumb_sand.jpg", small: "WE'RE RUNNING", big: "OUT", chip: "OF SAND" }} /><Composition id="ThumbPop" component={ThumbPop} width={1920} height={1080} fps={30} durationInFrames={1} defaultProps={{ img: "thumb_food4.jpg", top: "WHY SO", hl: "EXPENSIVE?" }} /></>;
};
