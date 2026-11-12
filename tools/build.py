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

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/repos.json"
OUT = ROOT / "index.html"
SITE = "https://royoshi.github.io/"
# Aurora's colours, for the images the build draws (the sharing card, the favicon).
BLACK, TEXT, MUTED, MAGENTA, GREEN = (0, 0, 0), (232, 239, 235), (141, 156, 152), (255, 0, 255), (0, 255, 0)
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


def heading(key: str, number: int, title: str) -> str:
    """A section heading: its number drawn in magenta pixels, then its title."""
    return (f'<h2 id="{key}"><span class="h2__index">{pixel_svg(f"{number:02d}", "pixel--index")}</span>'
            f'<span class="h2__title">{esc(title)}</span></h2>')


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
    if f.get("license_text"):
        parts = f["license_text"] if isinstance(f["license_text"], list) else [f["license_text"]]
        items.append(("License", "<br>".join(esc(part) for part in parts)))
    else:
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
    if icon and repo.get("icon_backdrop") == "carpet":
        # The game's own icon, from its website, on the carpet (shown if it can't load).
        return (f'<div class="repo__mark repo__mark--carpet"><img src="{esc(icon)}" alt="" width="96" height="96" '
                f'loading="lazy" decoding="async" onerror="this.remove()"></div>')
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
    credits = f'<p class="credits">{esc(repo["credits"])}</p>' if repo.get("credits") else ""
    # The game's extras: the rule its monsters live by, who hunts you, and how it's built.
    rule = ""
    if repo.get("rule"):
        rule = (f'<blockquote class="rule"><p>{esc(repo["rule"])}</p>'
                f'<footer>The one rule every monster follows</footer></blockquote>')
    entities = ""
    if repo.get("entities"):
        entities = ('<h4 class="sub">Who hunts you</h4><ul class="entities">' + "".join(
            f'<li class="entity entity--{slug(e["name"])}"><span class="entity__name">'
            f'<span class="visually-hidden">{esc(e["name"])}</span>{pixel_svg(e["name"], "pixel--cert")}</span>'
            f'<span class="entity__line">{esc(e["line"])}</span></li>' for e in repo["entities"]) + "</ul>")
    features = ""
    if repo.get("features"):
        features = ('<h4 class="sub">How it\'s built</h4><ul class="features">'
                    + "".join(f"<li>{esc(item)}</li>" for item in repo["features"]) + "</ul>")
    links = ""
    if repo.get("links"):
        links = '<ul class="links">' + "".join(
            f'<li><a class="{"cta" if link.get("primary") else ""}" href="{esc(link["url"])}">{esc(link["text"])}</a></li>'
            for link in repo["links"]) + "</ul>"
    classes = "repo repo--root" if root else "repo"
    return (f'<article class="{classes}" id="{key}" aria-labelledby="{key}-name">{mark(repo)}'
            f'<div class="repo__body">'
            f'<h3 class="repo__name" id="{key}-name"><span class="visually-hidden">{esc(repo["name"])}</span>'
            f'{pixel_svg(repo["name"], "pixel--name")}</h3>'
            f'<p class="where">{where}</p>{paragraphs}{rule}{entities}{features}{credits}{links}{inside}{facts(repo)}</div></article>')


SMILER = ('<div class="smiler" aria-hidden="true"><svg viewBox="0 0 120 60">'
          '<ellipse cx="38" cy="16" rx="7" ry="4.5"/><ellipse cx="82" cy="16" rx="7" ry="4.5"/>'
          '<path d="M14 30 Q60 70 106 30 Q60 52 14 30Z"/>'
          '<path class="teeth" d="M24 35v6M33 39v7M42 42v7M51 44v7M60 44v8M69 44v7M78 42v7M87 39v7M96 35v6"/>'
          '</svg></div>')


