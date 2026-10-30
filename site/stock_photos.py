#!/usr/bin/env python3
"""Download a free Pixabay photo of the same KIND of item for each product (not the exact branded product).

These are the same photos the TikTok / YouTube Shorts videos use: the product-type table, the search, the tag
filter and the per-ASIN pick below match stock.py's photo_for(name, asin) in the video folder, so a product's
site card, pins and video all show the same picture.

Usage:  python site/stock_photos.py                 # fetch photos for products that don't have one yet
        python site/stock_photos.py --asin B0XXXXXXXX   # re-fetch one product
        python site/stock_photos.py --check         # list products with no photo (no network, no key)

API key (never committed): PIXABAY_API_KEY env var, else --key-file PATH, else site/.pixabay-key (gitignored),
else the video folder's own key at ~/Documents/claud create/videos/.pixabay-key. build.py calls fetch_missing()
on every build, so on Frank's PC new products get their photo automatically; elsewhere (no key) it does nothing.

Writes assets/products/<ASIN>.jpg (max 1200 px wide) and assets/products/photos.json
({ASIN: {id, page_url, user, kind}}). Commit both: Pixabay asks API users to download images rather
than hotlink them, and committing keeps every deploy identical. build.py then uses the photo in the
site card and pin graphics, always labelled "Similar item shown" so nobody mistakes it for the product.
Pixabay Content License: free for commercial use, no attribution required (we credit anyway).
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "assets" / "products"
CREDITS = OUT_DIR / "photos.json"
# Photo ids reviewed and rejected per ASIN (wrong item, cutout noise, ...); pickers skip them next time.
REJECTED = json.loads((OUT_DIR / "rejected.json").read_text(encoding="utf-8")) if (OUT_DIR / "rejected.json").exists() else {}
UA = {"User-Agent": "KitchenFindsSite/1.0 (kitchenfindsfavorites.com)"}
SKIP_TAGS = ("ai generated", "ai created", "ai-generated", "logo")

# Same table as stock.py: (words to find in the product name, Pixabay photo search, tag(s) a photo must have;
# "a+b" means both). First match wins, so specific types come before general ones.
PRODUCT_TYPES = [
    # Drinkware first, so "MagSlider Lid" or "Slider" tumblers aren't read as lid organizers.
    ("tumbler", "tumbler cup", "cup"),
    ("water bottle", "water bottle", "bottle"),
    ("bottle", "water bottle", "bottle"),
    ("travel mug", "coffee travel mug", "mug"),
    ("mug", "coffee mug", "mug"),
    ("salad spinner", "salad spinner", "spinner"),
    ("thermometer", "meat thermometer", "thermometer"),
    ("scale", "kitchen scale", "scale"),
    ("shears", "kitchen scissors", "scissors"),
    ("pizza", "pizza cutter", "pizza"),
    ("slow cooker", "slow cooker", "slow+cooker"),
    ("immersion", "immersion blender", "blender"),
    ("blender", "blender smoothie", "blender"),
    ("hand mixer", "hand mixer", "mixer"),
    ("food processor", "food processor", "processor"),
    ("kettle", "electric kettle", "kettle"),
    ("french press", "french press coffee", "coffee"),
    ("frother", "milk frother", "frother"),
    ("air fryer", "air fryer", "fryer"),
    ("waffle", "waffle maker", "waffle"),
    ("egg cooker", "boiled eggs", "eggs"),
    ("drying rack", "dish drying rack", "dish+rack"),
    ("drying mat", "dishes drying", "dishes"),
    ("spice", "spice rack", "spice"),
    ("lazy susan", "spice jars", "jars"),
    ("can organizer", "canned food", "cans"),
    ("can opener", "can opener", "opener"),
    ("measuring cup", "measuring cup", "measuring"),
    ("oven mitt", "oven mitts", "oven"),
    ("baking mat", "cookies baking sheet", "cookies"),
    ("pastry mat", "rolling dough", "dough"),
    ("baking sheet", "cookies baking sheet", "cookies"),
    ("splatter", "microwave", "microwave"),
    ("fat separator", "gravy", "gravy"),
    ("apple peeler", "apples", "apple"),
    ("chopper", "chopped vegetables", "vegetables"),
    ("shredder", "shredded chicken", "chicken"),
    ("knife organizer", "knife block", "knife"),
    ("knife", "kitchen knives", "knife"),
    ("silverware", "cutlery drawer", "cutlery"),
    ("drawer", "kitchen drawer", "drawer"),
    ("shelf liner", "kitchen drawer", "drawer"),
    ("sponge", "kitchen sponge", "sponge"),
    ("under sink", "under sink cabinet", "sink"),
    ("sink", "kitchen sink", "sink"),
    ("lid", "pot lids", "lid"),
    ("cutting board", "cutting board", "board"),
    ("cookware", "pots and pans", "pots"),
    ("food storage", "food storage containers", "container"),
    ("container", "food storage containers", "container"),
    ("bins", "pantry storage", "pantry"),
]


# How captions name each type ("Photo shows a similar ..."). Types not listed here read as "<words>".
NOUNS = {
    "scale": "kitchen scale", "shears": "pair of kitchen shears", "pizza": "pizza cutter", "immersion": "immersion blender",
    "frother": "milk frother", "waffle": "waffle maker", "drying rack": "dish drying rack", "drying mat": "dish drying mat",
    "spice": "spice rack", "lazy susan": "lazy susan", "can organizer": "can organizer", "splatter": "splatter guard",
    "chopper": "vegetable chopper", "shredder": "meat shredder", "silverware": "silverware organizer",
    "drawer": "drawer organizer", "sink": "sink organizer", "under sink": "under-sink organizer", "lid": "lid organizer",
    "cookware": "cookware organizer", "food storage": "food storage container", "container": "storage container",
    "bins": "pantry bin", "oven mitt": "oven mitt", "knife": "kitchen knife",
}


def product_type(name):
    """(kind, search, required tag) for a product name, or None. `kind` is the caption noun."""
    n = name.lower()
    for words, query, tag in PRODUCT_TYPES:
        if re.search(r"\b" + re.escape(words) + r"(?:s|es)?\b", n):  # whole words: "lid" must not match "Slider"
            return NOUNS.get(words, words), query, tag
    return None


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60)


def pick(name, seed, key):
    """The Pixabay hit stock.py's photo_for(name, seed) would choose, or None."""
    pt = product_type(name)
    if not pt:
        return None
    kind, query, tag = pt
    q = urllib.parse.urlencode({"key": key, "q": query, "image_type": "photo", "per_page": 40,
                                "safesearch": "true", "min_width": 1000})
    hits = json.load(_get("https://pixabay.com/api/?" + q)).get("hits", [])
    need = tag.split("+")
    rejected = set(REJECTED.get(seed, []))  # photos already reviewed and turned down for this product
    hits = [h for h in hits if all(w in h.get("tags", "").lower() for w in need) and h["id"] not in rejected
            and not any(t in h.get("tags", "").lower() for t in SKIP_TAGS)]
    if not hits:
        return None
    h = hits[int(hashlib.md5(seed.encode()).hexdigest(), 16) % min(len(hits), 8)]
    return kind, [{"url": h.get("largeImageURL") or h["webformatURL"], "id": h["id"], "page_url": h.get("pageURL", ""),
                   "user": h.get("user", ""), "site": "Pixabay"}]


