#!/usr/bin/env python3
"""Search free / open media sources for every footage shot of a film.

  python3 tools/sources.py FILM [--only 03,07] [--per 6] [--src archive,nasa,wiki,openverse,loc]

Writes FILM/candidates.json: {shot_id: [candidate, ...]} where a candidate is
  {src, id, kind: video|image, title, thumb, url, license, credit, page, query}

Only licences that are safe for a monetised YouTube channel are kept:
public domain / CC0 / CC BY / CC BY-SA (no NC, no ND). NASA media is
generally not copyrighted; LoC items are kept only when their rights text
says there are no known restrictions or they come from public-domain
collections. Official APIs only — no scraping.
Pexels results arrive separately via Apify (tools/pexels_import.py) and are
merged into the same file.
"""
import json, os, re, sys, time, argparse, urllib.request, urllib.parse as up

UA = "WorldUnpackedEngine/1.0 (private documentary tool; https://github.com/odaisaac)"
OK_CC = re.compile(r"(publicdomain|/zero/|/by/|/by-sa/|^cc0$|^by$|^by-sa$|^pdm$|public domain|cc by(-sa)? \d|^cc0 1\.0$|cc-by(-sa)?)", re.I)
BAD_CC = re.compile(r"(-nc|-nd|/nc|/nd|\bnc\b|\bnd\b|noncommercial|noderiv)", re.I)


_last = {}


def get(url, tries=4):
    host = up.urlparse(url).netloc
    gap = 2.0 if "wikimedia" in host else 0.3          # Wikimedia rate-limits bursts
    wait = _last.get(host, 0) + gap - time.time()
    if wait > 0:
        time.sleep(wait)
    _last[host] = time.time()
    for i in range(tries):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA})
            return json.load(urllib.request.urlopen(r, timeout=40))
        except Exception as e:  # 429 / transient
            if i == tries - 1:
                print("  !", url[:90], e, file=sys.stderr)
                return None
            time.sleep(6 * (i + 1))


def clean(t):
    return re.sub(r"<[^>]+>", "", t or "").strip()


def lic_ok(s):
    s = (s or "").strip()
    return bool(s) and not BAD_CC.search(s) and bool(OK_CC.search(s))


# ---------------------------------------------------------------- adapters
def archive(q, n):
    words = [w for w in re.findall(r"[a-zA-Z]+", q) if len(w) > 3]
    docs = []
    for terms in (q, " ".join(words[-2:]), words[-1] if words else q):
        qq = f"({terms}) AND mediatype:movies AND (collection:prelinger OR licenseurl:*publicdomain* OR licenseurl:*zero*)"
        d = get("https://archive.org/advancedsearch.php?" + up.urlencode(
            {"q": qq, "fl[]": ["identifier", "title", "licenseurl", "collection", "year"], "rows": n * 2, "output": "json"}, doseq=True))
        docs = (d or {}).get("response", {}).get("docs", [])
        if len(docs) >= n:
            break
    out = []
    for x in docs:
        col = x.get("collection") or []
        col = [col] if isinstance(col, str) else col
        lic = x.get("licenseurl") or ("Public domain (Prelinger Archives)" if "prelinger" in col else "")
        if not (lic_ok(lic) or "Prelinger" in lic or "publicdomain" in lic):
            continue
        out.append(dict(src="archive", id=x["identifier"], kind="video", title=clean(x.get("title")), thumb=f"https://archive.org/services/img/{x['identifier']}",
                        url=None, license=lic, credit=f"Internet Archive · {x['identifier']}", page=f"https://archive.org/details/{x['identifier']}"))
        if len(out) >= n:
            break
    return out


def archive_resolve(c):
    m = get(f"https://archive.org/metadata/{c['id']}") or {}
    files = [f for f in m.get("files", []) if f["name"].lower().endswith((".mp4", ".mpeg4", ".m4v"))]
    files.sort(key=lambda f: int(f.get("height") or f.get("width") or 0), reverse=True)
    return f"https://archive.org/download/{c['id']}/{up.quote(files[0]['name'])}" if files else None


def nasa(q, n):
    d = get("https://images-api.nasa.gov/search?" + up.urlencode({"q": q, "media_type": "video", "page_size": n}))
    out = []
    for it in (d or {}).get("collection", {}).get("items", [])[:n]:
        x = it["data"][0]
        thumb = (it.get("links") or [{}])[0].get("href")
        out.append(dict(src="nasa", id=x["nasa_id"], kind="video", title=clean(x.get("title")), thumb=thumb, url=None, collection=it["href"],
                        license="NASA media (not copyrighted)", credit=f"NASA · {x.get('center', '')} · {x['nasa_id']}", page=f"https://images.nasa.gov/details/{x['nasa_id']}"))
    return out


def nasa_resolve(c):
    files = get(c["collection"]) or []
    for tag in ("~orig.mp4", "~large.mp4", "~medium.mp4"):
        for f in files:
            if f.endswith(tag):
                return f.replace("http://", "https://")
    return None


