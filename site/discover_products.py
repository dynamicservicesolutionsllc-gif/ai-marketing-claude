#!/usr/bin/env python3
"""
Discover and stage new Amazon products for Kitchen Finds & Favorites.
Runs daily via cron to find 5 new products matching your category/keyword strategy.

Searches Amazon via Creators API, researches competitors, identifies top sellers,
then adds candidates to products.json staging section for your review.

Requires: AMAZON_CREATORS_CLIENT_ID, AMAZON_CREATORS_CLIENT_SECRET (from .env)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRODUCTS_FILE = ROOT / "products.json"
LOG_FILE = ROOT / "logs" / "discovery.log"
TOKEN_URL = "https://api.amazon.com/auth/o2/token"
API_URL = "https://creatorsapi.amazon/catalog/v1/searchItems"
MARKETPLACE = "www.amazon.com"

# Keywords and categories to search for new products
SEARCH_QUERIES = [
    {"keyword": "kitchen drawer organizer", "category": "organization"},
    {"keyword": "small kitchen gadgets", "category": "gadgets"},
    {"keyword": "kitchen storage containers", "category": "organization"},
    {"keyword": "compact kitchen appliances", "category": "appliances"},
    {"keyword": "water bottle insulated", "category": "drinkware"},
]

# Top sellers to compare against (for ranking)
TOP_SELLER_BOOST = 2.0
PRODUCTS_TO_STAGE = 5


def log_msg(msg):
    """Log to file and stdout."""
    timestamp = datetime.now().isoformat()
    line = f"[{timestamp}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def post_json(url, body, headers):
    """POST JSON and return parsed response."""
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", **headers}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        log_msg(f"HTTP Error {e.code}: {e.read()[:500]}")
        return None


def get_access_token(cid, secret):
    """Get Amazon Creators API access token."""
    body = {
        "grant_type": "client_credentials",
        "client_id": cid,
        "client_secret": secret,
        "scope": "creatorsapi::default"
    }
    resp = post_json(TOKEN_URL, body, {})
    if not resp:
        return None
    return resp.get("access_token")


def search_products(token, tag, keyword, limit=10):
    """Search Amazon for products matching keyword."""
    body = {
        "keywords": [keyword],
        "marketplace": MARKETPLACE,
        "partnerTag": tag,
        "resources": ["itemInfo.title", "itemInfo.features", "images.primary", "offers.summaries"],
        "maxResults": limit
    }

    resp = post_json(
        API_URL,
        body,
        {"Authorization": f"Bearer {token}", "x-marketplace": MARKETPLACE}
    )

    if not resp:
        return []

    products = []
    for item in resp.get("searchResult", {}).get("items", []):
        asin = item.get("asin")
        title = item.get("itemInfo", {}).get("title", {}).get("displayValue", "")

        if asin and title:
            products.append({
                "asin": asin,
                "title": title,
                "source": keyword,
                "rank": len(products)
            })
        time.sleep(0.2)  # Rate limit

    return products


def load_existing_asins():
    """Get all ASINs already in products.json (including staging)."""
    try:
        data = json.loads(PRODUCTS_FILE.read_text())
        asins = set(p["asin"] for p in data.get("products", []))
        staging = data.get("staging", {}).get("products", [])
        asins.update(s["asin"] for s in staging)
        return asins
    except:
        return set()


def score_product(product, rank, is_top_seller=False):
    """Score product for ranking. Higher = better candidate."""
    score = 100 - rank  # Earlier results score higher
    if is_top_seller:
        score *= TOP_SELLER_BOOST
    return score


def main():
    # Support both naming conventions for flexibility
    cid = os.environ.get("AMAZON_CLIENT_ID") or os.environ.get("AMAZON_CREATORS_CLIENT_ID")
    secret = os.environ.get("AMAZON_CLIENT_SECRET") or os.environ.get("AMAZON_CREATORS_CLIENT_SECRET")

    if not cid or not secret:
        log_msg("ERROR: Amazon API credentials not set (requires AMAZON_CLIENT_ID and AMAZON_CLIENT_SECRET or AMAZON_CREATORS_CLIENT_ID/SECRET)")
        return 1

    # Load existing products
    try:
        data = json.loads(PRODUCTS_FILE.read_text())
    except Exception as e:
        log_msg(f"ERROR: Failed to load products.json: {e}")
        return 1

    existing_asins = load_existing_asins()
    associate_tag = data.get("site", {}).get("associate_tag")

    if not associate_tag:
        log_msg("ERROR: No associate_tag in products.json")
        return 1

    # Get access token
    token = get_access_token(cid, secret)
    if not token:
        log_msg("ERROR: Failed to get Amazon API token")
        return 1

    # Search for new products
    candidates = []
    log_msg(f"Searching for new products...")

    for query in SEARCH_QUERIES:
        keyword = query["keyword"]
        category = query["category"]

        results = search_products(token, associate_tag, keyword, limit=20)
        log_msg(f"  {keyword}: {len(results)} results")

        for product in results:
            if product["asin"] not in existing_asins:
                product["category"] = category
                product["score"] = score_product(product, product["rank"])
                candidates.append(product)

        time.sleep(1.1)  # Rate limit

    # Remove duplicates (keep highest scoring)
    seen_asins = {}
    for c in sorted(candidates, key=lambda x: x["score"], reverse=True):
        if c["asin"] not in seen_asins:
            seen_asins[c["asin"]] = c

    candidates = list(seen_asins.values())
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Stage top N products
    if not candidates:
        log_msg("No new products found")
        return 0

    to_stage = candidates[:PRODUCTS_TO_STAGE]
    log_msg(f"Staging {len(to_stage)} new products for review:")

    staged_products = []
    for prod in to_stage:
        staged_product = {
            "asin": prod["asin"],
            "name": prod["title"],
            "category": prod["category"],
            "blurb": f"[Auto-discovered via Amazon search: {prod['source']}]",
            "added": datetime.now().strftime("%Y-%m-%d"),
            "status": "pending_review",
            "source_keyword": prod["source"],
            "score": prod["score"],
            "graphic": {"label": "", "headline": "", "points": []},
            "subcategory": "",
            "award": "",
            "pin": {"title": "", "description": "", "board": ""},
            "suits": "[Needs review]",
            "check": "[Needs review]"
        }
        staged_products.append(staged_product)
        log_msg(f"  ✓ {prod['asin']}: {prod['title']}")

    # Update products.json
    if "staging" not in data:
        data["staging"] = {"products": []}

    data["staging"]["products"].extend(staged_products)

    # Save updated products.json
    try:
        PRODUCTS_FILE.write_text(json.dumps(data, indent=2) + "\n")
        log_msg(f"Updated products.json with {len(staged_products)} staged products")
        return 0
    except Exception as e:
        log_msg(f"ERROR: Failed to save products.json: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
