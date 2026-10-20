"""Draw research-city.svg and research-city-dark.svg from research.yml.

Isometric city: columns = years, rows = categories, building height = number of
items x the category's `unit`. A radar on the right shows the total per category.
Usage: python scripts/research_city.py [research.yml] [output-dir]
"""
import math
import sys
from html import escape

import yaml

THEMES = {
    "light": dict(bg="#ffffff", tile="#e9eef5", tile_edge="#d0d7de", text="#24292f",
                  muted="#6e7781", grid="#d0d7de", radar="#d29922", radar_fill="#d29922"),
    "dark": dict(bg="#03030f", tile="#14204a", tile_edge="#1d2d63", text="#e6edf3",
                 muted="#8b949e", grid="#3a3f4b", radar="#f2cc60", radar_fill="#f2cc60"),
}
W, H = 1000, 520
TW, TH = 62, 31            # isometric tile width/height


def shade(hex_color, f):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if f < 1:
        r, g, b = (int(c * f) for c in (r, g, b))
    else:
        r, g, b = (int(c + (255 - c) * (f - 1)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def iso(i, j, ox, oy):
    return ox + (i - j) * TW / 2, oy + (i + j) * TH / 2


def poly(points, fill, stroke=None, sw=1):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<polygon points="{pts}" fill="{fill}"{s}/>'


def box(i, j, h, color, ox, oy, pad=0.12):
    """Isometric box on tile (i, j) with height h."""
    a = iso(i + pad, j + pad, ox, oy)
    b = iso(i + 1 - pad, j + pad, ox, oy)
    c = iso(i + 1 - pad, j + 1 - pad, ox, oy)
    d = iso(i + pad, j + 1 - pad, ox, oy)
    up = lambda p: (p[0], p[1] - h)
    out = [
        poly([d, c, up(c), up(d)], shade(color, 0.72)),   # front-left face
        poly([b, c, up(c), up(b)], shade(color, 0.86)),   # front-right face
        poly([up(a), up(b), up(c), up(d)], shade(color, 1.18)),  # roof
    ]
    return "".join(out)


def text(x, y, s, fill, size=13, anchor="middle", weight="400"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{fill}" '
            f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">{escape(str(s))}</text>')


def radar(cx, cy, r, cats, counts, t):
    n = len(cats)
    mx = max(max(counts), 1)
    ang = lambda k: -math.pi / 2 + 2 * math.pi * k / n
    out = []
    for lvl in (0.25, 0.5, 0.75, 1.0):
        pts = [(cx + r * lvl * math.cos(ang(k)), cy + r * lvl * math.sin(ang(k))) for k in range(n)]
        out.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" '
                   f'fill="none" stroke="{t["grid"]}" stroke-dasharray="3 3"/>')
    for k in range(n):
        x, y = cx + r * math.cos(ang(k)), cy + r * math.sin(ang(k))
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{t["grid"]}" stroke-dasharray="3 3"/>')
        lx, ly = cx + (r + 22) * math.cos(ang(k)), cy + (r + 22) * math.sin(ang(k))
        anchor = "middle" if abs(math.cos(ang(k))) < 0.3 else ("start" if math.cos(ang(k)) > 0 else "end")
        out.append(text(lx, ly + 4, cats[k]["name"], t["text"], 12, anchor))
        out.append(text(lx, ly + 19, counts[k], cats[k]["color"], 12, anchor, "700"))
    pts = [(cx + r * (0.12 + 0.88 * counts[k] / mx) * math.cos(ang(k)),
            cy + r * (0.12 + 0.88 * counts[k] / mx) * math.sin(ang(k))) for k in range(n)]
    out.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" '
               f'fill="{t["radar_fill"]}" fill-opacity="0.35" stroke="{t["radar"]}" stroke-width="2.5"/>')
    return "".join(out)


def build(data, theme):
    global TW, TH
    t = THEMES[theme]
    cats = data["categories"]
    names = [c["name"] for c in cats]
    items = [it for it in data["items"] if it["cat"] in names]
    years = sorted({it["year"] for it in items})
    y0, y1 = years[0], years[-1]
    ncol, nrow = y1 - y0 + 1, len(cats)
    count = {}
    for it in items:
        key = (it["year"] - y0, names.index(it["cat"]))
        count[key] = count.get(key, 0) + 1

    # place the grid so it fits the left 62% of the canvas
    scale = min(1.0, 600 / ((ncol + nrow) * TW / 2))   # shrink tiles if many years
    TW, TH = 62 * scale, 31 * scale
    ox = 30 + nrow * TW / 2
    oy = 130
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" rx="12" fill="{t["bg"]}"/>',
         text(W - 20, 26, f"{y0} – {y1}", t["muted"], 12, "end"),
         text(30, 34, data.get("title", "Stats"), t["text"], 18, "start", "700")]
    # tiles
    for j in range(nrow):
        for i in range(ncol):
            pts = [iso(i, j, ox, oy), iso(i + 1, j, ox, oy), iso(i + 1, j + 1, ox, oy), iso(i, j + 1, ox, oy)]
            s.append(poly(pts, t["tile"], t["tile_edge"]))
    # buildings, back to front
    for j in range(nrow):
        for i in range(ncol):
            n = count.get((i, j), 0)
            if n:
                s.append(box(i, j, n * cats[j].get("unit", 20), cats[j]["color"], ox, oy))
    # year labels along the front-right edge
    for i in range(ncol):
        if (y0 + i) % 2 == 0 or ncol <= 8:
            x, y = iso(i + 0.5, nrow + 0.35, ox, oy)
            s.append(text(x, y + 10, y0 + i, t["muted"], 11))
    # category legend (bottom-left)
    lx, ly = 30, H - 24 - 20 * (nrow - 1)
    for j, c in enumerate(cats):
        s.append(f'<rect x="{lx}" y="{ly + 20 * j - 11}" width="13" height="13" rx="2" fill="{c["color"]}"/>')
        s.append(text(lx + 20, ly + 20 * j, c["name"], t["text"], 13, "start"))
    totals = [sum(1 for it in items if it["cat"] == c["name"]) for c in cats]
    s.append(radar(790, 215, 95, cats, totals, t))
    s.append(text(790, H - 28, f"{len(items)} {data.get('total_label', 'achievements unlocked')}", t["text"], 16, "middle", "600"))
    s.append("</svg>")
    return "\n".join(s)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "research.yml"
    out = sys.argv[2] if len(sys.argv) > 2 else "."
    data = yaml.safe_load(open(src, encoding="utf-8"))
    for theme, name in (("light", "research-city.svg"), ("dark", "research-city-dark.svg")):
        open(f"{out}/{name}", "w", encoding="utf-8").write(build(data, theme))
        print("wrote", name)


if __name__ == "__main__":
    main()
