/* Topic2Film: make all the pictures for a video in Gemini, at full size, saved in a few zip files.
 *
 * You don't edit this file. Run `python tale/images.py snippet FILM`; it writes FILM/gemini-snippet.js
 * with your prompts filled in. Then:
 *   1. Open https://gemini.google.com/app in Chrome (or Edge) and sign in.
 *   2. Press F12 (Mac: Cmd+Option+J) to open the Console.
 *   3. Paste the whole of gemini-snippet.js and press Enter.
 *      The first time, Chrome asks you to type "allow pasting" first.
 *   4. Leave the tab open and in front. A box in the corner shows progress.
 *      Every 25 pictures a zip file downloads (e.g. myfilm-images-01.zip).
 *   5. If it stops (closed tab, lost connection), paste the snippet again: finished pictures are skipped.
 * Then: python tale/images.py import FILM path/to/*.zip
 *
 * How it works: it types each prompt into Gemini, waits for the picture, clicks
 * "Download full size image", and keeps that full-size file in memory instead of
 * letting the page download it one by one. Use it with your own Google account and
 * follow Google's terms of service.
 */
(async () => {
  const FILM = "__FILM__";
  const STYLE = __STYLE__;
  const PROMPTS = __PROMPTS__;          // [[paragraphNumber or "thumb", "scene description"], ...]
  const BATCH = 25;                     // pictures per zip file
  const NEW_CHAT_EVERY = 30;            // Gemini gets slow in long chats
  const WIDTH = 2400;                   // saved width in pixels

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const doneKey = "t2f_done_" + FILM;
  let done = new Set();
  try { done = new Set(JSON.parse(localStorage.getItem(doneKey) || "[]").map(String)); } catch (e) {}
  const saveDone = () => { try { localStorage.setItem(doneKey, JSON.stringify([...done])); } catch (e) {} };

  // progress box
  let box = document.getElementById("t2f-box");
  if (!box) {
    box = document.createElement("div"); box.id = "t2f-box";
    Object.assign(box.style, { position: "fixed", right: "16px", bottom: "16px", zIndex: 99999, background: "#111", color: "#fff",
      font: "14px/1.4 system-ui, sans-serif", padding: "12px 16px", borderRadius: "10px", boxShadow: "0 6px 20px #0008", maxWidth: "320px" });
    document.body.appendChild(box);
  }
  const say = (t) => { box.textContent = "Topic2Film: " + t; console.log("[Topic2Film]", t); };

  // catch the full-size file when Gemini fetches it, and stop the page's own download
  const caught = [];
  if (!window.__t2fHooked) {
    window.__t2fHooked = true;
    const orig = window.fetch;
    window.fetch = async function (u, ...rest) {
      const res = await orig.call(this, u, ...rest);
      let isImg = false;
      try {
        const s = typeof u === "string" ? u : u.url;
        if (/usercontent/.test(s) && /s0-d-I/.test(s) && /^image\//.test(res.headers.get("content-type") || "")) {
          (window.__t2fCaught || []).push(await res.clone().blob()); isImg = true;
        }
      } catch (e) {}
      if (isImg) throw new TypeError("Failed to fetch");
      return res;
    };
  }
  window.__t2fCaught = caught;

  const dlButtons = () => [...document.querySelectorAll("button")].filter((b) => (b.getAttribute("aria-label") || "") === "Download full size image");
  const editor = () => document.querySelector(".ql-editor");

  // tiny zip writer (no compression; pictures are already compressed)
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

  const newChat = async () => {
    const c = [...document.querySelectorAll("a,button")].find((e) => /new chat/i.test((e.getAttribute("aria-label") || "") + " " + (e.textContent || "")));
    if (c) { c.click(); await sleep(4000); }
  };

  const makeOne = async (text) => {
    const before = dlButtons().length;
    const ed = editor(); if (!ed) throw new Error("Gemini prompt box not found. Is this gemini.google.com/app?");
    ed.focus(); document.execCommand("selectAll"); document.execCommand("insertText", false, STYLE + text);
    await sleep(800);
    const send = document.querySelector('button[aria-label="Send message"]'); if (!send) throw new Error("send button not found");
    send.click();
    let ok = false;
    for (let t = 0; t < 120; t++) { await sleep(1000); if (dlButtons().length > before) { ok = true; break; } }
    if (!ok) throw new Error("no picture came back (Gemini may have refused this prompt or hit a limit)");
    await sleep(1500);
    const n0 = caught.length, bs = dlButtons(), b = bs[bs.length - 1];
    b.scrollIntoView({ block: "center" }); await sleep(600); b.click();
    let got = null;
    for (let t = 0; t < 120; t++) { await sleep(500); if (caught.length > n0) { got = caught[caught.length - 1]; break; } }
    if (!got) throw new Error("full-size picture did not arrive");
    const bm = await createImageBitmap(got);
    const c = document.createElement("canvas"); c.width = WIDTH; c.height = Math.round(WIDTH * bm.height / bm.width);
    c.getContext("2d").drawImage(bm, 0, 0, c.width, c.height);
    caught.length = 0;
    return await new Promise((r) => c.toBlob(r, "image/jpeg", 0.92));
  };

  const todo = PROMPTS.filter(([n]) => !done.has(String(n)));
  if (!todo.length) { say("all pictures are already done. To start again, run: localStorage.removeItem('" + doneKey + "')"); return; }
  let zipNo = 1; try { zipNo = Number(localStorage.getItem(doneKey + "_zip") || "1"); } catch (e) {}
  let pending = [], inChat = 0, made = 0; const failed = [];
  const flush = async () => {
    if (!pending.length) return;
    const name = `${FILM}-images-${String(zipNo).padStart(2, "0")}.zip`;
    await zipDownload(pending, name);
    for (const [nm] of pending) done.add(nm.replace(/\.jpg$/, "").replace(/^0+(?=\d)/, ""));
    saveDone(); zipNo++; try { localStorage.setItem(doneKey + "_zip", String(zipNo)); } catch (e) {}
    pending = [];
  };
  const fname = (n) => (n === "thumb" ? "thumb" : String(n).padStart(3, "0")) + ".jpg";

  for (let round = 0; round < 3; round++) {
    const list = round === 0 ? todo : failed.splice(0);
    for (const [n, text] of list) {
      if (inChat >= NEW_CHAT_EVERY) { await newChat(); inChat = 0; }
      say(`picture ${made + 1} of ${todo.length} (paragraph ${n})${failed.length ? `, ${failed.length} to retry` : ""}`);
      try { pending.push([fname(n), await makeOne(text)]); made++; inChat++; }
      catch (e) { console.warn("[Topic2Film]", n, e.message); failed.push([n, text]); await sleep(4000); }
      if (pending.length >= BATCH) await flush();
      await sleep(1500);
    }
    if (!failed.length) break;
  }
  await flush();
  say(failed.length ? `finished with ${failed.length} failed: ${failed.map((f) => f[0]).join(", ")}. Paste the snippet again to retry them.`
                    : `done: ${made} pictures saved. Now run: python tale/images.py import ${FILM} <the zip files>`);
})();
