#!/usr/bin/env python3
"""Build the Kitchen Finds & Favorites site from products.json.

Usage: python3 build.py          # validate products.json and write public/
       python3 build.py --check  # validate only, exit non-zero on problems

Writes the landing page, one page per product (public/picks/<slug>/), a privacy
page, sitemap, robots, and the products.json feed the posting routines read.

Product images are original graphics rendered by graphics.py (needs Pillow) into
public/img/ — never Amazon-hosted photos, which the Associates policies only
license through Amazon's own tools/API. When stock_photos.py has saved a Pixabay
photo of the same kind of item (assets/products/), the graphics include it,
badged "Similar item shown", and the product page captions and credits it.
"""
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "public"
TOP_PICKS = 6  # newest N products shown in "This Week's Top Picks"
EAGER = 3  # first N card images on a page load eagerly (above the fold)
EXCLUDED_ASINS = {"B07TVDFVV9"}  # Associates-excluded; never list
DISCLOSURE = "As an Amazon Associate, we earn from qualifying purchases."
PIN_DISCLOSURE = "#ad As an Amazon Associate I earn from qualifying purchases."
PAID_NOTE = "Paid link · we may earn a commission"
OG_W, OG_H = 1200, 630
PRIVACY_UPDATED = "2026-10-20"  # bump when the privacy text changes
GA_ID = "G-8KQ2TM4X7Z"  # Google Analytics 4 measurement ID; the privacy page discloses it
INDEXNOW_KEY = "122e26ae769c42ab31f69e67f167a338"  # served at /<key>.txt; the deploy workflow pings IndexNow (Bing etc.)
e = html.escape
PRICE_CLAIM = re.compile(r"\$\s?\d|\b\d(\.\d)? ?stars?\b|\bcheapest\b|\blowest price\b|\bunder \$", re.I)
TESTING_CLAIM = re.compile(r"\b(tested|testing|we tried|i tried|i use|we use|hands-on)\b", re.I)


