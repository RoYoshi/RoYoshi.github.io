#!/usr/bin/env python3
"""Builds index.html from data/repos.json.

Run from the repository root after changing the data:

    python3 tools/build.py

The headings are drawn pixel by pixel from GNU Unifont glyphs (the bitmap look of
the FE-XicoOS desktop) and written into the page as small SVGs, so the site loads no
font files. Building needs Pillow and Unifont's OTF file; set UNIFONT=/path/to/unifont.otf
if it is not in a usual place (Fedora: unifont-fonts, Debian/Ubuntu: fonts-unifont).
GNU Unifont is dual-licensed under the SIL Open Font License 1.1 and the GNU GPL 2+
with the font embedding exception; the page contains drawings made with it, not the font.
"""
from __future__ import annotations

import datetime
import html
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/repos.json"
OUT = ROOT / "index.html"
UNIFONT_PATHS = [
    os.environ.get("UNIFONT", ""),
    "/usr/share/fonts/opentype/unifont/unifont.otf",
    "/usr/share/fonts/unifont/unifont.otf",
    "/usr/share/fonts/unifont/unifont.ttf",
]
# Language bar colours, in order: Aurora's interaction green and structure magenta,
# then its main and secondary text, then a dim grey for everything else.
LANGUAGE_COLOURS = ["#00FF00", "#FF00FF", "#E8EFEB", "#8D9C98"]
OTHER_COLOUR = "#4A504E"


def unifont() -> ImageFont.FreeTypeFont:
    for path in UNIFONT_PATHS:
        if path and Path(path).is_file():
            return ImageFont.truetype(path, 16)
    raise SystemExit("GNU Unifont not found: install it, or set UNIFONT=/path/to/unifont.otf")


FONT = unifont()


def bitmap(text: str) -> tuple[list[list[bool]], int, int]:
    """The text's pixels at Unifont's own size (16 px), cropped to its ink rows."""
    width = round(FONT.getlength(text))
    image = Image.new("1", (width, 18), 0)
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"  # no anti-aliasing: the real bitmap
    draw.text((0, 0), text, font=FONT, fill=1)
    rows = [[bool(image.getpixel((x, y))) for x in range(width)] for y in range(image.height)]
    inked = [y for y, row in enumerate(rows) if any(row)]
    top, bottom = (inked[0], inked[-1]) if inked else (0, 0)
    # Trim the empty column Unifont leaves on the right of the last glyph.
    while width > 1 and not any(rows[y][width - 1] for y in range(top, bottom + 1)):
        width -= 1
    return [row[:width] for row in rows[top:bottom + 1]], width, top


def runs(rows: list[list[bool]], keep) -> str:
    """An SVG path of horizontal runs of the pixels for which keep(x, y) is true."""
    parts = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            if row[x] and keep(x, y):
                start = x
                while x < len(row) and row[x] and keep(x, y):
                    x += 1
                parts.append(f"M{start} {y}h{x - start}v1h{start - x}z")
            else:
                x += 1
    return "".join(parts)


def pixel_svg(text: str, css_class: str, glow_dot: bool = False) -> str:
    """The text as crisp pixels. glow_dot: the dot of a final "i" is drawn apart (in
    the FE-Xico wordmark that dot is a glowing green light)."""
    rows, width, _ = bitmap(text)
    dot: set[tuple[int, int]] = set()
    if glow_dot and text.endswith("i"):
        start = round(FONT.getlength(text[:-1]))
        columns = range(start, width)
        inked = [y for y, row in enumerate(rows) if any(row[x] for x in columns)]
        y = inked[0]
        while y < len(rows) and any(rows[y][x] for x in columns):
            dot.update((x, y) for x in columns if rows[y][x])
            y += 1
    body = runs(rows, lambda x, y: (x, y) not in dot)
    lit = ""
    if dot:
        # The light: a soft green halo behind the dot, then the dot itself.
        cx = sum(x for x, _ in dot) / len(dot) + 0.5
        cy = sum(y for _, y in dot) / len(dot) + 0.5
        glow = f"glow-{css_class}"
        lit = (f'<radialGradient id="{glow}"><stop offset="0" stop-color="#00FF00" stop-opacity="0.55"/>'
               f'<stop offset="0.45" stop-color="#00FF00" stop-opacity="0.16"/>'
               f'<stop offset="1" stop-color="#00FF00" stop-opacity="0"/></radialGradient>'
               f'<circle class="halo" cx="{cx:g}" cy="{cy:g}" r="3.5" fill="url(#{glow})" shape-rendering="auto"/>'
               f'<path class="dot" d="{runs(rows, lambda x, y: (x, y) in dot)}"/>')
    return (f'<svg class="pixel {css_class}" viewBox="0 0 {width} {len(rows)}" '
            f'style="--w:{width};--h:{len(rows)}" aria-hidden="true" focusable="false" '
            f'shape-rendering="crispEdges"><path d="{body}"/>{lit}</svg>')


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def date(value: str) -> str:
    day = datetime.date.fromisoformat(value)
    return f"{day:%B} {day.day}, {day.year}"


def slug(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in text).strip("-")


