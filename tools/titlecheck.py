#!/usr/bin/env python3
"""Score YouTube title ideas before you pick one.

  python tools/titlecheck.py "Why the Stock Market Just Crashed" "The Story of Tea"
  python tools/titlecheck.py films/tea/youtube-pack.md      (reads the numbered titles under "## Title")

Checks what tends to work for story and explainer channels:
  length      the part before " | " fits on a phone (about 60 characters, best 30-55)
  question    opens a question the viewer wants answered (How, Why, What, Inside, The day...)
  number      a concrete number or money figure ($80 Billion, 342 chests, 3 days)
  stakes      a strong word: lost, war, crash, secret, spy, fail, collapse, billion...
  subject     a named subject the viewer recognises, early (a capitalised name in the first 5 words)
  calm caps   not shouting in capitals
A suffix after " | " (e.g. "| English Listening Practice") is ignored for length and kept as the search phrase.
"""
import re, sys

OPENERS = re.compile(r"^(how|why|what|who|when|inside|the (day|night|year|man|woman|truth|real|secret|story|leaf|war|deal)|"
                     r"this|nobody|everyone|the biggest|the worst|the last|the first)\b", re.I)
NUMBER = re.compile(r"[$€£₦]\s?\d|\d[\d,.]*\s?(%|k|m|bn|billion|million|trillion|years?|days?|hours?|minutes?|people|chests?)\b|\b\d{2,}\b", re.I)
STAKES = re.compile(r"\b(lost|losing|war|wars|crash(ed)?|secret|spy|fail(ed|s)?|collapse(d)?|billion|million|trillion|empire|"
                    r"disaster|deadly|banned|stole|stolen|scam|rich|poor|broke|died|killed|vanished|changed the world|started)\b", re.I)


def score(title):
    head = title.split(" | ")[0].strip()
    tips, pts = [], 0
    n = len(head)
    if 30 <= n <= 55: pts += 25
    elif n < 30: pts += 15; tips.append(f"{n} characters: short, room to add the stake or a number")
    elif n <= 62: pts += 15; tips.append(f"{n} characters: a little long for phones (aim for 30-55)")
    else: tips.append(f"{n} characters: will be cut off on phones (aim for 30-55)")
    if OPENERS.search(head): pts += 20
    else: tips.append('open a question: "How...", "Why...", "The day..."')
    if NUMBER.search(head): pts += 20
    else: tips.append("add a concrete number or money figure")
    if STAKES.search(head): pts += 20
    else: tips.append("add a stake word (lost, war, secret, crash, billion...)")
    caps = [w for w in re.findall(r"[A-Za-z]{2,}", head)]
    if any(w[0].isupper() for w in caps[1:6]) or re.search(r"\b[A-Z]{2,}\b", head): pts += 10
    else: tips.append("name the subject early (a person, company, country or thing people know)")
    shouting = sum(1 for w in caps if w.isupper() and len(w) > 3)
    if shouting <= 1: pts += 5
    else: tips.append("too many words in capitals")
    return pts, tips


def from_pack(path):
    text = open(path, encoding="utf-8").read()
    m = re.search(r"## Title[^\n]*\n(.*?)(\n## |\Z)", text, re.S)
    return [re.sub(r"^\d+\.\s*", "", l).strip() for l in (m.group(1) if m else "").splitlines() if re.match(r"^\d+\.", l.strip())]


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    titles = from_pack(args[0]) if len(args) == 1 and args[0].endswith(".md") else args
    if not titles:
        sys.exit("no titles found")
    rows = sorted(((score(t), t) for t in titles), key=lambda r: -r[0][0])
    for (pts, tips), t in rows:
        print(f"{pts:3d}/100  {t}")
        for tip in tips:
            print(f"         - {tip}")
    print(f"\nbest: {rows[0][1]}")
