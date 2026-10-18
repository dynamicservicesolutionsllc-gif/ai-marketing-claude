#!/usr/bin/env python3
"""Fetch official Amazon product photos through the Amazon Associates Creators API.

Writes amazon_images.json ({ASIN: {url, width, height}}) next to this script; build.py then shows
those Amazon-hosted photos on the site instead of the original graphic cards. Never commit that file:
Amazon's terms allow showing API data only while it is fresh, so it is regenerated on every deploy and
by the daily scheduled run in .github/workflows/deploy-hostinger.yml.

Credentials come from the environment (GitHub Actions secrets), never from the repo:
  AMAZON_CREATORS_CLIENT_ID, AMAZON_CREATORS_CLIENT_SECRET
With either one missing the script exits 0 without doing anything, so the site keeps its graphics.
Access requires an Associates account with 10+ qualifying sales in the past 30 days.

Docs: https://affiliate-program.amazon.com/creatorsapi/docs
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_FILE = ROOT / "amazon_images.json"
TOKEN_URL = "https://api.amazon.com/auth/o2/token"  # North America credentials
API_URL = "https://creatorsapi.amazon/catalog/v1/getItems"
MARKETPLACE = "www.amazon.com"
ALLOWED_HOST = "https://m.media-amazon.com/"


def post_json(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    cid, secret = os.environ.get("AMAZON_CREATORS_CLIENT_ID"), os.environ.get("AMAZON_CREATORS_CLIENT_SECRET")
    if not cid or not secret:
        print("Amazon Creators API credentials not set; keeping original graphics.")
        OUT_FILE.unlink(missing_ok=True)
        return 0
    data = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
    tag = data["site"]["associate_tag"]
    asins = [p["asin"] for p in data["products"]]
    token = post_json(TOKEN_URL, {"grant_type": "client_credentials", "client_id": cid,
                                  "client_secret": secret, "scope": "creatorsapi::default"}, {})["access_token"]
    images = {}
    for i in range(0, len(asins), 10):  # getItems takes at most 10 ASINs
        body = {"itemIds": asins[i:i + 10], "itemIdType": "ASIN", "marketplace": MARKETPLACE,
                "partnerTag": tag, "resources": ["images.primary.large"]}
        try:
            res = post_json(API_URL, body, {"Authorization": f"Bearer {token}", "x-marketplace": MARKETPLACE})
        except urllib.error.HTTPError as err:
            print(f"getItems failed ({err.code}): {err.read()[:300]!r}", file=sys.stderr)
            return 1
        for item in (res.get("itemResults") or {}).get("items", []):
            large = ((item.get("images") or {}).get("primary") or {}).get("large") or {}
            if str(large.get("url", "")).startswith(ALLOWED_HOST):
                images[item["asin"]] = {"url": large["url"], "width": large.get("width"), "height": large.get("height")}
        for e in res.get("errors", []):
            print(f"  skipped: {e.get('code')}: {e.get('message')}", file=sys.stderr)
        time.sleep(1.1)  # stay under the default 1 request/second throttle
    OUT_FILE.write_text(json.dumps(images, indent=1) + "\n", encoding="utf-8")
    print(f"Fetched Amazon photos for {len(images)}/{len(asins)} products.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
