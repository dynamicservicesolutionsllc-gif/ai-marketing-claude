#!/usr/bin/env python3
"""Download a free Pixabay photo of the same KIND of item for each product (not the exact branded product).

These are the same photos the TikTok / YouTube Shorts videos use: the product-type table, the search, the tag
filter and the per-ASIN pick below match stock.py's photo_for(name, asin) in the video folder, so a product's
site card, pins and video all show the same picture.

Usage:  python site/stock_photos.py                 # fetch photos for products that don't have one yet
        python site/stock_photos.py --asin B0XXXXXXXX   # re-fetch one product
        python site/stock_photos.py --check         # list products with no photo (no network, no key)

API key (never committed): PIXABAY_API_KEY env var, else --key-file PATH, else site/.pixabay-key
(gitignored; copy the .pixabay-key that sits next to stock.py in the video folder).

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
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "assets" / "products"
CREDITS = OUT_DIR / "photos.json"
UA = {"User-Agent": "KitchenFindsSite/1.0 (kitchenfindsfavorites.com)"}
SKIP_TAGS = ("ai generated", "ai created", "ai-generated", "logo")

# Same table as stock.py: (words to find in the product name, Pixabay photo search, tag(s) a photo must have;
# "a+b" means both). First match wins, so specific types come before general ones.
PRODUCT_TYPES = [
    ("salad spinner", "salad spinner", "spinner"),
    ("thermometer", "meat thermometer", "thermometer"),
    ("scale", "kitchen scale", "scale"),
    ("shears", "kitchen scissors", "scissors"),
    ("pizza", "pizza cutter", "pizza"),
    ("slow cooker", "slow cooker", "cooker"),
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
    ("tumbler", "tumbler cup", "cup"),
    ("water bottle", "water bottle", "bottle"),
    ("bottle", "water bottle", "bottle"),
    ("travel mug", "coffee travel mug", "mug"),
    ("mug", "coffee mug", "mug"),
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
        if words in n:
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
    hits = [h for h in hits if all(w in h.get("tags", "").lower() for w in need)
            and not any(t in h.get("tags", "").lower() for t in SKIP_TAGS)]
    if not hits:
        return None
    h = hits[int(hashlib.md5(seed.encode()).hexdigest(), 16) % min(len(hits), 8)]
    return kind, h


def read_key(key_file):
    if os.environ.get("PIXABAY_API_KEY"):
        return os.environ["PIXABAY_API_KEY"].strip()
    for path in (key_file, ROOT / ".pixabay-key"):
        if path and Path(path).exists():
            return Path(path).read_text(encoding="utf-8").strip()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asin", action="append", default=[], help="re-fetch these ASINs even if they have a photo")
    ap.add_argument("--key-file")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
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
    if not key:
        print("No Pixabay key (set PIXABAY_API_KEY, pass --key-file, or create site/.pixabay-key); "
              "products keep their text-only graphics.", file=sys.stderr)
        return 0
    from PIL import Image
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    got, missing = 0, []
    for p in todo:
        try:
            res = pick(p["name"], p["asin"], key)
        except Exception as err:  # network/API trouble: keep going, the product keeps its graphic
            print(f"{p['asin']}: Pixabay request failed ({err})", file=sys.stderr)
            res = None
        if not res:
            missing.append(p)
            continue
        kind, h = res
        with _get(h.get("largeImageURL") or h["webformatURL"]) as r:
            im = Image.open(io.BytesIO(r.read())).convert("RGB")
        if im.width > 1200:
            im = im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
        im.save(OUT_DIR / f"{p['asin']}.jpg", "JPEG", quality=85, optimize=True, progressive=True)
        credits[p["asin"]] = {"id": h["id"], "page_url": h.get("pageURL", ""), "user": h.get("user", ""), "kind": kind}
        got += 1
    CREDITS.write_text(json.dumps(dict(sorted(credits.items())), indent=2) + "\n", encoding="utf-8")
    print(f"Downloaded {got} photo(s).")
    for p in missing:
        print(f"no photo found: {p['asin']} {p['name']}" + ("" if product_type(p["name"]) else " (no product type)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
