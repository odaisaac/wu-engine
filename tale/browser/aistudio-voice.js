/* Topic2Film: narrate a whole video with Google's Gemini voices in AI Studio (free, no API key).
 *
 * You don't edit this file. Run `python tale/aistudio.py snippet FILM`; it writes FILM/aistudio-snippet.js
 * with your script filled in. Then:
 *   1. Open https://aistudio.google.com/generate-speech in Chrome or Edge and sign in.
 *   2. Click "Create new dialog". In the speech block, choose your voice (Speaker) and Style.
 *      Optional: open "Run settings" (top right) to pick the model.
 *   3. Press F12 (Mac: Cmd+Option+J), click Console, paste the whole of aistudio-snippet.js, press Enter.
 *      The first time, Chrome asks you to type "allow pasting" first.
 *   4. Leave the tab open and in front. A box in the corner shows progress.
 *      Every 25 recordings a zip downloads (e.g. myfilm-voice-01.zip).
 *   5. If it stops, paste the snippet again: finished parts are skipped.
 * Then: python tale/aistudio.py import FILM path/to/*-voice-*.zip
 *
 * MODE "paragraph" records one paragraph per run: exact timing, about 10 seconds per paragraph.
 * MODE "chapter" records a whole chapter per run: fewer runs; the import step splits it into
 * paragraphs at the pauses, which is usually right but can be off by a sentence.
 * Use it with your own Google account and follow Google's terms.
 */
(async () => {
  const FILM = "__FILM__";
  const MODE = "__MODE__";
  const PARTS = __PARTS__;             // [[name, [paragraph numbers], "text to speak"], ...]
  const BATCH = 25;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const doneKey = "t2f_voice_" + FILM + "_" + MODE;
  let done = new Set();
  try { done = new Set(JSON.parse(localStorage.getItem(doneKey) || "[]")); } catch (e) {}
  const saveDone = () => { try { localStorage.setItem(doneKey, JSON.stringify([...done])); } catch (e) {} };

  let box = document.getElementById("t2f-box");
  if (!box) {
    box = document.createElement("div"); box.id = "t2f-box";
    Object.assign(box.style, { position: "fixed", right: "16px", bottom: "80px", zIndex: 99999, background: "#111", color: "#fff",
      font: "14px/1.4 system-ui, sans-serif", padding: "12px 16px", borderRadius: "10px", boxShadow: "0 6px 20px #0008", maxWidth: "320px" });
    document.body.appendChild(box);
  }
  const say = (t) => { box.textContent = "Topic2Film: " + t; console.log("[Topic2Film]", t); };

  const textarea = () => document.querySelector('textarea[aria-label="Speech block text"]');
  const runButton = () => [...document.querySelectorAll("button")].find((b) => /^Run\b/.test((b.textContent || "").trim()));
  const audioSrc = () => { const a = document.querySelector("audio"); return a && a.src ? a.src : ""; };
  const setText = (t) => {
    const el = textarea(); if (!el) throw new Error('no speech block. Click "Create new dialog" first.');
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set.call(el, t);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  };

  const speak = async (text) => {
    setText(text); await sleep(600);
    const before = audioSrc(); const run = runButton(); if (!run) throw new Error("Run button not found");
    run.click();
    let last = "", stable = 0;
    for (let t = 0; t < 360; t++) {                       // up to 3 minutes per run
      await sleep(500);
      const s = audioSrc();
      if (s && s !== before && s.startsWith("data:audio") && s.length > 20000) {
        if (s === last) { if (++stable >= 4) break; } else { last = s; stable = 0; }
      }
    }
    if (!last || stable < 4) throw new Error("no audio came back (limit reached, or the page changed)");
    return await (await fetch(last)).blob();
  };

  const CRC = new Uint32Array(256).map((_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
  const crc32 = (b) => { let c = 0xFFFFFFFF; for (let i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
  const zipDownload = async (entries, name) => {
    const parts = [], cen = []; let off = 0; const enc = new TextEncoder();
    for (const [nm, blob] of entries) {
      const d = new Uint8Array(await blob.arrayBuffer()), fn = enc.encode(nm), c = crc32(d);
      const h = new DataView(new ArrayBuffer(30));
      h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint32(14, c, true); h.setUint32(18, d.length, true); h.setUint32(22, d.length, true); h.setUint16(26, fn.length, true);
      parts.push(new Uint8Array(h.buffer), fn, d);
      const e = new DataView(new ArrayBuffer(46));
      e.setUint32(0, 0x02014b50, true); e.setUint16(4, 20, true); e.setUint16(6, 20, true); e.setUint32(16, c, true); e.setUint32(20, d.length, true); e.setUint32(24, d.length, true); e.setUint16(28, fn.length, true); e.setUint32(42, off, true);
      cen.push(new Uint8Array(e.buffer), fn); off += 30 + fn.length + d.length;
    }
    let cs = 0; for (const x of cen) cs += x.length;
    const z = new DataView(new ArrayBuffer(22));
    z.setUint32(0, 0x06054b50, true); z.setUint16(8, entries.length, true); z.setUint16(10, entries.length, true); z.setUint32(12, cs, true); z.setUint32(16, off, true);
    const blob = new Blob([...parts, ...cen, new Uint8Array(z.buffer)], { type: "application/zip" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
  };

  const todo = PARTS.filter(([name]) => !done.has(name));
  if (!todo.length) { say("everything is already recorded. To start again, run: localStorage.removeItem('" + doneKey + "')"); return; }
  let zipNo = 1; try { zipNo = Number(localStorage.getItem(doneKey + "_zip") || "1"); } catch (e) {}
  let pending = [], made = 0; const failed = [];
  const flush = async () => {
    if (!pending.length) return;
    const map = {}; for (const [nm, , paras] of pending) map[nm] = paras;
    const entries = pending.map(([nm, blob]) => [nm, blob]);
    entries.push(["parts.json", new Blob([JSON.stringify({ film: FILM, mode: MODE, parts: map })], { type: "application/json" })]);
    await zipDownload(entries, `${FILM}-voice-${String(zipNo).padStart(2, "0")}.zip`);
    for (const [nm] of pending) done.add(nm.replace(/\.wav$/, ""));
    saveDone(); zipNo++; try { localStorage.setItem(doneKey + "_zip", String(zipNo)); } catch (e) {}
    pending = [];
  };

  for (let round = 0; round < 3; round++) {
    const list = round === 0 ? todo : failed.splice(0);
    for (const [name, paras, text] of list) {
      say(`recording ${made + 1} of ${todo.length} (${MODE === "chapter" ? "chapter" : "paragraph"} ${name})${failed.length ? `, ${failed.length} to retry` : ""}`);
      try { pending.push([name + ".wav", await speak(text), paras]); made++; }
      catch (e) { console.warn("[Topic2Film]", name, e.message); failed.push([name, paras, text]); await sleep(5000); }
      if (pending.length >= BATCH) await flush();
      await sleep(1200);
    }
    if (!failed.length) break;
  }
  await flush();
  say(failed.length ? `finished with ${failed.length} not recorded: ${failed.map((f) => f[0]).join(", ")}. Paste the snippet again later to retry them.`
                    : `done: ${made} recordings saved. Now run: python tale/aistudio.py import ${FILM} <the zip files>`);
})();