def slug(name):
    s = name.lower().replace("&", " and ")
    s = re.sub(r"[\"'’]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > 60:
        s = s[:60].rsplit("-", 1)[0]
    return s


def load():
    data = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
    errors = []
    seen, slugs = set(), set()
    cats = data["categories"]
    for i, p in enumerate(data["products"]):
        where = f"products[{i}] ({p.get('asin', '?')})"
        for field in ("asin", "name", "category", "blurb", "added"):
            if not str(p.get(field, "")).strip():
                errors.append(f"{where}: missing '{field}'")
        asin = p.get("asin", "")
        if not re.fullmatch(r"B0[0-9A-Z]{8}", asin):
            errors.append(f"{where}: ASIN must look like B0XXXXXXXX")
        if asin in seen:
            errors.append(f"{where}: duplicate ASIN")
        if asin in EXCLUDED_ASINS:
            errors.append(f"{where}: ASIN is Associates-excluded")
        seen.add(asin)
        s = slug(p.get("name", ""))
        if s in slugs:
            errors.append(f"{where}: name gives a duplicate page slug '{s}' — make the name more specific")
        slugs.add(s)
        if p.get("category") not in cats:
            errors.append(f"{where}: unknown category '{p.get('category')}' (add it to 'categories')")
        if bool(str(p.get("suits", "")).strip()) != bool(str(p.get("check", "")).strip()):
            errors.append(f"{where}: 'suits' and 'check' (the Who it's for / Before you buy text) must be filled in together")
        details = f"{p.get('suits', '')} {p.get('check', '')}"
        if TESTING_CLAIM.search(details):
            errors.append(f"{where}: suits/check copy implies hands-on testing/personal use")
        if PRICE_CLAIM.search(details):
            errors.append(f"{where}: no prices, star ratings, or price claims in suits/check copy")
        if p.get("subcategory") not in data.get("subcategories", {}):
            errors.append(f"{where}: unknown subcategory '{p.get('subcategory')}' (add it to 'subcategories')")
        if not str(p.get("award", "")).strip():
            errors.append(f"{where}: missing 'award' (short label for the guide's quick-picks table, e.g. 'Best budget')")
        if "image" in p:
            errors.append(f"{where}: remove 'image' — use an original 'graphic' block, not Amazon-hosted photos")
        g = p.get("graphic") or {}
        if not str(g.get("label", "")).strip() or not str(g.get("headline", "")).strip():
            errors.append(f"{where}: graphic needs 'label' and 'headline'")
        if not isinstance(g.get("points"), list) or len(g.get("points", [])) != 3:
            errors.append(f"{where}: graphic needs exactly 3 'points'")
        try:
            date.fromisoformat(p.get("added", ""))
        except ValueError:
            errors.append(f"{where}: 'added' must be YYYY-MM-DD")
        pin = p.get("pin")
        if pin is not None:
            for field in ("title", "description", "board"):
                if not str(pin.get(field, "")).strip():
                    errors.append(f"{where}: pin missing '{field}'")
            if not str(pin.get("description", "")).startswith(PIN_DISCLOSURE):
                errors.append(f"{where}: pin description must start with '{PIN_DISCLOSURE}'")
            if len(pin.get("title", "")) > 100:
                errors.append(f"{where}: pin title over Pinterest's 100-character limit")
            if len(pin.get("description", "")) > 500:
                errors.append(f"{where}: pin description over Pinterest's 500-character limit")
        # Amazon policy: no static prices or star ratings copied from Amazon.
        for banned in ("price", "rating", "ratings", "stars"):
            if banned in p:
                errors.append(f"{where}: remove '{banned}' — static Amazon prices/ratings violate the Associates agreement")
        # FTC: don't imply hands-on testing we haven't done.
        text = " ".join([p.get("blurb", ""), *(p.get("pin") or {}).values()])
        if TESTING_CLAIM.search(text + " " + p.get("award", "")):
            errors.append(f"{where}: copy implies hands-on testing/personal use — describe the product, not our use of it")
    used = {p.get("subcategory") for p in data["products"]}
    for key, s in data.get("subcategories", {}).items():
        where = f"subcategories['{key}']"
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", key):
            errors.append(f"{where}: key must be a lowercase-hyphenated URL slug")
        if s.get("category") not in cats:
            errors.append(f"{where}: unknown category '{s.get('category')}'")
        for field in ("title", "keyword", "description", "intro"):
            if not str(s.get(field, "")).strip():
                errors.append(f"{where}: missing '{field}'")
        if len(s.get("title", "")) > 60:
            errors.append(f"{where}: title over 60 characters (search results truncate it)")
        if len(s.get("description", "")) > 155:
            errors.append(f"{where}: description over 155 characters (search results truncate it)")
        if len(s.get("criteria", [])) < 2 or len(s.get("guide", [])) < 2:
            errors.append(f"{where}: needs at least 2 'criteria' and 2 'guide' entries")
        copy = json.dumps(s, ensure_ascii=False)
        if TESTING_CLAIM.search(copy):
            errors.append(f"{where}: copy implies hands-on testing/personal use")
        if PRICE_CLAIM.search(copy):
            errors.append(f"{where}: no prices, star ratings, or price claims in guide copy")
        hero = s.get("hero") or {}
        if not str(hero.get("alt", "")).strip() or not str(hero.get("credit", "")).strip():
            errors.append(f"{where}: needs hero {{alt, credit}} for its header photo")
        if not (ROOT / "assets" / "guides" / f"{key}.jpg").exists():
            errors.append(f"{where}: missing header photo assets/guides/{key}.jpg (licensed stock photo, no branded products)")
        if key not in used:
            errors.append(f"{where}: no products assigned — add products or remove the subcategory")
        if "reviewed" in s:
            try:
                date.fromisoformat(s["reviewed"])
            except ValueError:
                errors.append(f"{where}: 'reviewed' must be YYYY-MM-DD")
        own = {p.get("asin") for p in data["products"] if p.get("subcategory") == key}
        for t in s.get("types", []):
            for field in ("name", "best_for", "advantage", "tradeoff", "choose", "skip"):
                if not t.get(field):
                    errors.append(f"{where}: type '{t.get('name', '?')}' missing '{field}'")
            if t.get("pick") and t["pick"] not in own:
                errors.append(f"{where}: type '{t.get('name', '?')}' pick {t['pick']} is not a product in this guide")
    by_asin = {p.get("asin") for p in data["products"]}
    for key, g in data.get("gift_guides", {}).items():
        where = f"gift_guides['{key}']"
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", key):
            errors.append(f"{where}: key must be a lowercase-hyphenated URL slug")
        if key in data.get("subcategories", {}):
            errors.append(f"{where}: key clashes with a subcategory")
        for field in ("title", "keyword", "description", "intro"):
            if not str(g.get(field, "")).strip():
                errors.append(f"{where}: missing '{field}'")
        if len(g.get("title", "")) > 60:
            errors.append(f"{where}: title over 60 characters")
        if len(g.get("description", "")) > 155:
            errors.append(f"{where}: description over 155 characters (search results truncate it)")
        hero = g.get("hero") or {}
        if not hero.get("alt") or not hero.get("credit"):
            errors.append(f"{where}: needs hero {{alt, credit}}")
        if not (ROOT / "assets" / "guides" / f"{key}.jpg").exists():
            errors.append(f"{where}: missing header photo assets/guides/{key}.jpg")
        picks = g.get("picks") or []
        if len(picks) < 3:
            errors.append(f"{where}: needs at least 3 picks")
        for i, pk in enumerate(picks):
            if pk.get("asin") not in by_asin:
                errors.append(f"{where}.picks[{i}]: ASIN {pk.get('asin')} is not in products")
            if not str(pk.get("award", "")).strip() or not str(pk.get("why", "")).strip():
                errors.append(f"{where}.picks[{i}]: needs 'award' and 'why'")
        copy = json.dumps(g, ensure_ascii=False)
        if TESTING_CLAIM.search(copy):
            errors.append(f"{where}: copy implies hands-on testing/personal use")
        if PRICE_CLAIM.search(copy):
            errors.append(f"{where}: no prices, star ratings, or price claims in gift guide copy")
    for key, c in data.get("comparisons", {}).items():
        where = f"comparisons['{key}']"
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", key):
            errors.append(f"{where}: key must be a lowercase-hyphenated URL slug")
        for field in ("title", "description", "h1", "crumb", "intro", "added"):
            if not str(c.get(field, "")).strip():
                errors.append(f"{where}: missing '{field}'")
        if len(c.get("title", "")) > 60:
            errors.append(f"{where}: title over 60 characters")
        if len(c.get("description", "")) > 155:
            errors.append(f"{where}: description over 155 characters (search results truncate it)")
        asins = c.get("products") or []
        if not 2 <= len(asins) <= 3:
            errors.append(f"{where}: compare 2 or 3 products")
        for a in asins:
            if a not in by_asin:
                errors.append(f"{where}: ASIN {a} is not in products")
        subs = {p["subcategory"] for p in data["products"] if p["asin"] in asins}
        if len(subs) != 1:
            errors.append(f"{where}: all compared products must be in the same buying guide")
        if len(c.get("col_names") or []) != len(asins):
            errors.append(f"{where}: needs one 'col_names' entry per product")
        if len(c.get("short") or []) < 2 or any(len(x) != 2 for x in c.get("short") or []):
            errors.append(f"{where}: 'short' needs at least 2 [lead, rest] pairs")
        if not c.get("rows") or any(len(r) != len(asins) + 1 for r in c["rows"]):
            errors.append(f"{where}: every row needs a label plus one cell per product")
        if len(c.get("decide") or []) < 2 or any(len(x) != 2 for x in c.get("decide") or []):
            errors.append(f"{where}: 'decide' needs at least 2 [heading, text] pairs")
        try:
            date.fromisoformat(c.get("added", ""))
        except ValueError:
            errors.append(f"{where}: 'added' must be YYYY-MM-DD")
        copy = json.dumps(c, ensure_ascii=False)
        if TESTING_CLAIM.search(copy):
            errors.append(f"{where}: copy implies hands-on testing/personal use")
        if PRICE_CLAIM.search(copy):
            errors.append(f"{where}: no prices, star ratings, or price claims in comparison copy")
    for ch, t in (data["site"].get("channel_tags") or {}).items():
        if t and not re.fullmatch(r"[a-z0-9-]+-2[0-9]", t):
            errors.append(f"site.channel_tags['{ch}']: '{t}' doesn't look like an Associates tracking ID")
    return data, errors


def amazon_url(asin, tag):
    return f"https://www.amazon.com/dp/{asin}?tag={tag}"


def page_path(p):
    return f"picks/{slug(p['name'])}/"


# Official Amazon photos from the Creators API (written by fetch_amazon_images.py, only when API keys are set).
# Hotlinked from Amazon's servers as the API license requires; never committed, refreshed on every deploy.
AMAZON_IMAGES = {}
# Pixabay photos of a similar item, from assets/products/photos.json (see stock_photos.py).
PHOTO_CREDITS = {}


def photo_alt(p):
    kind = (PHOTO_CREDITS.get(p["asin"]) or {}).get("kind")
    return f"{p['name']} (photo shows a similar {kind}, not this exact product)" if kind else p["name"]


def photo_note(p):
    c = PHOTO_CREDITS.get(p["asin"])
    if not c or AMAZON_IMAGES.get(p["asin"]):
        return ""
    who = f'{e(c["user"])} / ' if c.get("user") else ""
    src = f'<a href="{e(c["page_url"])}" rel="nofollow noopener">{who}Pixabay</a>' if c.get("page_url") else "Pixabay"
    return (f'<p class="photo-note">Photo shows a similar {e(c["kind"])}, not this exact product. '
            f'See the real product photos on Amazon. Photo: {src}</p>')


def picture(p, base, eager=False):
    """Card image: the official Amazon photo when the API supplied one, else our WebP/PNG graphic card."""
    load = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    a = AMAZON_IMAGES.get(p["asin"])
    if a:
        return (f'<img class="amz" src="{e(a["url"])}" alt="{e(p["name"])}" {load} '
                f'width="{a.get("width") or 500}" height="{a.get("height") or 500}" referrerpolicy="no-referrer-when-downgrade">')
    return (f'<picture><source srcset="{base}img/{e(p["asin"])}-sq.webp" type="image/webp">'
            f'<img src="{base}img/{e(p["asin"])}-sq.png" alt="{e(photo_alt(p))}" {load} width="800" height="800"></picture>')


def buy(p, tag):
    return (f'<a class="btn" href="{e(amazon_url(p["asin"], tag))}" rel="sponsored nofollow noopener" target="_blank">Check price on Amazon →</a>\n'
            f'          <small class="paid">{PAID_NOTE}</small>')


def card(p, tag, base="", eager=False):
    return f"""      <article class="card" id="{e(p['asin'])}" data-pl="card">
        <a class="img" href="{e(amazon_url(p['asin'], tag))}" rel="sponsored nofollow noopener" target="_blank">
          {picture(p, base, eager)}
        </a>
        <div class="body">
          <h3><a href="{base}{page_path(p)}">{e(p['name'])}</a></h3>
          <p>{e(p['blurb'])}</p>
          {buy(p, tag)}
        </div>
      </article>"""


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"


CSS = """
  :root { color-scheme:light dark; --bg:#fbf8f3; --card:#fff; --ink:#2b2622; --mut:#6f665d; --acc:#ad512b; --acc-hover:#9a4724; --acc-ink:#fff; --bd:#ece4d8; }
  @media (prefers-color-scheme: dark) { :root { --bg:#1c1a18; --card:#262320; --ink:#f1ebe3; --mut:#b3a99d; --acc:#e07a4f; --acc-hover:#ec9470; --acc-ink:#1c1a18; --bd:#3a3530; } }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--ink); font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  .wrap { max-width:1080px; margin:0 auto; padding:0 16px; }
  .disclosure { position:sticky; top:0; z-index:10; background:var(--ink); color:var(--bg); text-align:center; font-size:13px; padding:6px 16px; }
  .disclosure a { color:inherit; }
  a:focus-visible, button:focus-visible, input:focus-visible { outline:3px solid var(--acc); outline-offset:2px; }
  .disclosure a:focus-visible { outline-color:var(--bg); }
  .skip { position:absolute; left:-9999px; top:0; z-index:20; background:var(--card); color:var(--ink); padding:8px 16px; border-radius:0 0 8px 0; }
  .skip:focus { left:0; }
  header { padding:48px 0 24px; text-align:center; }
  h1 { font-size:clamp(28px,5vw,44px); line-height:1.15; }
  h1 .sub { display:block; font-size:clamp(16px,2.4vw,20px); font-weight:600; color:var(--acc); margin-top:8px; }
  header p { color:var(--mut); max-width:560px; margin:12px auto 0; }
  nav { margin-top:16px; display:flex; gap:16px; justify-content:center; flex-wrap:wrap; font-size:14px; }
  nav a, .crumbs a, .brand { color:var(--acc); }
  nav a { display:inline-block; padding:6px 2px; }
  section { padding:24px 0; }
  h2 { font-size:24px; margin-bottom:16px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:20px; }
  .card { background:var(--card); border:1px solid var(--bd); border-radius:14px; overflow:hidden; display:flex; flex-direction:column; scroll-margin-top:48px; }
  .card:target { outline:3px solid var(--acc); }
  .img { background:#fbf8f3; display:block; aspect-ratio:1; }  /* graphics are cream in both themes */
  .img picture { display:block; width:100%; height:100%; }
  .img img { width:100%; height:100%; object-fit:cover; display:block; }
  .img img.amz { object-fit:contain; background:#fff; padding:8%; }
  .body { padding:16px; display:flex; flex-direction:column; gap:10px; flex:1; }
  h3 { font-size:18px; line-height:1.3; }
  h3 a { color:inherit; text-decoration:none; }
  h3 a:hover { text-decoration:underline; }
  .body p { color:var(--mut); font-size:15px; flex:1; }
  .btn { display:inline-block; background:var(--acc); color:var(--acc-ink); text-decoration:none; font-weight:600; padding:10px 16px; border-radius:8px; text-align:center; }
  .btn:hover { background:var(--acc-hover); }
  .paid { display:block; text-align:center; color:var(--mut); font-size:12px; margin-top:-4px; }
  .top { padding:20px 0 0; font-size:14px; display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; }
  .brand { font-weight:700; text-decoration:none; }
  .pick { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:32px; align-items:start; padding:24px 0; }
  @media (max-width:720px) { .pick { grid-template-columns:1fr; gap:20px; } }
  .pick .img { border-radius:14px; overflow:hidden; border:1px solid var(--bd); }
  .photo-note { font-size:13px; color:var(--mut); margin-top:8px; }
  .photo-note a { color:inherit; }
  .pick .info { display:flex; flex-direction:column; gap:14px; }
  .pick h1 { font-size:clamp(26px,4vw,36px); }
  .pick .lede { color:var(--mut); font-size:17px; }
  .pick .buy { display:inline-flex; flex-direction:column; gap:10px; align-self:flex-start; }
  .pick ul { list-style:none; display:flex; flex-direction:column; gap:6px; }
  .pick li::before { content:"✓ "; color:var(--acc); font-weight:700; }
  .prose { max-width:720px; padding:32px 0; }
  .prose h1 { font-size:32px; margin-bottom:8px; }
  .prose h2 { font-size:20px; margin:24px 0 8px; }
  .prose p, .prose li { margin-bottom:10px; }
  .prose ul, .prose ol { padding-left:20px; }
  .prose a { color:var(--acc); }
  .prose a.btn { color:var(--acc-ink); text-decoration:none; }
  .signup { background:var(--card); border:1px solid var(--bd); border-radius:14px; padding:28px 20px; text-align:center; margin:24px 0; }
  .signup p { color:var(--mut); }
  .signup form { display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-top:14px; }
  .signup input[type=email] { padding:10px 12px; border:1px solid var(--bd); border-radius:8px; min-width:0; flex:0 1 280px; font:inherit; background:var(--bg); color:var(--ink); }
  .signup button { border:0; cursor:pointer; font:inherit; }
  .signup small { display:block; margin-top:10px; color:var(--mut); }
  .signup small a { color:var(--acc); }
  .hidden { position:absolute; left:-9999px; }
  .hero { margin:20px 0 0; border-radius:14px; overflow:hidden; position:relative; background:var(--bd); aspect-ratio:5/2; }
  .hero img { width:100%; height:100%; object-fit:cover; display:block; }
  .hero figcaption { position:absolute; right:8px; bottom:6px; font-size:11px; color:#fff; background:rgba(0,0,0,.45); padding:2px 6px; border-radius:4px; }
  .gcard { padding:0 0 16px !important; overflow:hidden; }
  .gcard > strong, .gcard > span:not(.thumb), .gcard > em { padding:0 16px; }
  .gcard .thumb { display:block; aspect-ratio:5/2; background:var(--bd); margin-bottom:6px; }
  .gcard .thumb img { width:100%; height:100%; object-fit:cover; display:block; }
  .guide { padding:32px 0 8px; text-align:left; max-width:760px; }
  .guide p { margin-left:0; margin-right:0; max-width:none; }
  .guide .updated { color:var(--mut); font-size:14px; margin-top:8px; }
  .callout { background:var(--card); border:1px solid var(--bd); border-left:4px solid var(--acc); border-radius:8px; padding:12px 14px; margin:16px 0; font-size:14px; color:var(--ink); }
  .guide .intro { color:var(--ink); font-size:17px; margin:0; }
  .quick { width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--bd); border-radius:14px; overflow:hidden; }
  .quick th, .quick td { padding:10px 12px; border-bottom:1px solid var(--bd); text-align:left; vertical-align:middle; }
  .quick th { font-size:13px; color:var(--mut); }
  .quick td:first-child { font-weight:600; }
  .quick a { color:var(--acc); }
  .quick a.btn { color:var(--acc-ink); white-space:nowrap; }
  .btn.sm { padding:6px 10px; font-size:14px; }
  @media (max-width:640px) { .quick thead { display:none; } .quick tr { display:block; border-bottom:1px solid var(--bd); padding:8px 0; } .quick td { display:block; border:0; padding:4px 12px; } }
  .roundup { border-top:1px solid var(--bd); }
  .roundup h2 { font-size:clamp(22px,3vw,28px); margin:0; }
  .roundup h2 a { color:inherit; text-decoration:none; }
  .roundup .sub { color:var(--mut); font-size:15px; }
  .award { color:var(--acc); font-weight:700; font-size:14px; text-transform:uppercase; letter-spacing:.04em; }
  .more { color:var(--acc); font-size:14px; }
  .prose.wide { max-width:760px; padding:24px 0; }
  .prose h3 { font-size:17px; margin:16px 0 4px; }
  .vs-wrap { overflow-x:auto; margin:12px 0 8px; }
  .vs { width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--bd); font-size:15px; }
  .vs th, .vs td { padding:10px 12px; border-bottom:1px solid var(--bd); text-align:left; vertical-align:top; }
  .vs thead th { font-size:14px; }
  .vs tbody th { color:var(--mut); font-weight:600; width:22%; }
  .links { list-style:none; display:flex; flex-wrap:wrap; gap:10px 20px; }
  .links a { color:var(--acc); }
  .guides { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:14px; }
  .gcard { background:var(--card); border:1px solid var(--bd); border-radius:12px; padding:16px; text-decoration:none; color:var(--ink); display:flex; flex-direction:column; gap:6px; }
  .gcard:hover { border-color:var(--acc); }
  .gcard strong { font-size:16px; line-height:1.3; }
  .gcard span { color:var(--mut); font-size:14px; }
  .gcard em { color:var(--acc); font-style:normal; font-size:14px; font-weight:600; }
  .contact { display:flex; flex-direction:column; gap:14px; margin:20px 0; }
  .contact label { display:flex; flex-direction:column; gap:4px; font-weight:600; font-size:14px; }
  .contact input, .contact textarea { padding:10px 12px; border:1px solid var(--bd); border-radius:8px; font:inherit; font-weight:400; background:var(--card); color:var(--ink); }
  .contact textarea:focus-visible, .contact input:focus-visible { outline:3px solid var(--acc); outline-offset:2px; }
  .contact button { border:0; cursor:pointer; font:inherit; align-self:flex-start; }
  .err { color:#b3261e; font-weight:600; }
  @media (prefers-color-scheme: dark) { .err { color:#f2b8b5; } }
  .fnav { display:flex; flex-wrap:wrap; gap:6px 16px; margin-bottom:12px; font-size:14px; }
  footer { border-top:1px solid var(--bd); padding:24px 0 40px; color:var(--mut); font-size:13px; }
  footer a { color:var(--acc); }
"""


def track_js(site):
    """Records every Amazon link click: GA4 'amazon_click' event plus a beacon to /click.php (page, ASIN,
    channel, placement; no IP or cookies). If site.channel_tags has a tracking ID for the visitor's channel
    (from utm_source or the referrer), the link's tag is swapped to it at click time."""
    tags = {k: v for k, v in (site.get("channel_tags") or {}).items() if v}
    js = """(function(){var T=%s,ch,cp='',s=sessionStorage,q=new URLSearchParams(location.search);
try{if(q.get('utm_source')){ch=q.get('utm_source').toLowerCase();cp=q.get('utm_campaign')||'';s.setItem('kff_ch',ch);s.setItem('kff_cp',cp)}else{ch=s.getItem('kff_ch');cp=s.getItem('kff_cp')||''}}catch(e){}
if(!ch){var r=document.referrer;ch=/pinterest\\./.test(r)?'pinterest':/(facebook|instagram)\\.|fb\\.me/.test(r)?'facebook':/google\\./.test(r)?'google':/bing\\./.test(r)?'bing':(r&&r.indexOf(location.host)<0?'referral':'direct');try{s.setItem('kff_ch',ch)}catch(e){}}
document.addEventListener('click',function(ev){var a=ev.target.closest&&ev.target.closest('a[href*="amazon.com/dp/"]');if(!a)return;
var m=a.href.match(/\\/dp\\/([A-Z0-9]{10})/),asin=m?m[1]:'',pe=a.closest('[data-pl]'),pl=pe?pe.getAttribute('data-pl'):'other';
if(T[ch])a.href=a.href.replace(/([?&]tag=)[^&#]*/,'$1'+T[ch]);
if(window.gtag)gtag('event','amazon_click',{asin:asin,placement:pl,channel:ch,link_page:location.pathname,transport_type:'beacon'});
try{navigator.sendBeacon('/click.php',new URLSearchParams({p:location.pathname,a:asin,c:ch,l:pl,k:cp}))}catch(e){}},true)})();""" % json.dumps(tags)
    return "<script>" + js + "</script>\n"


def head(site, title, description, path, og_image, og_alt, og_w, og_h, extra="", noindex=False):
    url = f"{site['url']}/{path}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(url)}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta name="theme-color" content="#fbf8f3" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#1c1a18" media="(prefers-color-scheme: dark)">
{'<meta name="robots" content="noindex">' + chr(10) if noindex else ""}<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(site['name'])}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(og_image)}">
<meta property="og:image:width" content="{og_w}">
<meta property="og:image:height" content="{og_h}">
<meta property="og:image:alt" content="{e(og_alt)}">
<meta name="twitter:card" content="summary_large_image">
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA_ID}');</script>
{track_js(site)}{extra}<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="disclosure">{DISCLOSURE} <a href="/privacy/">Learn more</a></div>
<div class="wrap">
"""


def signup():
    return """    <section class="signup" id="updates">
      <h2>Free printable: the Small-Kitchen Measuring Checklist</h2>
      <p>Measure once, buy the right size. Get the one-page checklist of every measurement our guides are built around, plus one short email when we add new picks. No spam, unsubscribe anytime.</p>
      <form name="updates" method="POST" action="/subscribe.php">
        <p class="hidden"><label>Don't fill this out if you're human: <input name="bot-field" tabindex="-1" autocomplete="off"></label></p>
        <input type="email" name="email" placeholder="you@example.com" required autocomplete="email" aria-label="Email address">
        <button class="btn" type="submit">Send me the checklist</button>
      </form>
      <small>We only use your email to send new kitchen picks, and never sell or share it. See our <a href="/privacy/">privacy policy</a>.</small>
    </section>
