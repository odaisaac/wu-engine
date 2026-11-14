# Getting full-size Gemini pictures out of the browser pane (no save box per picture)

The desktop browser pane shows a Save dialog for every download, so clicking
"Download full size image" 110 times is not workable. Instead, run these steps
with the page's JavaScript tool on gemini.google.com.

1. **Queue prompts**: put text in `.ql-editor` with
   `document.execCommand('insertText')`, click `button[aria-label="Send message"]`,
   wait until the count of `button[aria-label="Download full size image"]` grows.
   About 15 s per picture. Prefix every prompt with the style line.
2. **Catch the full-size file**: wrap `window.fetch`. When the page fetches a
   `…usercontent…=s0-d-I?alr=yes` URL whose response is `image/*`, keep
   `await res.clone().blob()` (2752x1536 JPEG, 3-4 MB), then throw
   `TypeError('Failed to fetch')` back to the page so it never opens a Save dialog.
3. **Trigger it**: for each picture in order, `scrollIntoView` its download button,
   `.click()` it, wait for a new captured blob (about 12 s), then the next.
   One at a time only.
4. **One zip, one save**: build a store-only zip of the blobs in page JS
   (local headers + central directory + CRC32), make an `<a download>` and click
   it. The user clicks Save once. Stage the zip from Downloads and unpack with
   `python3 -I`.

Notes
- Previews (`img` elements) are only 1024x572; use them only as a fallback.
- After a page reload some previews load from a cross-origin URL and cannot be
  read through a canvas; the fetch hook in step 2 does not have that problem.
- Add "fills the entire frame edge to edge, no border, no text" to prompts, and
  start a new chat when changing style: Gemini carries layout habits over.

## Description footer (every Plain Tale English video)

    🔹 Plain Tale English: Disclaimer & Copyright
    This video is made for education and English language learning.
    The script is original. The pictures are AI-made illustrations, not real paintings or photographs, and the narration is a computer voice. Historical facts are told in simple words and some details are shortened.
    © Plain Tale English. All rights reserved.
    No part of this video may be copied or re-uploaded without written permission.
