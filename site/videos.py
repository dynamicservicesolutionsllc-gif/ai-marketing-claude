#!/usr/bin/env python3
"""Make 9:16 short videos (TikTok / Reels / Shorts) from each buying guide's "measure first" list.

`python3 site/videos.py` writes public/videos/<guide>.mp4 (1080x1920, about 20 s, silent: add a
sound in the app) and public/videos.json, the posting queue the free short-video routine reads
(site/routines/short-videos.md). Existing MP4s are kept (pass --force to re-render). Uses only the
site's own text and the licensed hero photos in assets/guides/ (never Amazon images).
"""
import json
import sys
import subprocess
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "public" / "videos"
QUEUE = ROOT / "public" / "videos.json"
W, H = 1080, 1920
ORANGE, INK, CREAM = (200, 100, 59), (43, 38, 34), (251, 248, 243)
F = lambda name, size: ImageFont.truetype(str(ROOT / "fonts" / f"{name}.ttf"), size)
SECS = {"hook": 3.0, "tip": 3.2, "cta": 3.5}
FADE = 0.4


def background(photo):
    img = Image.open(photo).convert("RGB")
    scale = H / img.height
    bg = img.resize((int(img.width * scale), H)).crop(((int(img.width * scale) - W) // 2, 0, (int(img.width * scale) + W) // 2, H))
    bg = bg.filter(ImageFilter.GaussianBlur(28))
    bg = Image.blend(bg, Image.new("RGB", (W, H), INK), 0.55)
    band = img.resize((W, int(img.height * W / img.width)))
    bg.paste(band, (0, 210))
    return bg, 210 + band.height


def wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur]


def card(bg, top, kicker, head, body=None, number=None):
    im = bg.copy()
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 14), fill=ORANGE)
    d.text((W // 2, 120), "KITCHEN FINDS & FAVORITES", font=F("DejaVuSans-Bold", 34), fill=CREAM, anchor="mm")
    y = top + 70
    box_top = y
    hf, bf = F("DejaVuSerif-Bold", 74), F("DejaVuSans", 44)
    hl = wrap(d, head, hf, W - 200)
    bl = wrap(d, body, bf, W - 200) if body else []
    box_h = 150 + len(hl) * 92 + (len(bl) * 60 + 40 if bl else 0) + (110 if number else 0)
    d.rounded_rectangle((60, box_top, W - 60, box_top + box_h), 36, fill=CREAM)
    y = box_top + 60
    if number:
        d.ellipse((W // 2 - 50, y, W // 2 + 50, y + 100), fill=ORANGE)
        d.text((W // 2, y + 50), str(number), font=F("DejaVuSans-Bold", 56), fill=CREAM, anchor="mm")
        y += 130
    d.text((W // 2, y), kicker.upper(), font=F("DejaVuSans-Bold", 34), fill=ORANGE, anchor="mt")
    y += 70
    for line in hl:
        d.text((W // 2, y), line, font=hf, fill=INK, anchor="mt")
        y += 92
    y += 20
    for line in bl:
        d.text((W // 2, y), line, font=bf, fill=(111, 102, 93), anchor="mt")
        y += 60
    return im


def caption(key, sub, data):
    """Per-platform captions. Videos link to our guide page (never to Amazon)."""
    site = data["site"]["url"]
    noun = sub.get("noun", sub["title"]).lower()
    noun = ("an " if noun[0] in "aeiou" else "a ") + noun
    tips = sub["measure"][:4]
    tags = list(dict.fromkeys(sub.get("hashtags", "").split() + ["#kitchenorganization", "#smallkitchen", "#kitchenhacks"]))[:5]
    page = f"{site}/guides/{key}/"
    hook = f"Measure these {len(tips)} things before you buy {noun}."
    disclosure = "Our site earns from qualifying Amazon purchases."
    return {
        "title": f"Measure these {len(tips)} things before buying {noun}"[:100],
        "page_url": page,
        "tiktok": f"{hook} Free small-kitchen measuring checklist + our full guide: link in bio. {disclosure} {' '.join(tags)}",
        "instagram": f"{hook} Save this for later. Free measuring checklist + our full buying guide: link in bio. {disclosure} {' '.join(tags)}",
        "youtube_title": f"{hook[:-1]} #shorts"[:100],
        "youtube_description": f"{hook} Full guide and free printable checklist: {page}?utm_source=youtube&utm_medium=social&utm_campaign={key}\n\n{disclosure}\n{' '.join(tags)}",
    }


def make(key, sub, tmp, force=False):
    out = OUT / f"{key}.mp4"
    if out.exists() and not force:
        return out
    bg, top = background(ROOT / "assets" / "guides" / f"{key}.jpg")
    noun = sub.get("noun", sub["title"]).lower()
    noun = ("an " if noun[0] in "aeiou" else "a ") + noun
    tips = sub["measure"][:4]
    slides = [("hook", card(bg, top, "Before you buy", f"Measure these {len(tips)} things first", f"Buying {noun}? Save yourself a return."))]
    for i, (h, b) in enumerate(tips, 1):
        slides.append(("tip", card(bg, top, "Measure", h, b, number=i)))
    slides.append(("cta", card(bg, top, "Free printable", "Get the full measuring checklist", "Link in bio: kitchenfindsfavorites.com")))
    inputs, filters = [], []
    for n, (kind, im) in enumerate(slides):
        p = Path(tmp) / f"{key}-{n}.png"
        im.save(p)
        inputs += ["-loop", "1", "-t", str(SECS[kind]), "-i", str(p)]
    # Chain crossfades between slides.
    prev, offset = "[0:v]", 0.0
    for n in range(1, len(slides)):
        offset += SECS[slides[n - 1][0]] - FADE
        label = f"[v{n}]"
        filters.append(f"{prev}[{n}:v]xfade=transition=fade:duration={FADE}:offset={offset:.2f}{label}")
        prev = label
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
                    "-map", prev, "-r", "30", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "20", str(out)], check=True)
    return out


def main():
    force = "--force" in sys.argv
    data = json.loads((ROOT / "products.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    queue = []
    with tempfile.TemporaryDirectory() as tmp:
        for key, sub in data["subcategories"].items():
            if not sub.get("measure"):
                continue
            path = make(key, sub, tmp, force)
            queue.append({"id": f"video-{key}", "order": len(queue) + 1, "guide": key,
                          "video": f"{data['site']['url']}/videos/{path.name}", **caption(key, sub, data)})
            print("ok", path.name, round(path.stat().st_size / 1e6, 1), "MB")
    QUEUE.write_text(json.dumps({"videos": queue}, indent=1) + "\n")
    print(len(queue), "videos in", QUEUE.name)


if __name__ == "__main__":
    main()