"""


def foot(site):
    links = "".join(f'<a href="/{h["path"]}">{e(h["nav"])}</a>' for h in HUBS.values())
    return f"""  <footer>
    <nav class="fnav" aria-label="Site">{links}<a href="/#gifts">Gift Guides</a><a href="/newsletter/">Free Checklist</a><a href="/about/">About</a><a href="/contact/">Contact</a></nav>
    <p>{e(site['name'])} is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com. {DISCLOSURE} Product details can change — check the current listing on Amazon before you buy.</p>
    <p style="margin-top:8px">Follow along on <a href="{e(site['pinterest'])}">Pinterest</a> and <a href="{e(site['facebook'])}">Facebook</a> · <a href="/privacy/">Privacy policy</a></p>
  </footer>
</div>
</body>
</html>
"""


def site_ld(site, products):
    org = {"@type": "Organization", "@id": f"{site['url']}/#org", "name": site["name"], "url": f"{site['url']}/",
           "logo": f"{site['url']}/img/og.png", "sameAs": [site["pinterest"], site["facebook"]]}
    web = {"@type": "WebSite", "@id": f"{site['url']}/#site", "name": site["name"], "url": f"{site['url']}/",
           "description": site["tagline"], "publisher": {"@id": f"{site['url']}/#org"}}
    items = {"@type": "ItemList", "name": f"{site['name']} kitchen picks",
             "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": p["name"],
                                  "url": f"{site['url']}/{page_path(p)}"} for i, p in enumerate(products)]}
    return ld({"@context": "https://schema.org", "@graph": [org, web, items]})


def render_home(data, products):
    site, tag = data["site"], data["site"]["associate_tag"]
    top = products[:TOP_PICKS]
    top_asins = {p["asin"] for p in top}
    sections = []
    for key, label in data["categories"].items():
        items = [p for p in products if p["category"] == key and p["asin"] not in top_asins]
        if items:
            cards = "\n".join(card(p, tag) for p in items)
            sections.append(f'    <section id="{e(key)}">\n      <h2>{e(label)}</h2>\n      <div class="grid">\n{cards}\n      </div>\n    </section>')
    nav = ('<a href="#gifts">Gift Guides</a> ' if data.get("gift_guides") else "") + '<a href="#guides">Buying Guides</a> ' + " ".join(
        f'<a href="/{h["path"]}">{e(h["nav"])}</a>' for h in HUBS.values())
    top_cards = "\n".join(card(p, tag, eager=i < EAGER) for i, p in enumerate(top))
    tiles = "\n".join(
        f'        <a class="gcard" href="{guide_path(k)}"><span class="thumb">{hero_picture(k, "", "", wide=False)}</span><strong>{e(s["title"])}</strong>'
        f'<span>{e(s["description"])}</span><em>{len(guide_products(products, k))} picks · Read the guide →</em></a>'
        for k, s in data["subcategories"].items())
    guides = f"""    <section id="guides">
      <h2>Buying Guides</h2>
      <div class="guides">
{tiles}
      </div>
    </section>"""
    gifts = ""
    if data.get("gift_guides"):
        gtiles = "\n".join(
            f'        <a class="gcard" href="{gift_path(k)}"><span class="thumb">{hero_picture(k, "", "", wide=False)}</span><strong>{e(g["title"])}</strong>'
            f'<span>{e(g["description"])}</span><em>{len(g["picks"])} picks · See the gift guide →</em></a>'
            for k, g in data["gift_guides"].items())
        gifts = f"""    <section id="gifts">
      <h2>Holiday Gift Guides</h2>
      <div class="guides">
{gtiles}
      </div>
    </section>
