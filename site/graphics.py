#!/usr/bin/env python3
"""Render original product graphics for the site and for pins.

Amazon's Associates policies only license product images for display through
Amazon's own tools/API, so the site and social posts use these original
graphics instead of Amazon-hosted photos.

For each product with a `graphic` block ({label, headline, points[3]}) this writes:
  public/img/<ASIN>.png     1000x1500 pin graphic (Pinterest 2:3)
  public/img/<ASIN>-sq.png   800x800 square card for the landing page

Requires Pillow (`pip install pillow`). Fonts are bundled in fonts/.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FONTS = ROOT / "fonts"
ORANGE, CREAM, INK, MUTED = (200, 100, 59), (251, 248, 243), (43, 38, 34), (111, 102, 93)
ACCENTS = {  # one accent per category so the grid reads as a set
    "organization": (93, 125, 110),
    "gadgets": (176, 122, 72),
    "appliances": (88, 105, 140),
    "drinkware": (64, 112, 150),
}


def _font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def _wrap(draw, text, font, width):
    """Greedy word wrap; honours explicit newlines."""
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            test = f"{line} {word}".strip()
            if draw.textlength(test, font=font) <= width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        lines.append(line)
    return lines


def _fit(draw, text, name, size, width, max_lines, min_size=24):
    """Largest font size (stepping down) at which text wraps into max_lines."""
    while size > min_size:
        f = _font(name, size)
        lines = _wrap(draw, text, f, width)
        if len(lines) <= max_lines and all(draw.textlength(l, font=f) <= width for l in lines):
            return f, lines
        size -= 2
    f = _font(name, min_size)
    return f, _wrap(draw, text, f, width)


def _check(draw, cx, cy, r):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ORANGE)
    draw.line([(cx - r * .45, cy), (cx - r * .1, cy + r * .4), (cx + r * .5, cy - r * .35)], fill="white", width=max(3, r // 5))


def pin_graphic(g, accent, site_name):
    W, H = 1000, 1500
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 110], fill=ORANGE)
    d.text((W / 2, 55), site_name.upper(), font=_font("DejaVuSans-Bold.ttf", 38), fill="white", anchor="mm")
    d.rounded_rectangle([60, 170, W - 60, 330], 28, fill=accent)
    f, lines = _fit(d, g["label"].upper(), "DejaVuSans-Bold.ttf", 46, W - 180, 2)
    d.multiline_text((W / 2, 250), "\n".join(lines), font=f, fill="white", anchor="mm", align="center", spacing=6)
    f, lines = _fit(d, g["headline"], "DejaVuSerif-Bold.ttf", 92, W - 140, 3)
    d.multiline_text((W / 2, 590), "\n".join(lines), font=f, fill=INK, anchor="mm", align="center", spacing=18)
    y = 870
    for pt in g["points"][:3]:
        f, lines = _fit(d, pt, "DejaVuSans.ttf", 44, W - 260, 1)
        _check(d, 128, y + 24, 20)
        d.text((175, y + 24), lines[0], font=f, fill=INK, anchor="lm")
        y += 105
    d.rounded_rectangle([200, 1220, W - 200, 1330], 55, fill=ORANGE)
    d.text((W / 2, 1275), "See the full pick →", font=_font("DejaVuSans-Bold.ttf", 46), fill="white", anchor="mm")
    d.text((W / 2, 1420), "#ad · As an Amazon Associate I earn from qualifying purchases",
           font=_font("DejaVuSans.ttf", 24), fill=MUTED, anchor="mm")
    return im


def square_graphic(g, accent):
    S = 800
    im = Image.new("RGB", (S, S), CREAM)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, S, 18], fill=accent)
    f, lines = _fit(d, g["label"].upper(), "DejaVuSans-Bold.ttf", 34, S - 120, 2)
    d.multiline_text((S / 2, 105), "\n".join(lines), font=f, fill=accent, anchor="mm", align="center", spacing=4)
    f, lines = _fit(d, g["headline"], "DejaVuSerif-Bold.ttf", 76, S - 110, 3)
    d.multiline_text((S / 2, 330), "\n".join(lines), font=f, fill=INK, anchor="mm", align="center", spacing=14)
    y = 545
    for pt in g["points"][:3]:
        f, lines = _fit(d, pt, "DejaVuSans.ttf", 34, S - 190, 1)
        _check(d, 85, y + 20, 16)
        d.text((122, y + 20), lines[0], font=f, fill=INK, anchor="lm")
        y += 72
    return im


def render_all(data, out_dir, force=False):
    out = Path(out_dir) / "img"
    out.mkdir(parents=True, exist_ok=True)
    made = 0
    for p in data["products"]:
        g, asin = p["graphic"], p["asin"]
        accent = ACCENTS.get(p["category"], ORANGE)
        for path, fn in ((out / f"{asin}.png", lambda: pin_graphic(g, accent, data["site"]["name"])),
                         (out / f"{asin}-sq.png", lambda: square_graphic(g, accent))):
            if force or not path.exists():
                fn().save(path, optimize=True)
                made += 1
    return made


if __name__ == "__main__":
    import json, sys
    data = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
    n = render_all(data, ROOT / "public", force="--force" in sys.argv)
    print(f"Rendered {n} images")
