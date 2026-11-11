# RoYoshi.github.io

RoYoshi's site on GitHub Pages: one page that describes every repository on this
account, public and private. Private repositories are described here, but their
source stays private.

## Files

| Path | What it is |
|---|---|
| `index.html` | The page. Built by `tools/build.py`; don't edit it by hand |
| `data/repos.json` | The content: each repository's description, what's inside, and its facts |
| `assets/style.css` | The look: FE-Xico Aurora colours, the family tree, the narrow-screen layout |
| `assets/icons/`, `assets/carpet.jpg`, `assets/favicon.png` | The apps' own icons, the Level 0 carpet and the top hat |
| `tools/build.py` | Writes `index.html` from the data |
| `.nojekyll` | Tells GitHub Pages to publish the files as they are |

## Changing the page

1. Edit `data/repos.json`: the text, the facts (dates, commit and pull request
   counts, license, release, language byte counts from the repository's
   Languages API) and `as_of`, the date the facts were taken.
2. Run `python3 tools/build.py`. It needs Pillow and GNU Unifont
   (Fedora: `unifont-fonts`, Debian/Ubuntu: `fonts-unifont`), because the
   headings are drawn from Unifont's pixels. Set `UNIFONT=/path/to/unifont.otf`
   if it is installed somewhere else.
3. Open `index.html` in a browser to check it, then commit both files.

## Publishing

In this repository's **Settings → Pages**, set **Source** to **Deploy from a
branch**, pick the branch and `/ (root)`, and save. The site appears at
https://royoshi.github.io a minute or two later.

## Credits

The headings are drawings made from GNU Unifont glyphs (Unifont is dual-licensed
under the SIL Open Font License 1.1 and the GNU GPL 2+ with the font embedding
exception); the page itself loads no fonts. The colours are FE-Xico Aurora's.
The icons belong to FE-XicoOS, FE-Xico UpdateR and FE-Xico Doctor.