"""
    title = seo_title("Small Kitchen Organization Ideas, Gadgets & Gear", site)
    return head(site, title, site["tagline"], "", f"{site['url']}/img/og.png",
                f"{site['name']} — {site['tagline']}", OG_W, OG_H, site_ld(site, products) + "\n") + f"""  <header>
    <h1>{e(site['name'])}<span class="sub">Organization, gadgets &amp; small appliances for small kitchens</span></h1>
    <p>{e(site['tagline'])}</p>
    <nav>{nav}</nav>
  </header>
  <main id="main">
{gifts}    <section id="top-picks">
      <h2>This Week's Top Picks</h2>
      <div class="grid">
{top_cards}
      </div>
    </section>
{guides}
{chr(10).join(sections)}
{signup()}  </main>
""" + foot(site)


def seo_title(text, site, limit=60):
    """<title> under `limit` chars: add the site name only when it fits, else trim at a word boundary."""
    branded = f"{text} | {site['name']}"
    if len(branded) <= limit:
        return branded
    if len(text) <= limit:
        return text
    cut = text[:limit + 1].rsplit(" ", 1)[0].rstrip(",;:—-&")
    for joiner in (" with ", ", "):  # prefer ending at a phrase boundary over a dangling word
        if joiner in cut and len(cut.rsplit(joiner, 1)[0]) >= 30:
            return cut.rsplit(joiner, 1)[0]
    return cut


def describe(text, limit=155):
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:—-") + "…"


def render_pick(data, p, products):
    site, tag = data["site"], data["site"]["associate_tag"]
    sub = data["subcategories"][p["subcategory"]]
    base = "../../"
    same = [q for q in products if q["subcategory"] == p["subcategory"] and q["asin"] != p["asin"]]
    near = [q for q in products if q["category"] == p["category"] and q["subcategory"] != p["subcategory"]]
    more = (same + near)[:3]
    more_html = ""
    cmp_links = "".join(
        f'      <p style="margin-top:8px"><a class="more" href="{base}{comparison_path(k)}">Compare: {e(c["h1"])} →</a></p>\n'
        for k, c in data.get("comparisons", {}).items() if p["asin"] in c["products"])
    details_html = ""
    if p.get("suits"):
        details_html = (f'    <section class="prose wide">\n      <h2>Who it\'s for</h2>\n      <p>{e(p["suits"])}</p>\n'
                        f'      <h2>Before you buy</h2>\n      <p>{e(p["check"])}</p>\n'
                        f'      <p><small>Product details can change, so check the current listing on Amazon.</small></p>\n    </section>\n')
    if more:
        cards = "\n".join(card(q, tag, base) for q in more)
        more_html = (f'    <section>\n      <h2>More picks like this</h2>\n      <div class="grid">\n{cards}\n      </div>\n'
                     f'      <p style="margin-top:16px"><a class="more" href="{base}{guide_path(p["subcategory"])}">See the full guide: {e(sub["title"])} →</a></p>\n'
                     f'{cmp_links}    </section>\n')
    crumbs = ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": site["name"], "item": f"{site['url']}/"},
        {"@type": "ListItem", "position": 2, "name": sub["title"], "item": f"{site['url']}/{guide_path(p['subcategory'])}"},
        {"@type": "ListItem", "position": 3, "name": p["name"], "item": f"{site['url']}/{page_path(p)}"}]})
    points = "".join(f"<li>{e(pt)}</li>" for pt in p["graphic"]["points"])
    title = seo_title(p["name"], site)
    return head(site, title, describe(p["blurb"]), page_path(p), f"{site['url']}/img/{p['asin']}.png",
                p["graphic"]["headline"], 1000, 1500, crumbs + "\n") + f"""  <div class="top">
    <a class="brand" href="{base}">{e(site['name'])}</a>
    <span class="crumbs"><a href="{base}">Home</a> › <a href="{base}{guide_path(p['subcategory'])}">{e(sub['title'])}</a></span>
  </div>
  <main id="main">
    <p class="callout">{DISCLOSURE} The "Check price on Amazon" button below is an affiliate link.</p>
    <article class="pick" id="{e(p['asin'])}" data-pl="pick">
      <div class="media">
      <a class="img" href="{e(amazon_url(p['asin'], tag))}" rel="sponsored nofollow noopener" target="_blank">
        {picture(p, base, eager=True)}
      </a>
      {photo_note(p)}
      </div>
      <div class="info">
        <h1>{e(p['name'])}</h1>
        <p class="lede">{e(p['blurb'])}</p>
        <ul>{points}</ul>
        <div class="buy">
          {buy(p, tag)}
        </div>
      </div>
    </article>
{details_html}{more_html}{signup()}  </main>
""" + foot(site)


def hero_picture(key, base, alt, eager=False, wide=True):
    """Guide header photo (licensed stock image, no branded products): WebP + JPEG fallback."""
    load = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    if wide:
        return (f'<picture><source type="image/webp" srcset="{base}img/guides/{key}-800.webp 800w, {base}img/guides/{key}.webp 1600w" sizes="(max-width: 800px) 100vw, 1048px">'
                f'<img src="{base}img/guides/{key}.jpg" alt="{e(alt)}" {load} width="1600" height="640"></picture>')
    return (f'<picture><source type="image/webp" srcset="{base}img/guides/{key}-800.webp">'
            f'<img src="{base}img/guides/{key}-800.jpg" alt="" {load} width="800" height="320"></picture>')


def render_hero_images(data):
    """Copy each guide's header photo from assets/guides/<key>.jpg into public/img/guides (JPEG + WebP, 1600 and 800 wide)."""
    from PIL import Image
    src_dir, out = ROOT / "assets" / "guides", OUT / "img" / "guides"
    out.mkdir(parents=True, exist_ok=True)
    for key in list(data["subcategories"]) + list(data.get("gift_guides", {})):
        src = src_dir / f"{key}.jpg"
        im = Image.open(src).convert("RGB")
        for suffix, width in (("", 1600), ("-800", 800)):
            size = (width, round(im.height * width / im.width))
            r = im.resize(size, Image.LANCZOS) if im.width != width else im
            r.save(out / f"{key}{suffix}.jpg", "JPEG", quality=80, optimize=True, progressive=True)
            r.save(out / f"{key}{suffix}.webp", "WEBP", quality=78, method=6)


def comparison_path(key):
    return f"comparisons/{key}/"


def comparison_guide_key(data, c):
    by_asin = {p["asin"]: p for p in data["products"]}
    return by_asin[c["products"][0]]["subcategory"]


def render_comparison(data, key):
    site, tag = data["site"], data["site"]["associate_tag"]
    c = data["comparisons"][key]
    by_asin = {p["asin"]: p for p in data["products"]}
    items = [by_asin[a] for a in c["products"]]
    gkey = items[0]["subcategory"]
    sub = data["subcategories"][gkey]
    base = "../../"
    crumbs = ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": site["name"], "item": f"{site['url']}/"},
        {"@type": "ListItem", "position": 2, "name": sub["title"], "item": f"{site['url']}/{guide_path(gkey)}"},
        {"@type": "ListItem", "position": 3, "name": c["title"], "item": f"{site['url']}/{comparison_path(key)}"}]})
    short = "\n".join(f"      <li><strong>{e(lead)}</strong> {e(rest)}</li>" for lead, rest in c["short"])
    thead = "".join(f'<th scope="col">{e(n)}</th>' for n in c["col_names"])
    rows = "\n".join('        <tr><th scope="row">' + e(r[0]) + "</th>" + "".join(f"<td>{e(x)}</td>" for x in r[1:]) + "</tr>"
                     for r in c["rows"])
    decide = "".join(f"      <h3>{e(h)}</h3>\n      <p>{e(t)}</p>\n" for h, t in c["decide"])
    cards = "\n".join(card(q, tag, base) for q in items)
    first = items[0]
    return head(site, c["title"], c["description"], comparison_path(key), f"{site['url']}/img/{first['asin']}.png",
                first["graphic"]["headline"], 1000, 1500, crumbs + "\n") + f"""  <div class="top">
    <a class="brand" href="{base}">{e(site['name'])}</a>
    <span class="crumbs"><a href="{base}">Home</a> › <a href="{base}{guide_path(gkey)}">{e(sub['title'])}</a> › {e(c['crumb'])}</span>
  </div>
  <main id="main">
    <p class="callout">{DISCLOSURE} The "Check price on Amazon" buttons below are affiliate links.</p>
    <section class="prose wide">
      <h1>{e(c['h1'])}</h1>
      <p>{e(c['intro'])}</p>
      <h2>The short answer</h2>
      <ul>
{short}
      </ul>
      <h2>Side-by-side</h2>
      <div class="vs-wrap">
        <table class="vs">
          <thead><tr><th scope="col"></th>{thead}</tr></thead>
          <tbody>
{rows}
          </tbody>
        </table>
      </div>
      <p><small>Product details can change. Check the current listing on Amazon before you buy.</small></p>
      <h2>How to decide</h2>
{decide}    </section>
    <section>
      <h2>Our picks</h2>
      <div class="grid">
{cards}
      </div>
      <p style="margin-top:16px"><a class="more" href="{base}{guide_path(gkey)}">See the full guide: {e(sub['title'])} →</a></p>
    </section>
{signup()}  </main>
""" + foot(site)