def group(data: dict, number: int) -> str:
    key = f'g-{data["id"]}'
    note = f'<p class="note">{esc(data["note"])}</p>' if data.get("note") else ""
    roots = [r for r in data["repos"] if r["role"] == "root"]
    children = [r for r in data["repos"] if r["role"] == "child"]
    singles = [r for r in data["repos"] if r["role"] == "single"]
    body = "".join(article(r, root=True) for r in roots)
    if children:
        body += '<ul class="tree">' + "".join(f"<li>{article(r)}</li>" for r in children) + "</ul>"
    body += "".join(article(r) for r in singles)
    # Level 0 around the game: fluorescent lights above, wallpaper behind, carpet below.
    room = ('<div class="room" aria-hidden="true"><span class="light"></span><span class="light"></span>'
            '<span class="light light--bad"></span><span class="light"></span></div>') if data["id"] == "game" else ""
    return (f'<section class="group group--{esc(data["id"])}" aria-labelledby="{key}">{room}'
            f'{heading(key, number, data["title"])}{note}{body}{SMILER if data["id"] == "game" else ""}</section>')


def certifications(data: dict, number: int) -> str:
    """The certifications: CompTIA's and Cisco's, then the stackables, each shown with
    the certifications it is made of (pointing at one lights those up)."""
    certs = data["certifications"]
    names = {c["id"]: c["short"] for g in certs["groups"] for c in g["certs"]}
    verify = ""
    if certs.get("verify_url"):
        verify = f' <a href="{esc(certs["verify_url"])}">Check them on Credly</a>.'
    blocks = []
    for g in certs["groups"]:
        rows = "".join(
            f'<li class="cert cert--{esc(c["id"])}" id="cert-{esc(c["id"])}"><span class="cert__label"><span class="visually-hidden">{esc(c["short"])}</span>'
            f'{pixel_svg(c["short"], "pixel--cert")}</span>'
            f'<span class="cert__text"><strong>{esc(c["name"])}</strong> <span class="cert__scope">{esc(c["scope"])}</span></span></li>'
            for c in g["certs"])
        blocks.append(f'<h3 class="certs__issuer">{esc(g["title"])}</h3><ul class="certs__list">{rows}</ul>')
    stacks = "".join(
        f'<li class="stack {" ".join("uses-" + esc(u) for u in s["uses"])}"><span class="stack__name">{esc(s["name"])}</span>'
        f'<span class="stack__parts" aria-label="for holding {esc(", ".join(names[u] for u in s["uses"]))}">'
        + "".join(f'<span class="part" aria-hidden="true">{esc(names[u])}</span>' for u in s["uses"]) + "</span></li>"
        for s in certs["stackables"])
    blocks.append(f'<h3 class="certs__issuer">{esc(certs["stackables_title"])}</h3><ul class="stacks">{stacks}</ul>')
    return (f'<section class="group group--certs certs" id="certifications" aria-labelledby="g-certs">'
            f'{heading("g-certs", number, "Certifications")}<p class="note">{esc(certs["note"])}{verify}</p>{"".join(blocks)}</section>')


def youtube(data: dict, number: int) -> str:
    yt = data["youtube"]
    return (f'<section class="group group--youtube" id="youtube" aria-labelledby="g-youtube">'
            f'{heading("g-youtube", number, yt["title"])}'
            f'<div class="channel"><h3 class="channel__name"><span class="visually-hidden">{esc(yt["handle"])}</span>'
            f'{pixel_svg(yt["handle"], "pixel--name")}</h3>'
            f'<p>{esc(yt["summary"])}</p>'
            f'<ul class="links"><li><a class="cta cta--video" href="{esc(yt["url"])}">Watch on YouTube</a></li></ul></div></section>')


