# RoYoshi.github.io

RoYoshi's site on GitHub Pages: one page about him, his projects (every repository
on this account, public and private), the skills behind them, his IT certifications
and his YouTube channel.
Private repositories are described here, but their source stays private.

## Files

| Path | What it is |
|---|---|
| `index.html` | The page. Built by `tools/build.py`; don't edit it by hand |
| `data/repos.json` | The content: the About section (roles and paragraphs); the prompt's lines (`terminal`) and the neofetch facts (`neofetch`); the Steam profile, its numbers and peak ranks (`steam`); the favourite games and characters (`favourites`); the skills, each with links to where they show on the page; each repository's description, what's inside and its facts; the certifications; the YouTube channel; the links at the top (a link whose `url` is `null`, such as Steam or Credly until they're filled in, is left off the page) |
| `assets/style.css` | The look: FE-Xico Aurora colours, the family tree, the narrow-screen layout, the hat on the name, the neofetch card, the Smiler |
| `assets/site.js` | The small things that move: the prompt typing under the name, sections rising into view, tipping the hat, and the `noclip` easter egg. The page reads the same without it |
| `assets/icons/`, `assets/carpet.jpg` | The apps' own icons and the Level 0 carpet. The Far Backrooms' icon loads from thefarbackrooms.com, with the carpet behind it |
| `assets/favicon.png`, `assets/apple-touch-icon.png`, `assets/og.png` | The tab icon, the home-screen icon and the picture shown when the page is shared; all drawn by `tools/build.py` |
| `404.html` | The page GitHub Pages shows for an address that isn't on the site. Built by `tools/build.py` |
| `robots.txt`, `sitemap.xml` | Point search engines at the page |
| `tools/build.py` | Writes `index.html`, `404.html` and the drawn images from the data |
| `.nojekyll` | Tells GitHub Pages to publish the files as they are |

## Changing the page

1. Edit `data/repos.json`: the text, the facts (dates, commit and pull request
   counts, license, release, language byte counts from the repository's
   Languages API) and `as_of`, the date the facts were taken.
2. Run `python3 tools/build.py`. It needs Pillow and GNU Unifont
   (Fedora: `unifont-fonts`, Debian/Ubuntu: `fonts-unifont`), because the
   headings are drawn from Unifont's pixels. Set `UNIFONT=/path/to/unifont.otf`
   if it is installed somewhere else.
3. Open `index.html` in a browser to check it, then commit it with the redrawn images.

## Publishing

In this repository's **Settings → Pages**, set **Source** to **Deploy from a
branch**, pick the branch and `/ (root)`, and save. The site appears at
https://royoshi.github.io a minute or two later.

## Credits

The headings are drawings made from GNU Unifont glyphs (Unifont is dual-licensed
under the SIL Open Font License 1.1 and the GNU GPL 2+ with the font embedding
exception); the page itself loads no fonts. The colours are FE-Xico Aurora's.
The icons belong to FE-XicoOS, FE-Xico UpdateR and FE-Xico Doctor.