# Fallback where no Pixabay key is available (e.g. the "Fetch product photos" GitHub workflow): Wikimedia
# Commons, searchable without a key. Only public-domain / CC0 photos are used, so commercial use needs no
# permission or attribution (the product page credits them anyway).
FREE_BAD = ("illustration", "vector", "drawing", "clipart", "clip art", "cartoon", "logo", "icon", "painting",
            "sketch", "diagram", "poster", "patent", "advert", "engraving", "map of", "nude", "ai generated", "ai-generated",
            "museum", "antique", "dynasty", "lithograph", "historical", "century", "archive", "vintage", "fishing",
            "black and white", "black-and-white", "monochrome", "ethnographic", "exhibit")
FREE_LICENSES = ("public domain", "cc0", "pd")
_free_cache = {}


def _commons_search(query):
    import time
    time.sleep(1.0)  # be polite to the Wikimedia API
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": 50,
        "gsrsearch": f"{query} filetype:bitmap", "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 1200})
    pages = (json.load(_get("https://commons.wikimedia.org/w/api.php?" + q)).get("query") or {}).get("pages") or {}
    out = []
    for pg in sorted(pages.values(), key=lambda x: x.get("index", 0)):
        ii = (pg.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata") or {}
        val = lambda k: re.sub(r"<[^>]+>", " ", str((md.get(k) or {}).get("value", "")))
        out.append({"title": pg.get("title", ""), "text": " ".join([pg.get("title", ""), val("ImageDescription"),
                    val("ObjectName"), val("Categories")]).lower(), "license": val("LicenseShortName").strip(),
                    "mime": ii.get("mime", ""), "width": ii.get("width") or 0, "url": ii.get("thumburl") or ii.get("url"),
                    "page_url": ii.get("descriptionurl", ""), "user": re.sub(r"\s+", " ", val("Artist")).strip()[:80]})
    return out


def pick_free(name, seed):
    pt = product_type(name)
    if not pt:
        return None
    kind, query, tag = pt
    found = {}
    for q in dict.fromkeys([query, kind if kind.split()[-1] in query else f"{kind} kitchen"]):  # two searches per type
        if q not in _free_cache:
            _free_cache[q] = _commons_search(q)
        for r in _free_cache[q]:
            found.setdefault(r["title"], r)
    need = tag.split("+")
    # Photos taken in a kitchen first; then the rest in search order.
    pool = sorted(found.values(), key=lambda r: "kitchen" not in r["text"])
    hits = [r for r in pool if all(w in r["text"] for w in need) and r["title"] not in REJECTED.get(seed, [])
            and not any(b in r["text"] for b in FREE_BAD) and r["mime"] == "image/jpeg" and r["width"] >= 800
            and any(r["license"].lower().startswith(l) for l in FREE_LICENSES)]
    if not hits:
        return None
    start = int(hashlib.md5(seed.encode()).hexdigest(), 16) % min(len(hits), 8)
    ordered = hits[start:] + hits[:start]  # this product's pick first, the rest as download fallbacks
    return kind, [{"url": r["url"], "id": r["title"], "page_url": r["page_url"], "user": r["user"],
                   "site": "Wikimedia Commons", "license": r["license"]} for r in ordered[:5]]


# Where the video scripts keep the key on Frank's PC (stock.py reads .pixabay-key next to itself).
VIDEO_KEY = Path.home() / "Documents" / "claud create" / "videos" / ".pixabay-key"


def read_key(key_file=None):
    if os.environ.get("PIXABAY_API_KEY"):
        return os.environ["PIXABAY_API_KEY"].strip()
    for path in (key_file, ROOT / ".pixabay-key", VIDEO_KEY):
        if path and Path(path).exists():
            return Path(path).read_text(encoding="utf-8").strip()
    return None


def fetch_missing(quiet=False):
    """Called by build.py: fetch photos for products without one, if a key is on this machine.
    Never raises, so a missing key or a Pixabay outage never blocks a build."""
    data = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
    if all((OUT_DIR / f"{p['asin']}.jpg").exists() for p in data["products"]) or not read_key():
        return
    try:
        main([])
    except Exception as err:
        print(f"stock_photos: skipped ({err})", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--asin", action="append", default=[], help="re-fetch these ASINs even if they have a photo")
    ap.add_argument("--key-file")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--free", "--openverse", dest="free", action="store_true",
                    help="with no Pixabay key, use public-domain photos from Wikimedia Commons")
    a = ap.parse_args(argv)
    data = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
    credits = json.loads(CREDITS.read_text(encoding="utf-8")) if CREDITS.exists() else {}
    todo = [p for p in data["products"]
            if p["asin"] in a.asin or not (OUT_DIR / f"{p['asin']}.jpg").exists() or p["asin"] not in credits]
    if a.check:
        for p in todo:
            print(f"no photo: {p['asin']} {p['name']}" + ("" if product_type(p["name"]) else "  (no product type: add one to PRODUCT_TYPES)"))
        print(f"{len(data['products']) - len(todo)}/{len(data['products'])} products have a photo")
        return 0
    if not todo:
        print("Every product already has a photo.")
        return 0
    key = read_key(a.key_file)
    if not key and not a.free:
        print("No Pixabay key (set PIXABAY_API_KEY, pass --key-file, or create site/.pixabay-key); "
              "products keep their text-only graphics.", file=sys.stderr)
        return 0
    from PIL import Image
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    got, missing, fails = 0, [], 0
    import time
    for p in todo:
        time.sleep(0.7)  # Pixabay allows 100 requests/minute
        try:
            res = pick(p["name"], p["asin"], key) if key else pick_free(p["name"], p["asin"])
            fails = 0
        except Exception as err:  # network/API trouble: the product keeps its graphic
            print(f"{p['asin']}: photo search failed ({err})", file=sys.stderr)
            res, fails = None, fails + 1
            if fails >= 3:  # bad key or Pixabay down: stop instead of retrying every product
                print("Photo search unavailable; stopping. Products without a photo keep their graphics.", file=sys.stderr)
                break
        if not res:
            missing.append(p)
            continue
        kind, cands = res
        im = c = None
        for c in cands:  # first candidate that downloads and opens as an image
            try:
                with _get(c["url"]) as r:
                    im = Image.open(io.BytesIO(r.read()))
                if im.mode in ("RGBA", "LA", "P"):  # cutouts: put them on white, or the transparent area turns to noise
                    im = im.convert("RGBA")
                    bg = Image.new("RGB", im.size, "white")
                    bg.paste(im, mask=im.getchannel("A"))
                    im = bg
                im = im.convert("RGB")
                break
            except Exception as err:
                print(f"{p['asin']}: download failed ({err}), trying the next photo", file=sys.stderr)
        if im is None:
            missing.append(p)
            continue
        if im.width > 1200:
            im = im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
        im.save(OUT_DIR / f"{p['asin']}.jpg", "JPEG", quality=85, optimize=True, progressive=True)
        credits[p["asin"]] = {k: v for k, v in c.items() if k != "url"} | {"kind": kind}
        got += 1
    CREDITS.write_text(json.dumps(dict(sorted(credits.items())), indent=2) + "\n", encoding="utf-8")
    print(f"Downloaded {got} photo(s).")
    for p in missing:
        print(f"no photo found: {p['asin']} {p['name']}" + ("" if product_type(p["name"]) else " (no product type)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
