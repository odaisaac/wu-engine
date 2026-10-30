import { STYLE } from "./styles";
export const C = {
  ink: "#0A0D14", panel: "#141B27", line: "#2B3647",
  cream: "#F4ECDD", dim: "#9AA6B8",
  amber: "#FFB547", coral: "#FF5E57", teal: "#3DD6C6", blue: "#4C8DFF",
};
/** serif = the style's DISPLAY face, sans = the style's BODY face. */
export const F = {
  serif: `'${STYLE.display.family}', Georgia, serif`,
  sans: `'${STYLE.body.family}', system-ui, sans-serif`,
  mono: STYLE.mono ? `'${STYLE.mono.family}', ui-monospace, monospace` : `'${STYLE.body.family}', system-ui, sans-serif`,
};
export const DS = STYLE.displayScale;
