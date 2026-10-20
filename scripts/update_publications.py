"""Rebuild the Publications section of README.md from ORCID (+ Crossref for full citations).

Run by .github/workflows/update-publications.yml. Only the text between
<!-- PUBLICATIONS:START --> and <!-- PUBLICATIONS:END --> is replaced.
"""
import json
import re
import sys
import urllib.parse
import urllib.request

ORCID_ID = "0000-0002-1424-8555"
MY_FAMILY_NAME = "Paladkong"          # bolded in author lists
README = "README.md"
START, END = "<!-- PUBLICATIONS:START -->", "<!-- PUBLICATIONS:END -->"
# ORCID work types to list here (posters go in Presentations, which you edit by hand)
KEEP_TYPES = {"journal-article", "book-chapter", "conference-paper", "preprint"}
UA = "Tanakan-Pal-profile-readme (mailto:tanakan.pal@gmail.com)"


def get_json(url, accept="application/json"):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def orcid_works():
    data = get_json(f"https://pub.orcid.org/v3.0/{ORCID_ID}/works")
    works = []
    for group in data.get("group", []):
        w = group["work-summary"][0]          # ORCID's preferred version of this work
        if w.get("type") not in KEEP_TYPES:
            continue
        ids = (w.get("external-ids") or {}).get("external-id", [])
        doi = next((i["external-id-value"] for i in ids if i["external-id-type"] == "doi"), None)
        date = w.get("publication-date") or {}
        works.append({
            "title": w["title"]["title"]["value"],
            "journal": (w.get("journal-title") or {}).get("value", ""),
            "year": int(((date.get("year") or {}).get("value")) or 0),
            "doi": doi.lower() if doi else None,
        })
    return works


def initials(given):
    parts = re.split(r"[\s\-]+", given or "")
    return "".join(p[0] + "." for p in parts if p)


def crossref(doi):
    try:
        m = get_json("https://api.crossref.org/works/" + urllib.parse.quote(doi))["message"]
    except Exception as e:                  # Crossref down or DOI not registered there
        print(f"crossref lookup failed for {doi}: {e}", file=sys.stderr)
        return None
    authors = []
    for a in m.get("author", []):
        name = f"{a.get('family', '')} {initials(a.get('given', ''))}".strip()
        if a.get("family", "").lower() == MY_FAMILY_NAME.lower():
            name = f"**{name}**"
        authors.append(name)
    year = (m.get("issued", {}).get("date-parts") or [[None]])[0][0]
    return {
        "authors": authors,
        "title": (m.get("title") or [""])[0],
        "journal": (m.get("short-container-title") or m.get("container-title") or [""])[0],
        "volume": m.get("volume", ""),
        "pages": m.get("page", "").replace("-", "–"),
        "year": year,
    }


def fmt(w):
    c = crossref(w["doi"]) if w["doi"] else None
    if c:
        authors = ", ".join(c["authors"])
        tail = f" {c['volume']}" if c["volume"] else ""
        tail += f": {c['pages']}" if c["pages"] else ""
        line = f"{authors} ({c['year'] or w['year']}). {c['title'].rstrip('.')}. *{c['journal']}*{tail}."
    else:
        journal = f" *{w['journal']}*." if w["journal"] else ""
        line = f"{w['title']} ({w['year'] or 'n.d.'}).{journal}"
    if w["doi"]:
        line += f" [doi:{w['doi']}](https://doi.org/{w['doi']})"
    return "- " + line


def main():
    works = sorted(orcid_works(), key=lambda w: w["year"], reverse=True)
    if not works:
        sys.exit("ORCID returned no works; leaving README unchanged.")
    block = "\n".join(fmt(w) for w in works)

    text = open(README, encoding="utf-8").read()
    if START not in text or END not in text:
        sys.exit(f"Markers {START} / {END} not found in {README}.")
    new = re.sub(re.escape(START) + r".*?" + re.escape(END),
                 f"{START}\n{block}\n{END}", text, flags=re.S)
    if new != text:
        open(README, "w", encoding="utf-8").write(new)
        print(f"Updated {len(works)} publications.")
    else:
        print("No changes.")


if __name__ == "__main__":
    main()
