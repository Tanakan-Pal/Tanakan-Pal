"""Build the project list from GitHub and keep the README and Tanakan Stats in sync.

Sources:
  - public repos of the owner tagged with the `portfolio` topic (added automatically)
  - scripts/manual_projects.json:
      * an entry whose name matches a repo overrides that repo's fields (description, stack, year)
      * any other entry is a manual row, for example a private repo

Writes:
  - README.md, between <!-- PROJECTS:START --> and <!-- PROJECTS:END -->
  - projects.json, read by scripts/research_city.py for the Projects row of Tanakan Stats
"""
import json
import os
import re
import urllib.request

USER = os.environ.get("PROFILE_USER", "Tanakan-Pal")
TOPIC = "portfolio"
README = "README.md"
MANUAL = "scripts/manual_projects.json"
OUT = "projects.json"
START, END = "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->"


def api(path):
    req = urllib.request.Request("https://api.github.com" + path, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.load(r)


manual = json.load(open(MANUAL, encoding="utf-8")) if os.path.exists(MANUAL) else []
overrides = {m["name"].lower(): m for m in manual}
used = set()

auto = []
for r in api("/users/%s/repos?per_page=100&type=owner" % USER):
    if r.get("fork") or r.get("archived") or r.get("private"):
        continue
    if TOPIC not in (r.get("topics") or []):
        continue
    p = {
        "name": r["name"],
        "url": r["html_url"],
        "description": r.get("description") or "",
        "stack": list(api("/repos/%s/languages" % r["full_name"]).keys())[:3],
        "site": r.get("homepage") or ("https://%s.github.io/%s/" % (USER.lower(), r["name"]) if r.get("has_pages") else ""),
        "year": int(r["created_at"][:4]),
        "created": r["created_at"],
    }
    o = overrides.get(r["name"].lower())
    if o:
        used.add(r["name"].lower())
        p.update({k: v for k, v in o.items() if k != "name" and v not in (None, "", [])})
    auto.append(p)
auto.sort(key=lambda p: p["created"])

import datetime
rows_manual = [{"url": "", "site": "", "stack": [], "year": datetime.date.today().year, **m} for m in manual if m["name"].lower() not in used]
projects = rows_manual + auto


def row(p):
    title = "**[%s](%s)**" % (p["name"], p["url"]) if p.get("url") else "**%s**" % p["name"]
    desc = p.get("description", "").replace("|", "\\|")
    if p.get("site"):
        desc = (desc + " " if desc else "") + "[Live site](%s)" % p["site"]
    return "| %s | %s | %s |" % (title, desc, " ".join("`%s`" % s for s in p.get("stack", [])))


table = "\n".join(["| Project | Description | Stack |", "|---|---|---|"] + [row(p) for p in projects])
text = open(README, encoding="utf-8").read()
if START not in text or END not in text:
    raise SystemExit("Add %s and %s around the Projects table in README.md" % (START, END))
new = re.sub(re.escape(START) + r".*?" + re.escape(END), START + "\n" + table + "\n" + END, text, flags=re.S)
open(README, "w", encoding="utf-8").write(new)

json.dump([{"name": p["name"], "year": p["year"]} for p in projects], open(OUT, "w", encoding="utf-8"), indent=2)
open(OUT, "a", encoding="utf-8").write("\n")
print("%d projects: %s" % (len(projects), ", ".join(p["name"] for p in projects)))
