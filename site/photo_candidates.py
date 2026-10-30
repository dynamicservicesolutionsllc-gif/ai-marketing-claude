#!/usr/bin/env python3
"""Hand-picked similar-item photos for products the automatic picker (stock_photos.py) can't match well.

Two steps, both run by the "Fetch product photos" workflow (they need the Pixabay key):

  python site/photo_candidates.py candidates
      For every product without a photo, runs several hand-written Pixabay searches and saves up to 12
      small candidate images to photo-candidates/<ASIN>/<pixabay id>.jpg with photo-candidates/index.json.
      The workflow pushes these to the `photo-candidates` branch for review; they never reach the site.

  python site/photo_candidates.py choose
      Reads assets/products/chosen.json ({ASIN: {"id": <pixabay id>, "kind": "<caption noun>"}}), downloads each
      chosen photo at full size into assets/products/<ASIN>.jpg and credits it in photos.json, like stock_photos.py.
"""
import io
import json
import sys
import time
import urllib.parse
from pathlib import Path

import stock_photos as sp

ROOT = Path(__file__).resolve().parent
CAND = ROOT / "photo-candidates"
CHOSEN = sp.OUT_DIR / "chosen.json"
PER_PRODUCT = 12

# Hand-written searches for products the automatic picker missed. Products not listed fall back to their
# product type's searches in stock_photos.py.
SEARCHES = {
    "B0C3QZ7SNF": ["sponge holder", "kitchen sink sponge", "sink caddy", "dish brush sponge"],
    "B09BKTSJFJ": ["apple peeler", "peeling apple", "apple corer", "apple slices"],
    "B07FNRXFTD": ["pot lids", "food container lids", "kitchen cabinet organized", "plastic containers stacked"],
    "B08NY9RYDG": ["pot lids", "pots and pans cabinet", "cookware lids", "kitchen cabinet organized"],
    "B004P2LEE0": ["slow cooker", "crockpot", "crock pot", "slow cooker stew"],
    "B003OAJGJO": ["slow cooker", "crockpot", "crock pot", "slow cooker chili"],
    "B0CFQFMC4F": ["under sink cabinet", "cleaning supplies cabinet", "sink cabinet", "kitchen cabinet storage"],
    "B0CSPKSCP2": ["under sink cabinet", "cleaning supplies cabinet", "sink cabinet", "kitchen cabinet storage"],
    "B08N9Q24M9": ["vegetable chopper", "mandoline slicer", "dicing onion", "vegetable slicer"],
    "B0764HS4SL": ["vegetable chopper", "spiralizer", "zucchini noodles", "dicing vegetables"],
    "B0CGRGRXPY": ["shredded chicken", "pulled chicken", "pulled pork", "shredding meat"],
    "B08PP48979": ["electric kettle", "glass kettle", "kettle boiling", "tea kettle"],
    "B07W7MG36T": ["kitchen drawer", "drawer liner", "shelf liner", "kitchen shelf"],
    "B0000645YM": ["food processor", "mini chopper", "chopping onion machine", "kitchen appliance blender"],
    "B0CJZW65R3": ["tumbler", "insulated tumbler", "stainless steel cup straw", "large tumbler"],
    "B073WJMKHN": ["tumbler", "insulated tumbler", "stainless steel cup", "thermos cup"],
    "B0DF472VMZ": ["coffee tumbler", "travel coffee cup", "reusable coffee cup", "insulated cup"],
    "B0BZYCJK89": ["water bottle", "reusable water bottle", "insulated bottle", "sports bottle"],
    "B0CQVWT2NH": ["water bottle", "reusable water bottle", "large water bottle", "gym water bottle"],
    "B0C1GNRZ6T": ["baking sheet", "baking tray", "cutting board", "kitchen cabinet organized"],
    "B0026RHI3M": ["baking sheet", "baking tray", "sheet pan", "cookies oven tray"],
    "B0725GYNG6": ["silicone baking mat", "baking mat", "cookies baking tray", "baking tray"],
    "B07V1ZSYVF": ["gravy", "gravy boat", "pouring gravy", "measuring jug"],
    "B079M8FPTW": ["food storage containers", "meal prep containers", "leftovers container", "plastic containers"],
    "B09NV9WV35": ["knife block", "kitchen knives", "knife set", "knives drawer"],
    "B07GTC4NCV": ["microwave", "microwave food", "microwave cover", "microwave oven"],
}