def guide_path(key):
    return f"guides/{key}/"


def gift_path(key):
    return f"gifts/{key}/"


def gift_products(data, key):
    """A gift guide's picks in listed order, each carrying the guide's own award and gift note."""
    by_asin = {p["asin"]: p for p in data["products"]}
    return [dict(by_asin[pk["asin"]], award=pk["award"], why=pk["why"]) for pk in data["gift_guides"][key]["picks"]]


def guide_products(products, key):
    """A guide's picks, in products.json order (curated order, not newest-first)."""
    return [p for p in products if p["subcategory"] == key]


def render_guide(data, key, items):
    site, tag = data["site"], data["site"]["associate_tag"]
    gift = key in data.get("gift_guides", {})
    s = data["gift_guides"][key] if gift else data["subcategories"][key]
    cat_label = "Holiday Gift Guides" if gift else HUBS[s["category"]]["nav"]
    cat_href = "#gifts" if gift else HUBS[s["category"]]["path"]
    path = gift_path(key) if gift else guide_path(key)
    base = "../../"
    updated = max([p["added"] for p in items] + ([s["reviewed"]] if s.get("reviewed") else []))
    year = updated[:4]
    month = date.fromisoformat(updated).strftime("%B %Y")
    rows = "\n".join(
        f'        <tr><td data-label="Best for">{e(p["award"])}</td>'
        f'<td data-label="Pick"><a href="#{e(p["asin"])}">{e(p["name"])}</a></td>'
        f'<td><a class="btn sm" href="{e(amazon_url(p["asin"], tag))}" rel="sponsored nofollow noopener" target="_blank">Check price on Amazon</a></td></tr>'
        for p in items)
    sections = []
    for i, p in enumerate(items):
        points = "".join(f"<li>{e(pt)}</li>" for pt in p["graphic"]["points"])
        lede = (f'<p class="lede">{e(p["why"])}</p>\n        <p class="sub">{e(p["blurb"])}</p>' if p.get("why")
                else f'<p class="lede">{e(p["blurb"])}</p>')
        sections.append(f"""    <article class="pick roundup" id="{e(p['asin'])}" data-pl="{'gift' if gift else 'roundup'}">
      <a class="img" href="{base}{page_path(p)}">
        {picture(p, base, eager=i < 1)}
      </a>
      <div class="info">
        <p class="award">{i + 1}. {e(p['award'])}</p>
        <h2><a href="{base}{page_path(p)}">{e(p['name'])}</a></h2>
        {lede}
        <ul>{points}</ul>
        <div class="buy">
          {buy(p, tag)}
          <a class="more" href="{base}{page_path(p)}">Full details on this pick →</a>
        </div>
      </div>
    </article>""")
    quick_answer = f'\n      <p class="callout"><strong>Quick answer:</strong> {e(s["quick_answer"])}</p>' if s.get("quick_answer") else ""
    cmp_callout = ""
    cmps = [(k, c) for k, c in data.get("comparisons", {}).items() if not gift and comparison_guide_key(data, c) == key]
    if cmps:
        cmp_callout = ('\n      <p class="callout"><strong>Head-to-head:</strong> '
                       + " · ".join(f'<a href="{base}{comparison_path(k)}">{e(c["h1"])}</a>' for k, c in cmps) + "</p>")
    measure = ""
    if s.get("measure"):
        measure = (f"    <section class=\"prose wide\">\n      <h2>{e(s.get('measure_heading', 'Before you buy, measure these'))}</h2>\n      <ol>"
                   + "".join(f"<li><strong>{e(h)}:</strong> {e(t)}</li>" for h, t in s["measure"])
                   + "</ol>\n" + (f"      <p>{e(s['measure_note'])}</p>\n" if s.get("measure_note") else "") + "    </section>\n")
    types = ""
    if s.get("types"):
        by_asin = {p["asin"]: p for p in items}

        def type_pick(t):
            p = by_asin.get(t.get("pick"))
            return f'<a href="#{e(p["asin"])}">{e(p["name"])}</a>' if p else "No pick listed yet"
        type_rows = "\n".join(
            f'        <tr><td data-label="Type">{e(t["name"])}</td><td data-label="Best for">{e(t["best_for"])}</td>'
            f'<td data-label="Main advantage">{e(t["advantage"])}</td><td data-label="Main tradeoff">{e(t["tradeoff"])}</td>'
            f'<td data-label="Our pick">{type_pick(t)}</td></tr>' for t in s["types"])
        details = "".join(
            f'      <h3>{e(t["name"])}</h3>\n' + (f'      <p>{e(t["summary"])}</p>\n' if t.get("summary") else "")
            + '      <p><strong>Choose this type if:</strong></p>\n      <ul>' + "".join(f"<li>{e(x)}</li>" for x in t["choose"]) + "</ul>\n"
            + '      <p><strong>Skip it if:</strong></p>\n      <ul>' + "".join(f"<li>{e(x)}</li>" for x in t["skip"]) + "</ul>\n"
            for t in s["types"])
        types = f"""    <section>
      <h2>{e(s.get('types_heading', 'Which type fits your space?'))}</h2>
      <table class="quick">
        <thead><tr><th>Type</th><th>Best for</th><th>Main advantage</th><th>Main tradeoff</th><th>Our pick</th></tr></thead>
        <tbody>
{type_rows}
        </tbody>
      </table>
    </section>
    <section class="prose wide">
      <h2>Who should choose, or skip, each type</h2>
{details}    </section>
"""
    situations = ""
    if s.get("situations"):
        situations = ("    <section class=\"prose wide\">\n      <h2>Picks for specific situations</h2>\n"
                      + "".join(f"      <h3>{e(h)}</h3>\n      <p>{e(t)}</p>\n" for h, t in s["situations"]) + "    </section>\n")
    criteria = "".join(f"<li>{e(c)}</li>" for c in s["criteria"])
    guide = "".join(f"<h3>{e(h)}</h3><p>{e(t)}</p>" for h, t in s["guide"])
    faq = s.get("faq", [])
    faq_html = ""
    if faq:
        faq_html = "    <section class=\"prose wide\">\n      <h2>Frequently asked questions</h2>\n" + "".join(
            f"      <h3>{e(q)}</h3>\n      <p>{e(a)}</p>\n" for q, a in faq) + "    </section>\n"
    if gift:
        others = [(gift_path(k), v["title"]) for k, v in data["gift_guides"].items() if k != key]
        rel_heading = "More holiday gift guides"
    else:
        others = [(guide_path(k), v["title"]) for k, v in data["subcategories"].items() if k != key and v["category"] == s["category"]]
        rel_heading = "Related buying guides"
    related = ""
    if others:
        related = f"    <section>\n      <h2>{rel_heading}</h2>\n      <ul class=\"links\">" + "".join(
            f'<li><a href="{base}{u}">{e(t)}</a></li>' for u, t in others) + "</ul>\n    </section>\n"
    url = f"{site['url']}/{path}"
    graph = [
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": site["name"], "item": f"{site['url']}/"},
            {"@type": "ListItem", "position": 2, "name": cat_label, "item": f"{site['url']}/{cat_href}"},
            {"@type": "ListItem", "position": 3, "name": s["title"], "item": url}]},
        {"@type": "Article", "headline": s["title"], "description": s["description"], "dateModified": updated,
         "url": url, "publisher": {"@id": f"{site['url']}/#org"}, "image": f"{site['url']}/img/guides/{key}.jpg"},
        {"@type": "ItemList", "name": s["title"], "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": p["name"], "url": f"{site['url']}/{page_path(p)}"}
            for i, p in enumerate(items)]}]
    if faq:
        graph.append({"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})
    title = seo_title(f"{s['title']} ({year})", site)
    return head(site, title, s["description"], path, f"{site['url']}/img/guides/{key}.jpg",
                s["hero"]["alt"], 1600, 640, ld({"@context": "https://schema.org", "@graph": graph}) + "\n") + f"""  <div class="top">
    <a class="brand" href="{base}">{e(site['name'])}</a>
    <span class="crumbs"><a href="{base}">Home</a> › <a href="{base}{cat_href}">{e(cat_label)}</a></span>
  </div>
  <main id="main">
    <figure class="hero">{hero_picture(key, base, s['hero']['alt'], eager=True)}<figcaption>Photo: {e(s['hero']['credit'])}</figcaption></figure>
    <header class="guide">
      <h1>{e(s['title'])} ({year})</h1>
      <p class="updated">Updated {month} · {len(items)} picks</p>
      <p class="callout"><strong>Affiliate disclosure:</strong> {e(site['name'])} is reader-supported. Buttons marked "Check price on Amazon" are affiliate links. {DISCLOSURE} It costs you nothing extra, and picks are chosen from product research, not commission rates.</p>
      <p class="intro">{e(s['intro'])}</p>{quick_answer}{cmp_callout}
    </header>
    <section>
      <h2>{"The gift list" if gift else "Quick picks"}</h2>
      <table class="quick" data-pl="quick">
        <thead><tr><th>Best for</th><th>Pick</th><th><span class="hidden">Link</span></th></tr></thead>
        <tbody>
{rows}
        </tbody>
      </table>
    </section>
{measure}{types}{situations}    <section class="prose wide">
      <h2>How we chose</h2>
      <p>Each pick was selected by comparing manufacturer specifications and recurring themes in owner feedback against these criteria:</p>
      <ul>{criteria}</ul>
      <p>Product details change — confirm sizes and current price on the Amazon listing before buying.</p>
    </section>
{chr(10).join(sections)}
    <section class="prose wide">
      <h2>{"How to choose the right gift" if gift else "Buying guide: what to look for"}</h2>
      {guide}
    </section>
{faq_html}{related}{signup()}  </main>
""" + foot(site)


def render_privacy(data):
    site = data["site"]
    return head(site, f"Privacy Policy | {site['name']}", f"How {site['name']} handles cookies, affiliate links, and email sign-ups.",
                "privacy/", f"{site['url']}/img/og.png", site["name"], OG_W, OG_H) + f"""  <div class="top"><a class="brand" href="../">{e(site['name'])}</a></div>
  <main id="main" class="prose">
    <h1>Privacy Policy</h1>
    <p>Last updated {PRIVACY_UPDATED}.</p>
    <h2>Affiliate links and cookies</h2>
    <p>{e(site['name'])} is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com. {DISCLOSURE}</p>
    <p>When you click a product link on this site you go to Amazon.com. Third parties, including Amazon, may place and read cookies on your browser, or use web beacons, to collect information such as which link you clicked and whether a purchase followed, so that we can be credited for the referral. That information is handled under <a href="https://www.amazon.com/gp/help/customer/display.html?nodeId=468496" rel="nofollow noopener">Amazon's Privacy Notice</a>. We never see your Amazon account, payment details, or what you personally bought.</p>
    <p>This site itself sets no advertising cookies.</p>
    <h2>Analytics</h2>
    <p>We use Google Analytics to understand how visitors use this site, such as which pages are viewed, how visitors arrive (for example from Pinterest or a search engine), and what device and browser are used. Google Analytics sets cookies and collects information such as your approximate location, browser, and pages visited; we see only aggregate reports and never your name or contact details. This information is handled under <a href="https://policies.google.com/privacy" rel="nofollow noopener">Google's Privacy Policy</a> (see also <a href="https://policies.google.com/technologies/partner-sites" rel="nofollow noopener">how Google uses data from sites that use its services</a>). You can opt out with the <a href="https://tools.google.com/dlpage/gaoptout" rel="nofollow noopener">Google Analytics opt-out browser add-on</a> or by blocking cookies in your browser.</p>
    <p>When you click a link to Amazon, the site also records which page and product the click came from, where the visit originated (for example Pinterest or a search engine) and the time, so we can tell which pages are useful. This click log stores no IP address, cookies, name or contact details.</p>
    <h2>Email sign-up</h2>
    <p>If you join our email list, we collect only the email address you enter. It is stored on our web host, Hostinger (see <a href="https://www.hostinger.com/legal/privacy-policy" rel="nofollow noopener">Hostinger's privacy policy</a>). We use your address only to send new kitchen picks. We never sell, rent, or share it. Every email includes an unsubscribe link, and you can ask us to delete your address at any time.</p>
    <h2>Contact form</h2>
    <p>If you use our contact form, we receive the name, email address and message you enter, by email and as a backup copy stored on our web host. We use them only to reply to you and delete them on request.</p>
    <h2>Hosting and server logs</h2>
    <p>Our host may log standard request data (such as IP address, browser type, and pages requested) to keep the site running and secure.</p>
    <h2>Children</h2>
    <p>This site is not directed to children under 13, and we do not knowingly collect their information.</p>
    <h2>Contact</h2>
    <p>Questions or deletion requests: email <a href="mailto:{e(site['email'])}">{e(site['email'])}</a>, message us on <a href="{e(site['facebook'])}">Facebook</a> or <a href="{e(site['pinterest'])}">Pinterest</a>, or reply to any email we send you.</p>
    <h2>Changes</h2>
    <p>If this policy changes, we will update the date above.</p>
  </main>
""" + foot(site)


def render_simple(data, path, title, heading, body):
    """Small noindex utility page (form success, 404) with a way back into the picks."""
    site = data["site"]
    return head(site, f"{title} | {site['name']}", site["tagline"], path, f"{site['url']}/img/og.png",
                site["name"], OG_W, OG_H, noindex=True) + f"""  <div class="top"><a class="brand" href="/">{e(site['name'])}</a></div>
  <main id="main" class="prose">
    <h1>{e(heading)}</h1>
    <p>{body}</p>
    <p><a class="btn" href="/#top-picks">See this week's top picks</a></p>
  </main>
""" + foot(site)


# Category hub pages: one per top-level category, linking its buying guides and every pick in it.
HUBS = {
    "organization": {"path": "kitchen-organization/", "nav": "Kitchen Organization",
                     "title": "Kitchen Organization Ideas for Small Kitchens",
                     "intro": "Drawer, cabinet, pantry, sink and pot-and-lid storage for kitchens that are short on space. Start with the guide for the spot you're fixing: each one says what to measure first and which kind of organizer suits which situation."},
    "gadgets": {"path": "kitchen-gadgets/", "nav": "Kitchen Gadgets",
                "title": "Small Kitchen Gadgets Worth the Drawer Space",
                "intro": "Prep tools, scales, thermometers, frothers and kettles that make everyday cooking faster without taking over your drawers. Each guide explains what the gadget is good for and what to check before you buy."},
    "appliances": {"path": "small-kitchen-appliances/", "nav": "Small Kitchen Appliances",
                   "title": "Small Kitchen Appliances for Limited Counter Space",
                   "intro": "Immersion blenders, hand mixers, air fryers, slow cookers and other compact appliances for kitchens without much counter. The guides cover footprint, storage and cleanup, so you can tell what will actually fit."},
    "drinkware": {"path": "drinkware/", "nav": "Drinkware",
                  "title": "Insulated Tumblers and Water Bottles",
                  "intro": "Insulated tumblers and bottles for coffee on the go, all-day water and the car cup holder. The guide covers lids, sizes, cup-holder fit and cleaning."},
}


def page_top(site, crumb=""):
    return f"""  <div class="top"><a class="brand" href="/">{e(site['name'])}</a>{crumb}</div>
"""


def render_hub(data, key, products):
    site, tag, h = data["site"], data["site"]["associate_tag"], HUBS[key]
    items = [p for p in products if p["category"] == key]
    subs = [(k, s) for k, s in data["subcategories"].items() if s["category"] == key]
    tiles = "\n".join(
        f'        <a class="gcard" href="/{guide_path(k)}"><span class="thumb">{hero_picture(k, "/", "", wide=False)}</span><strong>{e(s["title"])}</strong>'
        f'<span>{e(s["description"])}</span><em>{len(guide_products(products, k))} picks · Read the guide →</em></a>'
        for k, s in subs)
    cards = "\n".join(card(p, tag, "/", eager=i < EAGER) for i, p in enumerate(items))
    url = f"{site['url']}/{h['path']}"
    graph = [{"@type": "CollectionPage", "name": h["title"], "url": url, "description": h["intro"],
              "isPartOf": {"@id": f"{site['url']}/#site"},
              "mainEntity": {"@type": "ItemList", "itemListElement": [
                  {"@type": "ListItem", "position": i + 1, "name": p["name"], "url": f"{site['url']}/{page_path(p)}"}
                  for i, p in enumerate(items)]}},
             {"@type": "BreadcrumbList", "itemListElement": [
                 {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{site['url']}/"},
                 {"@type": "ListItem", "position": 2, "name": h["nav"], "item": url}]}]
    return head(site, seo_title(h["title"], site), describe(h["intro"]), h["path"], f"{site['url']}/img/og.png",
                site["name"], OG_W, OG_H, ld({"@context": "https://schema.org", "@graph": graph}) + "\n") + page_top(
        site, f'<span class="crumbs"><a href="/">Home</a> › {e(h["nav"])}</span>') + f"""  <main id="main">
    <section class="guide">
      <h1>{e(h['title'])}</h1>
      <p class="intro">{e(h['intro'])}</p>
    </section>
    <section>
      <h2>Buying guides</h2>
      <div class="guides">
{tiles}
      </div>
    </section>
    <section>
      <h2>Every {e(h['nav'].lower())} pick</h2>
      <div class="grid">
{cards}
      </div>
    </section>
{signup()}  </main>
""" + foot(site)


def render_about(data):
    site = data["site"]
    hubs = ", ".join(h["nav"].lower() for h in HUBS.values())
    return head(site, f"About | {site['name']}", f"What {site['name']} covers, how products are chosen, and how the site is funded.",
                "about/", f"{site['url']}/img/og.png", site["name"], OG_W, OG_H) + page_top(site) + f"""  <main id="main" class="prose">
    <h1>About {e(site['name'])}</h1>
    <p>{e(site['name'])} is an independent site about making small, busy kitchens work better: {e(hubs)}. Every buying guide starts from a real problem, such as a cluttered drawer, a cramped sink cabinet or a counter with no room left, and points you to the kinds of products that solve it.</p>
    <h2>How we choose products</h2>
    <ul>
      <li>We look for products that fix a specific, everyday kitchen problem and suit kitchens with limited space.</li>
      <li>Before adding a product we compare its listing, its dimensions and specifications, and the recurring themes in customer reviews.</li>
      <li>We don't test products hands-on, and we say so. Our write-ups are based on published details and what buyers report.</li>
      <li>We don't post prices or star ratings, because they change constantly. Every product links to its current Amazon listing so you can check the latest details.</li>
      <li>Our guides tell you what to measure before you buy, because the most common problem with kitchen organizers is the wrong size.</li>
    </ul>
    <h2>How the site is funded</h2>
    <p>{e(site['name'])} is a participant in the Amazon Services LLC Associates Program. {DISCLOSURE} It doesn't change what you pay, and it keeps the site free and free of display ads.</p>
    <h2>Get in touch</h2>
    <p>Questions, corrections or product suggestions are welcome. Email <a href="mailto:{e(site['email'])}">{e(site['email'])}</a> or use the <a href="/contact/">contact form</a>.</p>
    <p><a class="btn" href="/#top-picks">See this week's top picks</a></p>
  </main>
""" + foot(site)


def render_contact(data):
    site = data["site"]
    return head(site, f"Contact | {site['name']}", f"Contact {site['name']} with questions, corrections or product suggestions.",
                "contact/", f"{site['url']}/img/og.png", site["name"], OG_W, OG_H) + page_top(site) + f"""  <main id="main" class="prose">
    <h1>Contact us</h1>
    <p>Questions, corrections, or a product you think belongs here? Send a message and we'll reply by email, usually within two business days. You can also email <a href="mailto:{e(site['email'])}">{e(site['email'])}</a> directly.</p>
    <p>Questions about an order, shipping or a return go to Amazon: purchases are made there, and we can't see or change orders.</p>
    <form class="contact" id="form" method="POST" action="/contact.php">
      <p class="hidden"><label>Leave this empty: <input name="website" tabindex="-1" autocomplete="off"></label></p>
      <label>Name <input name="name" required maxlength="100" autocomplete="name"></label>
      <label>Email <input type="email" name="email" required maxlength="254" autocomplete="email"></label>
      <label>Message <textarea name="message" required minlength="10" maxlength="5000" rows="7"></textarea></label>
      <p class="err" id="err" hidden>Your message wasn't sent. Check that every field is filled in, or email us directly.</p>
      <button class="btn" type="submit">Send message</button>
    </form>
    <script>if(new URLSearchParams(location.search).has("error"))document.getElementById("err").hidden=false;</script>
    <p><small>We use your details only to reply to you. See our <a href="/privacy/">privacy policy</a>.</small></p>
  </main>
""" + foot(site)


def render_thanksgiving_timeline(data):
    site = data["site"]
    desc = "Free printable Thanksgiving hosting timeline: a checklist countdown from three weeks out to dinner time, with turkey thawing and food-safety reminders."
    return head(site, seo_title("Free Thanksgiving Hosting Timeline (Printable)", site), desc, "thanksgiving-timeline/",
                f"{site['url']}/img/pins/gift-thanksgiving-kitchen-checklist-c.jpg", site["name"], 1000, 1500) + page_top(site) + f"""  <main id="main">
    <section class="guide">
      <h1>Free printable: Thanksgiving Hosting Timeline</h1>
      <p class="intro">Hosting Thanksgiving is mostly a timing problem. This one-page printable counts down from three weeks out to dinner time: when to order the turkey, when to start thawing it, what to make ahead, and the food-safety basics for the day itself.</p>
      <ul>
        <li>3-week, 2-week and 1-week to-do lists</li>
        <li>Turkey thawing times, so you know which day to start</li>
        <li>A Thanksgiving Day countdown and leftover tips</li>
      </ul>
    </section>
    <section class="signup" id="updates">
      <h2>Get the free timeline</h2>
      <p>Enter your email and the printable PDF opens right away. You'll also get one short email when we add new kitchen picks and holiday lists. No spam, unsubscribe anytime.</p>
      <form name="updates" method="POST" action="/subscribe.php">
        <p class="hidden"><label>Don't fill this out if you're human: <input name="bot-field" tabindex="-1" autocomplete="off"></label></p>
        <input type="hidden" name="src" value="thanksgiving">
        <input type="email" name="email" placeholder="you@example.com" required autocomplete="email" aria-label="Email address">
        <button class="btn" type="submit">Send me the timeline</button>
      </form>
      <small>We only use your email to send new kitchen picks, and never sell or share it. See our <a href="/privacy/">privacy policy</a>.</small>
    </section>
    <section>
      <h2>Getting the kitchen ready?</h2>
      <p>See the <a href="/{gift_path('thanksgiving-kitchen-checklist')}">Thanksgiving Kitchen Checklist for Hosts</a>: the thermometer, fat separator and slow cookers that make the day easier.</p>
    </section>
  </main>
""" + foot(site)


def render_newsletter(data, products):
    site, tag = data["site"], data["site"]["associate_tag"]
    latest = "\n".join(card(p, tag, "/") for p in products[:3])
    desc = "Get the free Small-Kitchen Measuring Checklist and one short email when we add new kitchen organization, gadget and appliance picks."
    return head(site, seo_title("Free Small-Kitchen Measuring Checklist", site), desc, "newsletter/", f"{site['url']}/img/og.png",
                site["name"], OG_W, OG_H) + page_top(site) + f"""  <main id="main">
    <section class="guide">
      <h1>Measure once, buy the right size</h1>
      <p class="intro">The most common reason a drawer organizer, dish rack or under-sink shelf goes back is that it doesn't fit. Our free one-page checklist lists every measurement our buying guides are built around: drawers, cabinets, the space around the drain pipe, the counter beside the sink and more.</p>
    </section>
{signup()}    <section>
      <h2>The latest picks</h2>
      <div class="grid">
{latest}
      </div>
    </section>
  </main>
""" + foot(site)


FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#c8643b"/><text x="32" y="44" font-family="Georgia,serif" font-size="38" font-weight="700" fill="#fff" text-anchor="middle">K</text></svg>
"""


# Hostinger serves the site with Apache/LiteSpeed, so .htaccess replaces Netlify's _headers.
HTACCESS = """# Generated by build.py — edit there.
Options -Indexes
ErrorDocument 404 /404.html
RewriteEngine On
# Never serve the deploy checkout's git data or the build sources.
RewriteRule (^|/)\\.(git|data)(/|$) - [R=404,L]
# Force HTTPS and the bare domain.
RewriteCond %{HTTPS} off [OR]
RewriteCond %{HTTP_HOST} ^www\\. [NC]
RewriteRule ^ https://kitchenfindsfavorites.com%{REQUEST_URI} [R=301,L]
<IfModule mod_headers.c>
  # Posting routines load the graphics cross-origin (canvas -> file upload).
  <FilesMatch "\\.(png|webp)$">
    Header set Access-Control-Allow-Origin "*"
  </FilesMatch>
  Header always set X-Content-Type-Options "nosniff"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
</IfModule>
<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresByType image/png "access plus 30 days"
  ExpiresByType image/webp "access plus 30 days"
  ExpiresByType image/svg+xml "access plus 30 days"
  ExpiresByType text/html "access plus 10 minutes"
</IfModule>
"""

# Email sign-up handler. Addresses go to a CSV one level ABOVE the web root
# (outside public_html), so they can never be downloaded from the site.
SUBSCRIBE_PHP = r"""<?php
// Generated by build.py — edit there.
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { header('Location: /#updates', true, 303); exit; }
if (!empty($_POST['bot-field'])) { header('Location: /thanks/', true, 303); exit; }  // honeypot
$email = trim((string)($_POST['email'] ?? ''));
if (strlen($email) > 254 || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
  header('Location: /#updates', true, 303); exit;
}
// Which sign-up form it came from; each freebie has its own thank-you page.
$src = ((string)($_POST['src'] ?? '')) === 'thanksgiving' ? 'thanksgiving' : 'site';
$file = dirname(__DIR__) . '/kff-subscribers.csv';
$fh = @fopen($file, 'a');
if ($fh) {
  if (flock($fh, LOCK_EX)) {
    fputcsv($fh, [gmdate('c'), strtolower($email), $src]);
    flock($fh, LOCK_UN);
  }
  fclose($fh);
}
header('Location: ' . ($src === 'thanksgiving' ? '/thanks/thanksgiving/' : '/thanks/'), true, 303);
"""


CONTACT_PHP = r"""<?php
// Generated by build.py — edit there. Emails contact-form messages to the site mailbox and keeps a
// backup copy next to public_html (not web-reachable).
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { header('Location: /contact/', true, 303); exit; }
if (trim((string)($_POST['website'] ?? '')) !== '') { header('Location: /contact/sent/', true, 303); exit; }  // honeypot
$to = 'help@kitchenfindsfavorites.com';
$name = substr(trim((string)preg_replace('/[\r\n\t]+/', ' ', (string)($_POST['name'] ?? ''))), 0, 100);  // no header injection
$email = strtolower(trim((string)($_POST['email'] ?? '')));
$message = trim(str_replace("\r\n", "\n", (string)($_POST['message'] ?? '')));
if ($name === '' || strlen($email) > 254 || !filter_var($email, FILTER_VALIDATE_EMAIL)
    || strlen($message) < 10 || strlen($message) > 5000) {
  header('Location: /contact/?error=1#form', true, 303); exit;
}
$safe = function ($v) { return preg_match('/^[=+\-@\t\r]/', $v) ? "'" . $v : $v; };  // no spreadsheet formulas
$fh = @fopen(dirname(__DIR__) . '/kff-contact.csv', 'a');
if ($fh) {
  if (flock($fh, LOCK_EX)) { fputcsv($fh, [gmdate('c'), $safe($name), $safe($email), $safe($message)]); flock($fh, LOCK_UN); }
  fclose($fh);
}
$subject = '=?UTF-8?B?' . base64_encode('Website message from ' . $name) . '?=';
$body = "Name: $name\nEmail: $email\n\n$message\n\n-- Sent from the contact form on kitchenfindsfavorites.com\n";

// Preferred: sign in to the mailbox over SMTP so Hostinger signs the message (DKIM) and it reaches the
// Inbox. The password lives in kff-smtp.php next to public_html (never in the repo or the web root):
//   <?php return ['user' => 'help@kitchenfindsfavorites.com', 'pass' => '...'];
function kff_smtp_send($cfg, $to, $replyTo, $subject, $body) {
  $fp = @stream_socket_client('ssl://smtp.hostinger.com:465', $errno, $errstr, 15);
  if (!$fp) return false;
  stream_set_timeout($fp, 15);
  $read = function () use ($fp) { $out = ''; while (($line = fgets($fp, 515)) !== false) { $out .= $line; if (strlen($line) < 4 || $line[3] === ' ') break; } return $out; };
  $cmd = function ($c, $ok) use ($fp, $read) { fwrite($fp, $c . "\r\n"); return strpos($read(), (string)$ok) === 0; };
  $user = $cfg['user'];
  $ok = strpos($read(), '220') === 0
     && $cmd('EHLO kitchenfindsfavorites.com', 250)
     && $cmd('AUTH LOGIN', 334)
     && $cmd(base64_encode($user), 334)
     && $cmd(base64_encode($cfg['pass']), 235)
     && $cmd("MAIL FROM:<$user>", 250)
     && $cmd("RCPT TO:<$to>", 250)
     && $cmd('DATA', 354);
  if ($ok) {
    $msg = "Date: " . date('r') . "\r\n"
         . "From: Kitchen Finds & Favorites website <$user>\r\n"
         . "To: <$to>\r\nReply-To: <$replyTo>\r\nSubject: $subject\r\n"
         . "Message-ID: <" . bin2hex(random_bytes(12)) . "@kitchenfindsfavorites.com>\r\n"
         . "MIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n"
         . chunk_split(base64_encode($body)) . ".";
    $ok = $cmd($msg, 250);
  }
  @fwrite($fp, "QUIT\r\n");
  fclose($fp);
  return $ok;
}
$cfgFile = dirname(__DIR__) . '/kff-smtp.php';
$cfg = is_file($cfgFile) ? @include $cfgFile : null;
$sent = false;
if (is_array($cfg) && !empty($cfg['user']) && !empty($cfg['pass']) && strpos($cfg['pass'], 'PASTE') === false) {
  $sent = kff_smtp_send($cfg, $to, $email, $subject, $body);
}
if (!$sent) {
  // Fallback: the server's own mail() (arrives, but Hostinger files it as Junk).
  $host = gethostname();
  $from = (is_string($host) && strpos($host, '.') !== false) ? 'noreply@' . $host : $to;
  $headers = "From: Kitchen Finds & Favorites website <$from>\r\nReply-To: $email\r\nMIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8";
  $sent = @mail($to, $subject, $body, $headers);
}
header('Location: ' . ($sent ? '/contact/sent/' : '/contact/?error=1#form'), true, 303);
"""


# Amazon click logger (see track_js). Writes to .data/clicks.csv, which .htaccess blocks from the web.
CLICK_PHP = r"""<?php
// Generated by build.py — edit there. Logs Amazon link clicks: no IP address, cookies or personal data.
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(204); exit; }
$p = substr((string)($_POST['p'] ?? ''), 0, 200);
$a = (string)($_POST['a'] ?? '');
$c = strtolower(substr((string)($_POST['c'] ?? ''), 0, 20));
$l = substr((string)($_POST['l'] ?? ''), 0, 20);
$k = substr((string)($_POST['k'] ?? ''), 0, 60);
if (!preg_match('~^/[A-Za-z0-9/_.-]*$~', $p) || !preg_match('/^B0[0-9A-Z]{8}$/', $a)) { http_response_code(204); exit; }
if (!preg_match('/^[a-z0-9_-]{1,20}$/', $c)) $c = 'other';
if (!preg_match('/^[a-z-]{1,20}$/', $l)) $l = 'other';
if (!preg_match('/^[A-Za-z0-9_-]{0,60}$/', $k)) $k = '';
$dir = __DIR__ . '/.data';
if (!is_dir($dir)) @mkdir($dir, 0750);
$fh = @fopen($dir . '/clicks.csv', 'a');
if ($fh) {
  if (flock($fh, LOCK_EX)) { fputcsv($fh, [gmdate('c'), $p, $a, $c, $l, $k]); flock($fh, LOCK_UN); }
  fclose($fh);
}
http_response_code(204);
"""


def main():
    data, errors = load()
    if errors:
        print("products.json has problems:", *errors, sep="\n  - ", file=sys.stderr)
        sys.exit(1)
    if "--check" in sys.argv:
        print(f"OK: {len(data['products'])} products")
        return
    OUT.mkdir(exist_ok=True)
    global AMAZON_IMAGES
    amz = ROOT / "amazon_images.json"
    if amz.exists():
        AMAZON_IMAGES = {k: v for k, v in json.loads(amz.read_text(encoding="utf-8")).items()
                         if str(v.get("url", "")).startswith("https://m.media-amazon.com/")}
        print(f"Using official Amazon photos for {len(AMAZON_IMAGES)} products")
    import graphics  # needs Pillow; only required for a full build
    global PHOTO_CREDITS
    PHOTO_CREDITS = {k: v for k, v in graphics.photo_credits().items() if graphics.product_photo(k)}
    if PHOTO_CREDITS:
        print(f"Using similar-item stock photos for {len(PHOTO_CREDITS)} products")
    graphics.render_all(data, OUT, force="--force-graphics" in sys.argv)
    render_hero_images(data)
    url, tag = data["site"]["url"], data["site"]["associate_tag"]
    products = sorted(data["products"], key=lambda p: p["added"], reverse=True)
    (OUT / "index.html").write_text(render_home(data, products), encoding="utf-8")
    # Rebuild product pages from scratch so removed products don't leave stale pages.
    shutil.rmtree(OUT / "picks", ignore_errors=True)
    for p in products:
        d = OUT / page_path(p)
        d.mkdir(parents=True)
        (d / "index.html").write_text(render_pick(data, p, products), encoding="utf-8")
    shutil.rmtree(OUT / "guides", ignore_errors=True)
    guide_urls = []
    for key in data["subcategories"]:
        items = guide_products(data["products"], key)
        d = OUT / guide_path(key)
        d.mkdir(parents=True)
        (d / "index.html").write_text(render_guide(data, key, items), encoding="utf-8")
        guide_urls.append((f"{url}/{guide_path(key)}", max(p["added"] for p in items)))
    shutil.rmtree(OUT / "comparisons", ignore_errors=True)
    comparison_urls = []
    for key, c in data.get("comparisons", {}).items():
        d = OUT / comparison_path(key)
        d.mkdir(parents=True)
        (d / "index.html").write_text(render_comparison(data, key), encoding="utf-8")
        comparison_urls.append((f"{url}/{comparison_path(key)}", c["added"]))
    shutil.rmtree(OUT / "gifts", ignore_errors=True)
    gift_urls = []
    for key in data.get("gift_guides", {}):
        items = gift_products(data, key)
        d = OUT / gift_path(key)
        d.mkdir(parents=True)
        (d / "index.html").write_text(render_guide(data, key, items), encoding="utf-8")
        gift_urls.append((f"{url}/{gift_path(key)}", max(p["added"] for p in items)))
    (OUT / ".htaccess").write_text(HTACCESS, encoding="utf-8")
    (OUT / "click.php").write_text(CLICK_PHP, encoding="utf-8")
    (OUT / ".data").mkdir(exist_ok=True)
    (OUT / ".data" / ".htaccess").write_text("Require all denied\n", encoding="utf-8")
    lm = data["site"].get("lead_magnet")
    if lm:
        src = ROOT / "assets" / lm["file"]
        dst = OUT / lm["file"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    shutil.copyfile(ROOT / "assets" / "printables" / "thanksgiving-hosting-timeline.pdf",
                    OUT / "printables" / "thanksgiving-hosting-timeline.pdf")
    import pins  # Pinterest queue: several pins per page (see pins.py)
    pin_list = pins.build(data, OUT, url, force="--force-graphics" in sys.argv)
    (OUT / "pins.json").write_text(json.dumps(pin_list, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "subscribe.php").write_text(SUBSCRIBE_PHP, encoding="utf-8")
    (OUT / "contact.php").write_text(CONTACT_PHP, encoding="utf-8")
    extra_urls = []
    for key, h in HUBS.items():
        d = OUT / h["path"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(render_hub(data, key, products), encoding="utf-8")
        extra_urls.append((f"{url}/{h['path']}", max(p["added"] for p in products if p["category"] == key)))
    for path, html in (("about/", render_about(data)), ("contact/", render_contact(data)),
                       ("newsletter/", render_newsletter(data, products))):
        (OUT / path).mkdir(exist_ok=True)
        (OUT / path / "index.html").write_text(html, encoding="utf-8")
        extra_urls.append((f"{url}/{path}", None))
    (OUT / "contact" / "sent").mkdir(exist_ok=True)
    (OUT / "contact" / "sent" / "index.html").write_text(render_simple(
        data, "contact/sent/", "Message sent", "Thanks, your message is on its way",
        "We usually reply within two business days. Questions about an order go to Amazon, since purchases are made there."),
        encoding="utf-8")
    (OUT / "privacy").mkdir(exist_ok=True)
    (OUT / "privacy" / "index.html").write_text(render_privacy(data), encoding="utf-8")
    (OUT / "thanks").mkdir(exist_ok=True)
    (OUT / "thanks" / "index.html").write_text(render_simple(
        data, "thanks/", "Thanks for signing up", "You're on the list",
        "Thanks for signing up. Your free printable is ready: <a class=\"btn\" href=\"/printables/small-kitchen-measuring-checklist.pdf\">Download the Small-Kitchen Measuring Checklist (PDF)</a></p><p>We'll send one short email whenever we add new kitchen picks, and every email has an unsubscribe link."),
        encoding="utf-8")
    (OUT / "thanks" / "thanksgiving").mkdir(exist_ok=True)
    (OUT / "thanks" / "thanksgiving" / "index.html").write_text(render_simple(
        data, "thanks/thanksgiving/", "Your Thanksgiving timeline", "Your Thanksgiving timeline is ready",
        "Thanks for signing up. <a class=\"btn\" href=\"/printables/thanksgiving-hosting-timeline.pdf\">Download the Thanksgiving Hosting Timeline (PDF)</a></p>"
        f"<p>Getting the kitchen ready? See the <a href=\"/{gift_path('thanksgiving-kitchen-checklist')}\">Thanksgiving Kitchen Checklist for Hosts</a>.</p>"
        f"<p>For more holiday kitchen ideas, follow us on <a href=\"{e(data['site']['facebook'])}\" rel=\"noopener\">Facebook</a>. We'll send one short email whenever we add new picks, and every email has an unsubscribe link."),
        encoding="utf-8")
    (OUT / "thanksgiving-timeline").mkdir(exist_ok=True)
    (OUT / "thanksgiving-timeline" / "index.html").write_text(render_thanksgiving_timeline(data), encoding="utf-8")
    extra_urls.append((f"{url}/thanksgiving-timeline/", None))
    (OUT / "404.html").write_text(render_simple(
        data, "404.html", "Page not found", "That page isn't here",
        "The pick you're looking for may have moved or been removed. Everything we currently recommend is on the home page."),
        encoding="utf-8")
    (OUT / "favicon.svg").write_text(FAVICON, encoding="utf-8")
    # Let the posting routines load the graphics cross-origin (canvas -> file upload on Pinterest/Facebook).
    (OUT / "_headers").write_text("/img/*\n  Access-Control-Allow-Origin: *\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {url}/sitemap.xml\n", encoding="utf-8")
    (OUT / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY, encoding="utf-8")
    # Machine-readable feed: the posting routines read this as their queue.
    feed = [dict(p, page_url=f"{url}/{page_path(p)}", pin_image=f"{url}/img/{p['asin']}.png",
                 amazon_url=amazon_url(p["asin"], tag))
            for p in sorted(data["products"], key=lambda p: p["added"])]
    (OUT / "products.json").write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    newest = products[0]["added"]
    urls = [(f"{url}/", newest), (f"{url}/privacy/", PRIVACY_UPDATED)] + extra_urls + gift_urls + guide_urls + comparison_urls + [(f"{url}/{page_path(p)}", p["added"]) for p in products]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{e(u)}</loc>{f'<lastmod>{m}</lastmod>' if m else ''}</url>\n" for u, m in urls)
        + "</urlset>\n", encoding="utf-8")
    print(f"Built public/ with {len(products)} products")


if __name__ == "__main__":
    main()