def languages(counts: dict[str, int]) -> str:
    total = sum(counts.values())
    ranked = sorted(counts.items(), key=lambda item: -item[1])
    # Up to four languages of at least 1 % each; the rest together as Other.
    shown = [item for item in ranked if item[1] / total >= 0.01][:4]
    rest = ranked[len(shown):]
    entries = [(name, value, LANGUAGE_COLOURS[i]) for i, (name, value) in enumerate(shown)]
    if rest:
        entries.append(("Other", sum(value for _, value in rest), OTHER_COLOUR))

    def percent(value: int) -> str:
        share = value / total * 100
        return "under 1%" if share < 1 else f"{round(share)}%"

    bar = "".join(f'<span style="--share:{value / total:.4f};--colour:{colour}"></span>'
                  for _, value, colour in entries)
    legend = "".join(f'<li><span class="swatch" style="--colour:{colour}"></span>{esc(name)} {percent(value)}</li>'
                     for name, value, colour in entries)
    others = f' (other: {esc(", ".join(name for name, _ in rest))})' if rest else ""
    return (f'<div class="bar" aria-hidden="true">{bar}</div>'
            f'<ul class="legend" aria-label="Languages by share of code{others}">{legend}</ul>')


def facts(repo: dict) -> str:
    f = repo["facts"]
    items = []
    if f.get("languages"):
        items.append(("Languages", languages(f["languages"])))
    items.append(("Started", esc(date(f["created"]))))
    items.append(("Last change", esc(date(f["pushed"]))))
    if f.get("commits") is not None:
        note = f' <span class="aside">({esc(f["commits_note"])})</span>' if f.get("commits_note") else ""
        items.append(("Commits on main", f'{f["commits"]:,}{note}'))
    if f.get("pulls") is not None:
        items.append(("Pull requests", f'{f["pulls"]:,}'))
    items.append(("License", esc(f["licence"]) if f.get("licence") else "None chosen yet"))
    if f.get("release"):
        release = f["release"]
        items.append(("Latest release", f'<a href="{esc(release["url"])}">{esc(release["name"])}</a>, {esc(date(release["date"]))}'))
    elif f.get("commits") is not None:
        items.append(("Latest release", "None yet"))
    rows = "".join(f"<dt>{term}</dt><dd>{value}</dd>" for term, value in items)
    return f'<dl class="facts">{rows}</dl>'


def mark(repo: dict) -> str:
    icon = repo.get("icon")
    if icon == "carpet":
        return '<div class="repo__mark repo__mark--carpet"></div>'
    if icon:
        return f'<div class="repo__mark"><img src="{esc(icon)}" alt="" width="96" height="96"></div>'
    # No icon of its own: the lit "i" of the heading above, in a panel-black square.
    return f'<div class="repo__mark repo__mark--pixel">{pixel_svg("i", "pixel--mark", glow_dot=True)}</div>'


def article(repo: dict, root: bool = False) -> str:
    key = slug(repo["name"])
    url = f'https://github.com/{repo["repo"]}'
    if repo["private"]:
        where = f'Private repository <span class="path">{esc(repo["repo"])}</span>. Its source isn\'t public.'
    else:
        where = f'Public repository <a class="path" href="{esc(url)}">{esc(repo["repo"])}</a>'
    paragraphs = "".join(f"<p>{esc(text)}</p>" for text in repo["summary"])
    inside = ""
    if repo.get("inside"):
        inside = '<ul class="inside">' + "".join(f"<li>{esc(item)}</li>" for item in repo["inside"]) + "</ul>"
    classes = "repo repo--root" if root else "repo"
    return (f'<article class="{classes}" id="{key}" aria-labelledby="{key}-name">{mark(repo)}'
            f'<div class="repo__body">'
            f'<h3 class="repo__name" id="{key}-name"><span class="visually-hidden">{esc(repo["name"])}</span>'
            f'{pixel_svg(repo["name"], "pixel--name")}</h3>'
            f'<p class="where">{where}</p>{paragraphs}{inside}{facts(repo)}</div></article>')


def group(data: dict) -> str:
    key = f'g-{data["id"]}'
    note = f'<p class="note">{esc(data["note"])}</p>' if data.get("note") else ""
    roots = [r for r in data["repos"] if r["role"] == "root"]
    children = [r for r in data["repos"] if r["role"] == "child"]
    singles = [r for r in data["repos"] if r["role"] == "single"]
    body = "".join(article(r, root=True) for r in roots)
    if children:
        body += '<ul class="tree">' + "".join(f"<li>{article(r)}</li>" for r in children) + "</ul>"
    body += "".join(article(r) for r in singles)
    return (f'<section class="group group--{esc(data["id"])}" aria-labelledby="{key}">'
            f'<h2 id="{key}">{esc(data["title"])}</h2>{note}{body}</section>')


def page(data: dict) -> str:
    count = sum(len(g["repos"]) for g in data["groups"])
    private = sum(1 for g in data["groups"] for r in g["repos"] if r["private"])
    groups = "".join(group(g) for g in data["groups"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(data["owner"])}: repositories</title>
<meta name="description" content="{esc(data["intro"])}">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#000000">
<link rel="icon" type="image/png" href="assets/favicon.png">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<a class="skip" href="#main">Skip to the repositories</a>
<header class="masthead">
<h1><span class="visually-hidden">{esc(data["owner"])}</span>{pixel_svg(data["owner"], "pixel--hero", glow_dot=True)}</h1>
<p class="intro">{esc(data["intro"])}</p>
<p class="profile"><a href="{esc(data["profile"])}">github.com/{esc(data["owner"])}</a>, with {count} repositories, {private} of them private.</p>
</header>
<main id="main">
{groups}
</main>
<footer class="colophon">
<p>Facts as of {esc(date(data["as_of"]))}. Private repositories are described here, but their source stays private.</p>
<p>Headings are drawn from GNU Unifont glyphs. The colours are FE-Xico Aurora's, and the icons are the apps' own.</p>
</footer>
</body>
</html>
"""


def main() -> None:
    data = json.loads(DATA.read_text())
    OUT.write_text(page(data))
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
