#!/usr/bin/env python3
"""Merge Pexels results from the Apify actor (automation-lab/pexels-stock-media-scraper) into FILM/candidates.json.

  python3 tools/pexels_import.py FILM items.json

items.json = list of dataset rows with at least mediaId, query, title, thumbnailUrl (optionally width, url).
Fetch them with Apify get-dataset-items fields="mediaId,query,title,width,thumbnailUrl".
Rows are matched to shots by their search phrase; portrait clips (width 1080/2160 with no 16:9) are skipped.
"""
import json, os, sys
film, src = sys.argv[1], sys.argv[2]
spec = json.load(open(os.path.join(film, "spec.json")))
q2s = {q: s["id"] for s in spec["shots"] for q in s.get("query", [])}
cp = os.path.join(film, "candidates.json")
cand = json.load(open(cp)) if os.path.exists(cp) else {}
n = 0
for r in json.load(open(src)):
    sid = q2s.get(r.get("query"))
    if not sid or int(r.get("width") or 1920) in (1080, 720):
        continue
    lst = cand.setdefault(sid, [])
    if any(c["src"] == "pexels" and c["id"] == str(r["mediaId"]) for c in lst):
        continue
    lst.append(dict(src="pexels", id=str(r["mediaId"]), kind="video", title=r.get("title", ""), thumb=(r.get("thumbnailUrl") or f"https://images.pexels.com/videos/{r['mediaId']}/pictures/preview-0.jpg").replace("w=750", "w=640"),
                    url=r.get("url"), license="Pexels License", credit=f"Pexels · video {r['mediaId']}", page=f"https://www.pexels.com/video/{r['mediaId']}/", query=r.get("query")))
    n += 1
json.dump(cand, open(cp, "w"), indent=1)
print("added", n, "pexels candidates")