_cache = {}


def search(key, q):
    if q not in _cache:
        time.sleep(0.7)  # Pixabay allows 100 requests/minute
        qs = urllib.parse.urlencode({"key": key, "q": q, "image_type": "photo", "per_page": 30, "safesearch": "true",
                                     "min_width": 1000})
        _cache[q] = json.load(sp._get("https://pixabay.com/api/?" + qs)).get("hits", [])
    return _cache[q]


def candidates(key):
    from PIL import Image
    data = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
    todo = [p for p in data["products"] if not (sp.OUT_DIR / f"{p['asin']}.jpg").exists()]
    index = {}
    for p in todo:
        asin = p["asin"]
        pt = sp.product_type(p["name"])
        queries = SEARCHES.get(asin) or ([pt[1]] if pt else [p["name"]])
        rejected = set(sp.REJECTED.get(asin, []))
        lists = [[h for h in search(key, q) if h["id"] not in rejected
                  and not any(t in h.get("tags", "").lower() for t in sp.SKIP_TAGS)] for q in queries]
        picks, seen = [], set()
        for rank in range(30):  # round-robin across the searches so each one is represented
            for q, hits in zip(queries, lists):
                if rank < len(hits) and hits[rank]["id"] not in seen and len(picks) < PER_PRODUCT:
                    h = hits[rank]
                    seen.add(h["id"])
                    picks.append({"id": h["id"], "tags": h.get("tags", ""), "query": q, "url": h["webformatURL"]})
        d = CAND / asin
        d.mkdir(parents=True, exist_ok=True)
        for c in picks:
            try:
                with sp._get(c["url"]) as r:
                    im = Image.open(io.BytesIO(r.read()))
                if im.mode in ("RGBA", "LA", "P"):
                    im = im.convert("RGBA")
                    bg = Image.new("RGB", im.size, "white")
                    bg.paste(im, mask=im.getchannel("A"))
                    im = bg
                im = im.convert("RGB")
                im.thumbnail((400, 400))
                im.save(d / f"{c['id']}.jpg", "JPEG", quality=80)
            except Exception as err:
                print(f"{asin}: candidate {c['id']} failed ({err})", file=sys.stderr)
        index[asin] = {"name": p["name"], "candidates": [{k: v for k, v in c.items() if k != "url"} for c in picks]}
        print(f"{asin}: {len(picks)} candidates")
    CAND.mkdir(exist_ok=True)
    (CAND / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


def choose(key):
    from PIL import Image
    chosen = json.loads(CHOSEN.read_text(encoding="utf-8"))
    credits = json.loads(sp.CREDITS.read_text(encoding="utf-8")) if sp.CREDITS.exists() else {}
    for asin, c in chosen.items():
        if (sp.OUT_DIR / f"{asin}.jpg").exists() and credits.get(asin, {}).get("id") == c["id"] \
                and credits[asin].get("note") == c.get("note"):
            continue
        time.sleep(0.7)
        hits = json.load(sp._get("https://pixabay.com/api/?" + urllib.parse.urlencode({"key": key, "id": c["id"]}))).get("hits", [])
        if not hits:
            print(f"{asin}: Pixabay photo {c['id']} not found", file=sys.stderr)
            continue
        h = hits[0]
        with sp._get(h.get("largeImageURL") or h["webformatURL"]) as r:
            im = Image.open(io.BytesIO(r.read()))
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im, mask=im.getchannel("A"))
            im = bg
        im = im.convert("RGB")
        if im.width > 1200:
            im = im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
        im.save(sp.OUT_DIR / f"{asin}.jpg", "JPEG", quality=85, optimize=True, progressive=True)
        credits[asin] = {"id": h["id"], "page_url": h.get("pageURL", ""), "user": h.get("user", ""), "site": "Pixabay",
                         "kind": c.get("kind", "")}
        if c.get("note"):  # no similar-item photo exists: the caption says what the photo shows instead
            credits[asin]["note"] = c["note"]
        print(f"{asin}: saved Pixabay photo {h['id']} ({c['kind']})")
    sp.CREDITS.write_text(json.dumps(dict(sorted(credits.items())), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    k = sp.read_key()
    if not k:
        sys.exit("No Pixabay key (PIXABAY_API_KEY).")
    {"candidates": candidates, "choose": choose}[sys.argv[1]](k)
