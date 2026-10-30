import React from "react";
import { useCurrentFrame } from "remotion";
import { F } from "./theme";
import { useTh } from "./themes";
import { BarRow, Count, KText, Tag, clamp, useSpr } from "./motion";

export type Overlay =
  | { type: "title"; tag?: string; text: string; hl?: string[] }
  | { type: "kinetic"; text: string; hl?: string[]; sub?: string }
  | { type: "stat"; value: number; prefix?: string; suffix?: string; dec?: number; label: string; from?: number }
  | { type: "compare"; items: { label: string; value: number; prefix?: string; suffix?: string; dec?: number }[]; title?: string }
  | { type: "bars"; title?: string; items: { label: string; value: number; display: string }[]; max?: number }
  | { type: "list"; title?: string; items: string[] }
  | { type: "quote"; text: string; by: string }
  | { type: "lower"; text: string; sub?: string }
  | { type: "none" };

const words = (text: string, hl: string[] = [], color: string): [string, string?][] =>
  text.split(" ").map((w) => [w, hl.some((h) => w.replace(/[^\w%$]/g, "").toLowerCase() === h.toLowerCase()) ? color : undefined]);

/** Text sits on a soft dark panel when over footage; directly on the theme for graphic shots. */
export const OverlayView: React.FC<{ o: Overlay; dur: number; onFootage: boolean }> = ({ o, dur, onFootage }) => {
  const T = useTh();
  const f = useCurrentFrame();
  const at = (p: number) => Math.round(dur * p);
  const box: React.CSSProperties = onFootage ? { position: "absolute", left: 90, top: 110, maxWidth: 1100 } : { position: "absolute", left: 130, right: 130, top: 0, bottom: 120, display: "flex", flexDirection: "column", justifyContent: "center" };
  const acc = T.amber;
  switch (o.type) {
    case "none": return null;
    case "title":
      return <div style={{ ...box, ...(onFootage ? { top: 330 } : {}) }}>{o.tag ? <Tag at={6} color={acc} size={30}>{o.tag}</Tag> : null}<div style={{ height: 22 }} /><KText words={words(o.text, o.hl, acc)} size={onFootage ? 110 : 128} at={12} font="sans" weight={900} stagger={4} /></div>;
    case "kinetic":
      return <div style={box}><KText words={words(o.text, o.hl, acc)} size={onFootage ? 88 : 112} at={at(0.08)} />{o.sub ? <Sub at={at(0.45)}>{o.sub}</Sub> : null}</div>;
    case "stat":
      return (
        <div style={box}>
          <Count to={o.value} from={o.from ?? 0} pre={o.prefix ?? ""} suf={o.suffix ?? ""} dec={o.dec ?? 0} size={onFootage ? 210 : 260} color={acc} d={Math.min(60, at(0.35))} at={6} />
          <div style={{ height: 12 }} />
          <KText words={o.label} size={onFootage ? 60 : 70} at={at(0.18)} />
        </div>
      );
    case "compare":
      return (
        <div style={{ ...box, ...(onFootage ? { maxWidth: 1700, right: 90 } : {}) }}>
          {o.title ? <Tag at={4} color={acc}>{o.title}</Tag> : null}
          <div style={{ display: "flex", gap: 120, marginTop: 30 }}>
            {o.items.map((it, i) => (
              <div key={i} style={{ opacity: clamp((f - 8 - i * 18) / 12) }}>
                <Count to={it.value} pre={it.prefix ?? ""} suf={it.suffix ?? ""} dec={it.dec ?? 0} size={190} color={i === 0 ? T.teal : T.coral} at={8 + i * 18} d={45} />
                <div style={{ fontFamily: F.sans, fontWeight: 700, fontSize: 48, color: T.fg, marginTop: 10 }}>{it.label}</div>
              </div>
            ))}
          </div>
        </div>
      );
    case "bars": {
      const mx = o.max ?? Math.max(...o.items.map((i) => i.value));
      const cols = [T.coral, T.amber, T.teal, T.blue, T.fg];
      return (
        <div style={{ position: "absolute", left: 110, right: 110, top: onFootage ? 120 : 150 }}>
          {o.title ? <Tag at={4} color={acc}>{o.title}</Tag> : null}
          {o.items.map((it, i) => <BarRow key={i} x={0} y={90 + i * 140} w={1700} v={it.value / mx} label={it.label} val={it.display} color={cols[i % cols.length]} at={10 + i * 10} d={45} labW={460} h={70} />)}
        </div>
      );
    }
    case "list":
      return (
        <div style={box}>
          {o.title ? <><Tag at={4} color={acc}>{o.title}</Tag><div style={{ height: 30 }} /></> : null}
          {o.items.map((it, i) => <Item key={i} at={at(0.1 + i * (0.6 / o.items.length))} n={i + 1} text={it} />)}
        </div>
      );
    case "quote":
      return (
        <div style={{ ...box, ...(onFootage ? { top: 260 } : {}) }}>
          <KText words={`“${o.text}”`} size={onFootage ? 70 : 84} italic weight={400} at={at(0.08)} stagger={3} />
          <Sub at={at(0.4)}>{o.by}</Sub>
        </div>
      );
    case "lower": {
      const s = useSpr(10, { damping: 15, stiffness: 120 });
      const out = clamp((dur - 14 - f) / 10);
      return (
        <div style={{ position: "absolute", left: 90, bottom: 170, opacity: out, transform: `translateX(${(1 - s) * -80}px)` }}>
          <div style={{ display: "flex", alignItems: "stretch" }}>
            <div style={{ width: 12, background: acc, borderRadius: 6 }} />
            <div style={{ background: "#0A0D14D9", padding: "18px 30px", borderRadius: "0 14px 14px 0" }}>
              <div style={{ fontFamily: F.sans, fontWeight: 800, fontSize: 48, color: "#FFFFFF" }}>{o.text}</div>
              {o.sub ? <div style={{ fontFamily: F.sans, fontWeight: 500, fontSize: 32, color: "#C9D2DE", marginTop: 4 }}>{o.sub}</div> : null}
            </div>
          </div>
        </div>
      );
    }
  }
};

const Sub: React.FC<{ at: number; children: React.ReactNode }> = ({ at, children }) => {
  const T = useTh(); const s = useSpr(at);
  return <div style={{ fontFamily: F.sans, fontWeight: 500, fontSize: 42, color: T.dim, marginTop: 24, opacity: clamp(s * 1.5), transform: `translateY(${(1 - s) * 24}px)` }}>{children}</div>;
};
const Item: React.FC<{ at: number; n: number; text: string }> = ({ at, n, text }) => {
  const T = useTh(); const s = useSpr(at, { damping: 13, stiffness: 140 });
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 28, marginBottom: 26, opacity: clamp(s * 2), transform: `translateX(${(1 - s) * -60}px)` }}>
      <div style={{ width: 74, height: 74, borderRadius: 37, background: T.amber, color: "#15171E", fontFamily: F.sans, fontWeight: 900, fontSize: 40, display: "grid", placeItems: "center", flexShrink: 0 }}>{n}</div>
      <div style={{ fontFamily: F.sans, fontWeight: 700, fontSize: 58, color: T.fg }}>{text}</div>
    </div>
  );
};