def about(data: dict, number: int) -> str:
    a = data["about"]
    links = a.get("role_links", {})
    roles = "".join(f'<li><a href="{esc(links[role])}">{esc(role)}</a></li>' if role in links else f"<li>{esc(role)}</li>"
                    for role in a["roles"])
    text = "".join(f"<p>{esc(p)}</p>" for p in a["paragraphs"])
    t = data["terminal"]
    title = f'{t["user"]}@{t["host"]}'
    rows = "".join(f'<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k, v in data["neofetch"])
    swatches = "".join(f'<span style="--colour:{c}"></span>'
                       for c in ("#000000", "#FF00FF", "#00FF00", "#D8C46A", "#8D9C98", "#E8EFEB"))
    # A neofetch, as on the FE-XicoOS desktop: the mark, then the facts.
    fetch = (f'<figure class="fetch" aria-label="RoYoshi at a glance">'
             f'<div class="fetch__bar" aria-hidden="true"><span></span><span></span><span></span>'
             f'<span class="fetch__title">Foot: ~</span></div>'
             f'<div class="fetch__body"><p class="fetch__cmd" aria-hidden="true">'
             f'<span class="p-user">{esc(title)}</span>:<span class="p-path">~</span>$ neofetch</p>'
             f'<div class="fetch__out"><img class="fetch__hat" src="assets/icons/fe-xicoos.png" alt="" width="96" height="96">'
             f'<div><p class="fetch__who"><span class="p-user">{esc(t["user"])}</span>@<span class="p-host">{esc(t["host"])}</span></p>'
             f'<p class="fetch__rule" aria-hidden="true">{"-" * len(title)}</p>'
             f'<dl>{rows}</dl><p class="fetch__swatches" aria-hidden="true">{swatches}</p></div></div></div></figure>')
    return (f'<section class="group group--about" id="about" aria-labelledby="g-about">'
            f'{heading("g-about", number, "About")}<ul class="roles" aria-label="Roles">{roles}</ul>'
            f'<div class="about"><div class="about__text">{text}</div>{fetch}</div></section>')


def skills(data: dict, number: int) -> str:
    """Skill areas, each with its tools and links to where on the page it shows."""
    sk = data["skills"]
    rows = "".join(
        f'<li class="skill"><span class="skill__name">{esc(area["name"])}</span>'
        f'<span class="skill__body"><span class="skill__items">'
        + "".join(f'<span class="part">{esc(item)}</span>' for item in area["items"])
        + '</span><span class="skill__seen">Seen in '
        + ", ".join(f'<a href="{esc(href)}">{esc(text)}</a>' for text, href in area["seen"])
        + "</span></span></li>"
        for area in sk["areas"])
    return (f'<section class="group group--skills" id="skills" aria-labelledby="g-skills">'
            f'{heading("g-skills", number, sk["title"])}<p class="note">{esc(sk["note"])}</p>'
            f'<ul class="skills">{rows}</ul></section>')


def steam(data: dict, number: int) -> str:
    """The Steam profile: its numbers drawn in pixels, then the peak ranks."""
    st = data["steam"]
    stats = "".join(
        f'<li class="stat"><span class="stat__value"><span class="visually-hidden">{esc(value)}</span>'
        f'{pixel_svg(value, "pixel--stat")}</span><span class="stat__label">{esc(label)}</span></li>'
        for value, label in st["stats"])
    ranks = "".join(
        f'<li class="cert"><span class="cert__label"><span class="visually-hidden">{esc(rank)}</span>'
        f'{pixel_svg(rank, "pixel--cert")}</span>'
        f'<span class="cert__text"><strong>{esc(game)}</strong>'
        + (f' <span class="cert__scope">{esc(note)}</span>' if note else "") + "</span></li>"
        for rank, game, note in st["ranks"])
    return (f'<section class="group group--steam" id="steam" aria-labelledby="g-steam">'
            f'{heading("g-steam", number, st["title"])}<p class="steam__summary">{esc(st["summary"])}</p>'
            f'<ul class="stats" aria-label="Steam in numbers">{stats}</ul>'
            f'<h3 class="certs__issuer">{esc(st["ranks_title"])}</h3><ul class="certs__list">{ranks}</ul>'
            f'<ul class="links"><li><a class="cta" href="{esc(st["url"])}">See the profile on Steam</a></li></ul></section>')


def yexico(data: dict, number: int) -> str:
    """YEXICO, the community RoYoshi is president of: its flag, motto, numbers and a photo."""
    y = data["yexico"]
    stats = "".join(
        f'<li class="stat"><span class="stat__value"><span class="visually-hidden">{esc(value)}</span>'
        f'{pixel_svg(value, "pixel--stat")}</span><span class="stat__label">{esc(label)}</span></li>'
        for value, label in y["stats"])
    text = "".join(f"<p>{esc(p)}</p>" for p in y["summary"])
    links = '<ul class="links">' + "".join(
        f'<li><a class="{"cta" if link.get("primary") else ""}" href="{esc(link["url"])}">{esc(link["text"])}</a></li>'
        for link in y["links"]) + "</ul>"
    photo = y["photo"]
    anthem = ""
    if y.get("anthem"):
        vid = y["anthem"]
        # A still and a link until clicked (assets/site.js swaps in the player), so the page
        # loads nothing from YouTube but the picture, and works as a plain link without the script.
        anthem = (f'<figure class="anthem">'
                  f'<a class="video" href="https://www.youtube.com/watch?v={esc(vid["id"])}" data-video="{esc(vid["id"])}" '
                  f'data-title="{esc(vid["title"])}"><img src="https://i.ytimg.com/vi/{esc(vid["id"])}/hqdefault.jpg" alt="" '
                  f'width="480" height="360" loading="lazy" decoding="async"><span class="video__play" aria-hidden="true"></span>'
                  f'<span class="visually-hidden">Play {esc(vid["title"])}</span></a>'
                  f'<figcaption>The anthem: {esc(vid["title"])}, on his channel.</figcaption></figure>')
    return (f'<section class="group group--yexico" id="yexico" aria-labelledby="g-yexico">'
            f'{heading("g-yexico", number, y["title"])}'
            f'<div class="yexico"><div class="flagpole"><img class="flag" src="{esc(y["flag"])}" '
            f'alt="The YEXICO flag: green, white and green, with a smile in the middle" width="640" height="320"></div>'
            f'<div class="yexico__text"><p class="motto">{esc(y["motto"]).replace(" :(", '&nbsp;<span class="nowrap">:(</span>')}</p>{text}'
            f'<p class="president">President: <strong>{esc(data["owner"])}</strong>, 2023 to now</p>{links}</div></div>'
            f'<ul class="stats stats--yexico" aria-label="YEXICO in numbers">{stats}</ul>'
            f'<div class="media">{anthem}'
            f'<figure class="photo"><img src="{esc(photo["src"])}" alt="{esc(photo["alt"])}" width="{photo["width"]}" '
            f'height="{photo["height"]}" loading="lazy" decoding="async"><figcaption>{esc(photo["caption"])}</figcaption></figure></div>'
            f'</section>')


def favourites(data: dict, number: int) -> str:
    """Favourite games and characters as a character-select screen, then a text box."""
    fav = data["favourites"]
    lists = []
    for group_ in fav["lists"]:
        tiles = "".join(
            f'<li class="pick">'
            + (f'<span class="pick__badge">{esc(item["badge"])}</span>' if item.get("badge") else "")
            + f'<span class="pick__name"><span class="visually-hidden">{esc(item["name"])}</span>'
            f'{pixel_svg(item["name"], "pixel--cert")}</span>'
            f'<span class="pick__line">{esc(item["line"])}</span></li>'
            for item in group_["items"])
        lists.append(f'<h3 class="certs__issuer">{esc(group_["title"])}</h3>'
                     f'<ul class="picks picks--{slug(group_["title"])}">{tiles}</ul>')
    box = f'<p class="textbox">{esc(fav["box"])}</p>' if fav.get("box") else ""
    return (f'<section class="group group--favourites" id="favourites" aria-labelledby="g-favourites">'
            f'{heading("g-favourites", number, fav["title"])}<p class="note">{esc(fav["note"])}</p>'
            f'{"".join(lists)}{box}</section>')


def person(data: dict) -> str:
    """Structured data for search engines: who the page is about, and where else to find him."""
    same = [link["url"] for link in data["links"] if link.get("url")]
    info = {"@context": "https://schema.org", "@type": "Person", "name": data["owner"], "url": SITE,
            "jobTitle": ", ".join(data["about"]["roles"]), "sameAs": same,
            "knowsAbout": [item for area in data["skills"]["areas"] for item in area["items"]]}
    return json.dumps(info, ensure_ascii=False).replace("</", "<\\/")


def page(data: dict) -> str:
    count = sum(len(g["repos"]) for g in data["groups"])
    private = sum(1 for g in data["groups"] for r in g["repos"] if r["private"])
    projects = [g for g in data["groups"] if g["id"] != "site"]
    site = [g for g in data["groups"] if g["id"] == "site"]
    builders = ([lambda n: about(data, n)] + [lambda n, g=g: group(g, n) for g in projects]
                + [lambda n: skills(data, n), lambda n: certifications(data, n), lambda n: youtube(data, n),
                   lambda n: steam(data, n), lambda n: yexico(data, n),
                   lambda n: favourites(data, n)]
                + [lambda n, g=g: group(g, n) for g in site])
    groups = "\n".join(build(number) for number, build in enumerate(builders, 1))
    # Links without an address yet (filled in data/repos.json) are left out.
    elsewhere = "".join(f'<li><a href="{esc(link["url"])}">{esc(link["text"])}</a></li>'
                        for link in data["links"] if link.get("url"))
    total_certs = sum(len(g["certs"]) for g in data["certifications"]["groups"]) + len(data["certifications"]["stackables"])
    jumps = [("#about", "About"), ("#g-fe-xico", "FE-XicoOS"), ("#g-game", "The Far Backrooms"),
             ("#skills", "Skills"), ("#certifications", "Certifications"), ("#youtube", "On YouTube"), ("#steam", "On Steam"), ("#yexico", "YEXICO"),
             ("#favourites", "Favourites")]
    t = data["terminal"]
    # A shell prompt on RoYoshi's own machine; the script types the lines in turn.
    prompt = (f'<p class="prompt"><span class="p-user">{esc(t["user"])}@{esc(t["host"])}</span>:<span class="p-path">~</span>$ '
              f'<span class="prompt__cmd" data-lines="{esc(json.dumps(t["lines"]))}">{esc(t["lines"][0])}</span>'
              f'<span class="cursor" aria-hidden="true"></span></p>')
    nav = "".join(f'<li><a href="{href}">{esc(text)}</a></li>' for href, text in jumps)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(data["owner"])}: projects, certifications and videos</title>
<meta name="description" content="{esc(data["intro"])}">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#000000">
<link rel="canonical" href="{SITE}">
<link rel="icon" type="image/png" sizes="64x64" href="assets/favicon.png">
<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(data["owner"])}">
<meta property="og:title" content="{esc(data["owner"])}: projects, certifications and videos">
<meta property="og:description" content="{esc(data["intro"])}">
<meta property="og:url" content="{SITE}">
<meta property="og:image" content="{SITE}assets/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(data["owner"])}, drawn in pixels, with the FE-XicoOS, FE-Xico UpdateR and FE-Xico Doctor icons and the Level 0 carpet">
<meta name="twitter:card" content="summary_large_image">
<meta name="author" content="{esc(data["owner"])}">
<link rel="stylesheet" href="assets/style.css">
<script type="application/ld+json">{person(data)}</script>
<script src="assets/site.js" defer></script>
</head>
<body>
<a class="skip" href="#main">Skip to the content</a>
<header class="masthead" id="top">
<h1 class="hero"><span class="visually-hidden">{esc(data["owner"])}</span><img class="hat" src="assets/icons/fe-xicoos.png" alt="" width="192" height="192">{pixel_svg(data["owner"], "pixel--hero", glow_dot=True)}</h1>
{prompt}
<p class="intro">{esc(data["intro"])}</p>
<ul class="elsewhere">{elsewhere}</ul>
<p class="profile">{count} repositories ({private} of them private) and {total_certs} certifications.</p>
<nav class="jump" aria-label="On this page"><ul>{nav}</ul></nav>
</header>
<main id="main">
{groups}
</main>
<footer class="colophon">
<ul class="elsewhere elsewhere--footer">{elsewhere}<li><a href="#top">Back to the top</a></li></ul>
<p>Facts as of {esc(date(data["as_of"]))}. Private repositories are described here, but their source stays private.</p>
<p>Headings are drawn from GNU Unifont glyphs. The colours are FE-Xico Aurora's, and the icons are the apps' own.</p>
<p>&copy; {esc(data["as_of"][:4])} {esc(data["owner"])}. <span class="hint">Psst: type <kbd>noclip</kbd>.</span></p>
</footer>
</body>
</html>
"""


def not_found(data: dict) -> str:
    """GitHub Pages shows 404.html for any address that isn't on the site."""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Not found: {esc(data["owner"])}</title>