def wiki(q, n, kind="video"):
    flt = "filetype:video" if kind == "video" else "filetype:bitmap"
    d = get("https://commons.wikimedia.org/w/api.php?" + up.urlencode({"action": "query", "generator": "search", "gsrnamespace": 6, "gsrsearch": f"{q} {flt}", "gsrlimit": n * 2,
            "prop": "imageinfo", "iiprop": "url|extmetadata|size|mediatype", "iiurlwidth": 640, "format": "json"}))
    out = []
    for p in ((d or {}).get("query") or {}).get("pages", {}).values():
        ii = p["imageinfo"][0]
        md = ii.get("extmetadata", {})
        lic = md.get("LicenseShortName", {}).get("value", "")
        if not lic_ok(lic) or (ii.get("width") or 0) < (1280 if kind == "video" else 1600):
            continue
        artist = re.sub("<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()[:60]
        out.append(dict(src="wiki", id=p["title"], kind=kind, title=p["title"].replace("File:", ""), thumb=ii.get("thumburl"), url=ii["url"].split("?")[0],
                        license=lic, credit=f"{artist or 'Unknown'} · Wikimedia Commons · {lic}", page=ii.get("descriptionurl", "")))
        if len(out) >= n:
            break
    return out


def openverse(q, n):
    d = get("https://api.openverse.org/v1/images/?" + up.urlencode({"q": q, "page_size": n * 2, "license_type": "commercial,modification", "aspect_ratio": "wide", "size": "large"}))
    out = []
    for r in (d or {}).get("results", []):
        if not lic_ok(r["license"]) or (r.get("width") or 0) < 1600:
            continue
        out.append(dict(src="openverse", id=r["id"], kind="image", title=clean(r.get("title")), thumb=r["thumbnail"], url=r["url"], license=f"CC {r['license'].upper()} {r.get('license_version', '')}".strip(),
                        credit=f"{r.get('creator') or 'Unknown'} · {r.get('source')} · CC {r['license'].upper()}", page=r.get("foreign_landing_url", "")))
        if len(out) >= n:
            break
    return out


def loc(q, n):
    d = get("https://www.loc.gov/search/?" + up.urlencode({"q": q, "fa": "online-format:image", "fo": "json", "c": n * 3}))
    out = []
    for r in (d or {}).get("results", []):
        rights = " ".join(r.get("rights") or []) if isinstance(r.get("rights"), list) else str(r.get("rights") or "")
        pd = re.search(r"no known restrictions|public domain", rights, re.I) or any(k in str(r.get("partof", "")).lower() for k in ("farm security administration", "fsa/owi"))
        imgs = r.get("image_url") or []
        if not pd or not imgs:
            continue
        big = imgs[-1].split("#")[0]
        out.append(dict(src="loc", id=r.get("id", big), kind="image", title=clean(r.get("title"))[:120], thumb=imgs[0].split("#")[0], url=big, license="No known restrictions (Library of Congress)",
                        credit="Library of Congress, Prints & Photographs Division", page=r.get("url") or r.get("id", "")))
        if len(out) >= n:
            break
    return out


ADAPT = {"archive": archive, "nasa": nasa, "wiki": wiki, "wikiimg": lambda q, n: wiki(q, n, "image"), "openverse": openverse, "loc": loc}
def pexels_resolve(c):
    """1080p rendition: explicit url from the Apify dataset, else probe the classic file-name pattern."""
    i = c["id"]
    for res in ("1920_1080", "2048_1080", "1920_1012", "1920_1018"):
        for f in ("25", "30", "24", "60", "50", "29"):
            u = f"https://videos.pexels.com/video-files/{i}/{i}-hd_{res}_{f}fps.mp4"
            try:
                urllib.request.urlopen(urllib.request.Request(u, method="HEAD", headers={"User-Agent": UA}), timeout=15)
                return u
            except Exception:
                pass
    return None


RESOLVE = {"archive": archive_resolve, "nasa": nasa_resolve, "pexels": pexels_resolve}


def resolve(c):
    """Fill c['url'] for sources that need a second lookup."""
    if not c.get("url") and c["src"] in RESOLVE:
        c["url"] = RESOLVE[c["src"]](c)
    return c.get("url")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("--only", default="")
    ap.add_argument("--per", type=int, default=5)
    ap.add_argument("--src", default="nasa,wiki,openverse,loc")   # add "archive" for history topics (SD archival film)
    a = ap.parse_args()
    spec = json.load(open(os.path.join(a.film, "spec.json")))
    only = set(filter(None, a.only.split(",")))
    path = os.path.join(a.film, "candidates.json")
    cand = json.load(open(path)) if os.path.exists(path) else {}
    for s in spec["shots"]:
        if s["kind"] not in ("footage", "photo") or (only and s["id"] not in only):
            continue
        got, seen = [c for c in cand.get(s["id"], []) if c["src"] == "pexels"], set()
        for q in s.get("query", [])[:2]:
            for src in a.src.split(","):
                for c in ADAPT[src](q, a.per):
                    if c["id"] in seen:
                        continue
                    seen.add(c["id"]); c["query"] = q; got.append(c)
        cand[s["id"]] = got
        print(s["id"], len(got), "candidates", {k: sum(c["src"] == k for c in got) for k in set(c["src"] for c in got)})
        json.dump(cand, open(path, "w"), indent=1)


if __name__ == "__main__":
    main()