<meta name="robots" content="noindex">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#000000">
<link rel="icon" type="image/png" sizes="64x64" href="/assets/favicon.png">
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<main class="lost">
<h1><span class="visually-hidden">404</span>{pixel_svg("404", "pixel--hero")}</h1>
<p class="intro">You noclipped out of the page. There's nothing at this address, only the hum of the fluorescent lights.</p>
<ul class="links"><li><a class="cta" href="/">Back to {esc(data["owner"])}</a></li></ul>
</main>
</body>
</html>
"""


def paint(image: Image.Image, text: str, x: int, y: int, scale: int, glow_dot: bool = False) -> tuple[int, int]:
    """Draws the text's pixels at scale; returns its size. The dot of a final "i" is lit."""
    rows, width, _ = bitmap(text)
    draw = ImageDraw.Draw(image)
    start = round(FONT.getlength(text[:-1])) if glow_dot and text.endswith("i") else width
    dot_rows = set()
    if start < width:
        y0 = next(r for r, row in enumerate(rows) if any(row[start:]))
        while y0 < len(rows) and any(rows[y0][start:]):
            dot_rows.add(y0)
            y0 += 1
    for r, row in enumerate(rows):
        for c, on in enumerate(row):
            if on:
                lit = c >= start and r in dot_rows
                draw.rectangle([x + c * scale, y + r * scale, x + (c + 1) * scale - 1, y + (r + 1) * scale - 1],
                               fill=GREEN if lit else TEXT)
    return width * scale, len(rows) * scale


def halo(image: Image.Image, text: str, x: int, y: int, scale: int) -> None:
    """A soft green light around the dot of the final "i" (drawn before the pixels)."""
    rows, width, _ = bitmap(text)
    start = round(FONT.getlength(text[:-1]))
    r0 = next(r for r, row in enumerate(rows) if any(row[start:]))
    c0 = next(c for c in range(start, width) if rows[r0][c])
    cx, cy = x + (c0 + 0.5) * scale, y + (r0 + 1) * scale
    light = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(light).ellipse([cx - 3 * scale, cy - 3 * scale, cx + 3 * scale, cy + 3 * scale], fill=GREEN + (150,))
    light = light.filter(ImageFilter.GaussianBlur(scale * 1.6))
    image.alpha_composite(light)


def favicon() -> None:
    """RoYoshi's mark, the FE-Xico hat: on its own for the browser tab, and on panel
    black for the home screen (which would fill a see-through corner with its own colour)."""
    hat = Image.open(ROOT / "assets/icons/fe-xicoos.png").convert("RGBA")
    hat = hat.crop(hat.getbbox())
    for size, name, backdrop, fill in ((64, "favicon.png", None, 1.0), (180, "apple-touch-icon.png", BLACK, 0.78)):
        image = Image.new("RGBA", (size, size), (backdrop or BLACK) + (255 if backdrop else 0,))
        fit = round(size * fill)
        scale = fit / max(hat.size)
        mark = hat.resize((round(hat.width * scale), round(hat.height * scale)), Image.LANCZOS)
        image.alpha_composite(mark, ((size - mark.width) // 2, (size - mark.height) // 2))
        (image if backdrop is None else image.convert("RGB")).save(ROOT / "assets" / name, optimize=True)


def card(data: dict) -> None:
    """The picture shown when the page is shared (1200 x 630)."""
    image = Image.new("RGBA", (1200, 630), BLACK + (255,))
    scale = 13
    halo(image, data["owner"], 96, 120, scale)
    paint(image, data["owner"], 96, 120, scale, glow_dot=True)
    draw = ImageDraw.Draw(image)
    draw.line([(0, 380), (1200, 380)], fill=MAGENTA, width=2)
    x = 96
    for path in ("assets/icons/fe-xicoos.png", "assets/icons/fe-xico-updater.png", "assets/icons/fe-xico-doctor.png"):
        icon = Image.open(ROOT / path).convert("RGBA").resize((128, 128), Image.LANCZOS)
        image.alpha_composite(icon, (x, 430))
        x += 168
    carpet = Image.open(ROOT / "assets/carpet.jpg").convert("RGBA").resize((128, 128), Image.LANCZOS)
    image.alpha_composite(carpet, (x, 430))
    image.convert("RGB").save(ROOT / "assets/og.png", optimize=True)


def main() -> None:
    data = json.loads(DATA.read_text())
    OUT.write_text(page(data))
    (ROOT / "404.html").write_text(not_found(data))
    favicon()
    card(data)
    print(f"wrote {OUT.relative_to(ROOT)}, 404.html, assets/favicon.png, assets/apple-touch-icon.png, assets/og.png")


if __name__ == "__main__":
    main()
