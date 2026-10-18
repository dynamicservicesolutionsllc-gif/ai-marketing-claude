#!/usr/bin/env python3
"""Build the Kitchen Finds & Favorites site from products.json.

Usage: python3 build.py          # validate products.json and write public/
       python3 build.py --check  # validate only, exit non-zero on problems

Writes the landing page, one page per product (public/picks/<slug>/), a privacy
page, sitemap, robots, and the products.json feed the posting routines read.

Product images are original graphics rendered by graphics.py (needs Pillow) into
public/img/ — never Amazon-hosted photos, which the Associates policies only
license through Amazon's own tools/API.
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
PRIVACY_UPDATED = "2026-10-17"  # bump when the privacy text changes
GA_ID = "G-8KQ2TM4X7Z"  # Google Analytics 4 measurement ID; the privacy page discloses it
e = html.escape
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
        if len(s.get("description", "")) > 160:
            errors.append(f"{where}: description over 160 characters")
        if len(s.get("criteria", [])) < 2 or len(s.get("guide", [])) < 2:
            errors.append(f"{where}: needs at least 2 'criteria' and 2 'guide' entries")
        copy = json.dumps(s, ensure_ascii=False)
        if TESTING_CLAIM.search(copy):
            errors.append(f"{where}: copy implies hands-on testing/personal use")
        if re.search(r"\$\s?\d|\b\d(\.\d)? ?stars?\b|\bcheapest\b|\blowest price\b", copy, re.I):
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
    return data, errors


def amazon_url(asin, tag):
    return f"https://www.amazon.com/dp/{asin}?tag={tag}"


def page_path(p):
    return f"picks/{slug(p['name'])}/"


# Official Amazon photos from the Creators API (written by fetch_amazon_images.py, only when API keys are set).
# Hotlinked from Amazon's servers as the API license requires; never committed, refreshed on every deploy.
AMAZON_IMAGES = {}


def picture(p, base, eager=False):
    """Card image: the official Amazon photo when the API supplied one, else our WebP/PNG graphic card."""
    load = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    a = AMAZON_IMAGES.get(p["asin"])
    if a:
        return (f'<img class="amz" src="{e(a["url"])}" alt="{e(p["name"])}" {load} '
                f'width="{a.get("width") or 500}" height="{a.get("height") or 500}" referrerpolicy="no-referrer-when-downgrade">')
    return (f'<picture><source srcset="{base}img/{e(p["asin"])}-sq.webp" type="image/webp">'
            f'<img src="{base}img/{e(p["asin"])}-sq.png" alt="{e(p["name"])}" {load} width="800" height="800"></picture>')


def buy(p, tag):
    return (f'<a class="btn" href="{e(amazon_url(p["asin"], tag))}" rel="sponsored nofollow noopener" target="_blank">Check price on Amazon →</a>\n'
            f'          <small class="paid">{PAID_NOTE}</small>')


def card(p, tag, base="", eager=False):
    return f"""      <article class="card" id="{e(p['asin'])}">
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
  .award { color:var(--acc); font-weight:700; font-size:14px; text-transform:uppercase; letter-spacing:.04em; }
  .more { color:var(--acc); font-size:14px; }
  .prose.wide { max-width:760px; padding:24px 0; }
  .prose h3 { font-size:17px; margin:16px 0 4px; }
  .links { list-style:none; display:flex; flex-wrap:wrap; gap:10px 20px; }
  .links a { color:var(--acc); }
  .guides { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:14px; }
  .gcard { background:var(--card); border:1px solid var(--bd); border-radius:12px; padding:16px; text-decoration:none; color:var(--ink); display:flex; flex-direction:column; gap:6px; }
  .gcard:hover { border-color:var(--acc); }
  .gcard strong { font-size:16px; line-height:1.3; }
  .gcard span { color:var(--mut); font-size:14px; }
  .gcard em { color:var(--acc); font-style:normal; font-size:14px; font-weight:600; }
  footer { border-top:1px solid var(--bd); padding:24px 0 40px; color:var(--mut); font-size:13px; }
  footer a { color:var(--acc); }
"""


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
{extra}<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="disclosure">{DISCLOSURE} <a href="/privacy/">Learn more</a></div>
<div class="wrap">
"""


def signup():
    return """    <section class="signup" id="updates">
      <h2>Get the next 5 kitchen finds before anyone else</h2>
      <p>One short email whenever we add new picks. No spam, unsubscribe anytime.</p>
      <form name="updates" method="POST" action="/subscribe.php">
        <p class="hidden"><label>Don't fill this out if you're human: <input name="bot-field" tabindex="-1" autocomplete="off"></label></p>
        <input type="email" name="email" placeholder="you@example.com" required autocomplete="email" aria-label="Email address">
        <button class="btn" type="submit">Get Updates</button>
      </form>
      <small>We only use your email to send new kitchen picks, and never sell or share it. See our <a href="/privacy/">privacy policy</a>.</small>
    </section>
"""


def foot(site):
    return f"""  <footer>
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
    nav = '<a href="#guides">Buying Guides</a> ' + " ".join(
        f'<a href="#{e(k)}">{e(v)}</a>' for k, v in data["categories"].items()
        if any(p["category"] == k and p["asin"] not in top_asins for p in products))
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
    title = f"Small Kitchen Organization & Gadget Picks | {site['name']}"
    return head(site, title, site["tagline"], "", f"{site['url']}/img/og.png",
                f"{site['name']} — {site['tagline']}", OG_W, OG_H, site_ld(site, products) + "\n") + f"""  <header>
    <h1>{e(site['name'])}<span class="sub">Organization, gadgets &amp; small appliances for small kitchens</span></h1>
    <p>{e(site['tagline'])}</p>
    <nav>{nav}</nav>
  </header>
  <main id="main">
    <section id="top-picks">
      <h2>This Week's Top Picks</h2>
      <div class="grid">
{top_cards}
      </div>
    </section>
{guides}
{chr(10).join(sections)}
{signup()}  </main>
""" + foot(site)


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
    if more:
        cards = "\n".join(card(q, tag, base) for q in more)
        more_html = (f'    <section>\n      <h2>More picks like this</h2>\n      <div class="grid">\n{cards}\n      </div>\n'
                     f'      <p style="margin-top:16px"><a class="more" href="{base}{guide_path(p["subcategory"])}">See the full guide: {e(sub["title"])} →</a></p>\n    </section>\n')
    crumbs = ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": site["name"], "item": f"{site['url']}/"},
        {"@type": "ListItem", "position": 2, "name": sub["title"], "item": f"{site['url']}/{guide_path(p['subcategory'])}"},
        {"@type": "ListItem", "position": 3, "name": p["name"], "item": f"{site['url']}/{page_path(p)}"}]})
    points = "".join(f"<li>{e(pt)}</li>" for pt in p["graphic"]["points"])
    title = f"{p['name']} | {site['name']}"
    return head(site, title, describe(p["blurb"]), page_path(p), f"{site['url']}/img/{p['asin']}.png",
                p["graphic"]["headline"], 1000, 1500, crumbs + "\n") + f"""  <div class="top">
    <a class="brand" href="{base}">{e(site['name'])}</a>
    <span class="crumbs"><a href="{base}">Home</a> › <a href="{base}{guide_path(p['subcategory'])}">{e(sub['title'])}</a></span>
  </div>
  <main id="main">
    <p class="callout">{DISCLOSURE} The "Check price on Amazon" button below is an affiliate link.</p>
    <article class="pick" id="{e(p['asin'])}">
      <a class="img" href="{e(amazon_url(p['asin'], tag))}" rel="sponsored nofollow noopener" target="_blank">
        {picture(p, base, eager=True)}
      </a>
      <div class="info">
        <h1>{e(p['name'])}</h1>
        <p class="lede">{e(p['blurb'])}</p>
        <ul>{points}</ul>
        <div class="buy">
          {buy(p, tag)}
        </div>
      </div>
    </article>
{more_html}{signup()}  </main>
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
    for key in data["subcategories"]:
        src = src_dir / f"{key}.jpg"
        im = Image.open(src).convert("RGB")
        for suffix, width in (("", 1600), ("-800", 800)):
            size = (width, round(im.height * width / im.width))
            r = im.resize(size, Image.LANCZOS) if im.width != width else im
            r.save(out / f"{key}{suffix}.jpg", "JPEG", quality=80, optimize=True, progressive=True)
            r.save(out / f"{key}{suffix}.webp", "WEBP", quality=78, method=6)


def guide_path(key):
    return f"guides/{key}/"


def guide_products(products, key):
    """A guide's picks, in products.json order (curated order, not newest-first)."""
    return [p for p in products if p["subcategory"] == key]


def render_guide(data, key, items):
    site, tag = data["site"], data["site"]["associate_tag"]
    s = data["subcategories"][key]
    cat_label = data["categories"][s["category"]]
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
        sections.append(f"""    <article class="pick roundup" id="{e(p['asin'])}">
      <a class="img" href="{base}{page_path(p)}">
        {picture(p, base, eager=i < 1)}
      </a>
      <div class="info">
        <p class="award">{i + 1}. {e(p['award'])}</p>
        <h2><a href="{base}{page_path(p)}">{e(p['name'])}</a></h2>
        <p class="lede">{e(p['blurb'])}</p>
        <ul>{points}</ul>
        <div class="buy">
          {buy(p, tag)}
          <a class="more" href="{base}{page_path(p)}">Full details on this pick →</a>
        </div>
      </div>
    </article>""")
    quick_answer = f'\n      <p class="callout"><strong>Quick answer:</strong> {e(s["quick_answer"])}</p>' if s.get("quick_answer") else ""
    measure = ""
    if s.get("measure"):
        measure = ("    <section class=\"prose wide\">\n      <h2>Before you buy, measure these</h2>\n      <ol>"
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
    criteria = "".join(f"<li>{e(c)}</li>" for c in s["criteria"])
    guide = "".join(f"<h3>{e(h)}</h3><p>{e(t)}</p>" for h, t in s["guide"])
    faq = s.get("faq", [])
    faq_html = ""
    if faq:
        faq_html = "    <section class=\"prose wide\">\n      <h2>Frequently asked questions</h2>\n" + "".join(
            f"      <h3>{e(q)}</h3>\n      <p>{e(a)}</p>\n" for q, a in faq) + "    </section>\n"
    others = [(k, v) for k, v in data["subcategories"].items() if k != key and v["category"] == s["category"]]
    related = ""
    if others:
        related = "    <section>\n      <h2>Related buying guides</h2>\n      <ul class=\"links\">" + "".join(
            f'<li><a href="{base}{guide_path(k)}">{e(v["title"])}</a></li>' for k, v in others) + "</ul>\n    </section>\n"
    url = f"{site['url']}/{guide_path(key)}"
    graph = [
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": site["name"], "item": f"{site['url']}/"},
            {"@type": "ListItem", "position": 2, "name": cat_label, "item": f"{site['url']}/#{s['category']}"},
            {"@type": "ListItem", "position": 3, "name": s["title"], "item": url}]},
        {"@type": "Article", "headline": s["title"], "description": s["description"], "dateModified": updated,
         "url": url, "publisher": {"@id": f"{site['url']}/#org"}, "image": f"{site['url']}/img/guides/{key}.jpg"},
        {"@type": "ItemList", "name": s["title"], "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": p["name"], "url": f"{site['url']}/{page_path(p)}"}
            for i, p in enumerate(items)]}]
    if faq:
        graph.append({"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})
    title = f"{s['title']} ({year}) | {site['name']}"
    return head(site, title, s["description"], guide_path(key), f"{site['url']}/img/guides/{key}.jpg",
                s["hero"]["alt"], 1600, 640, ld({"@context": "https://schema.org", "@graph": graph}) + "\n") + f"""  <div class="top">
    <a class="brand" href="{base}">{e(site['name'])}</a>
    <span class="crumbs"><a href="{base}">Home</a> › <a href="{base}#{e(s['category'])}">{e(cat_label)}</a></span>
  </div>
  <main id="main">
    <figure class="hero">{hero_picture(key, base, s['hero']['alt'], eager=True)}<figcaption>Photo: {e(s['hero']['credit'])}</figcaption></figure>
    <header class="guide">
      <h1>{e(s['title'])} ({year})</h1>
      <p class="updated">Updated {month} · {len(items)} picks</p>
      <p class="callout"><strong>Affiliate disclosure:</strong> {e(site['name'])} is reader-supported. Buttons marked "Check price on Amazon" are affiliate links. {DISCLOSURE} It costs you nothing extra, and picks are chosen from product research, not commission rates.</p>
      <p class="intro">{e(s['intro'])}</p>{quick_answer}
    </header>
    <section>
      <h2>Quick picks</h2>
      <table class="quick">
        <thead><tr><th>Best for</th><th>Pick</th><th><span class="hidden">Link</span></th></tr></thead>
        <tbody>
{rows}
        </tbody>
      </table>
    </section>
{measure}{types}    <section class="prose wide">
      <h2>How we chose</h2>
      <p>Each pick was selected by comparing manufacturer specifications and recurring themes in owner feedback against these criteria:</p>
      <ul>{criteria}</ul>
      <p>Product details change — confirm sizes and current price on the Amazon listing before buying.</p>
    </section>
{chr(10).join(sections)}
    <section class="prose wide">
      <h2>Buying guide: what to look for</h2>
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
    <h2>Email sign-up</h2>
    <p>If you join our email list, we collect only the email address you enter. It is stored on our web host, Hostinger (see <a href="https://www.hostinger.com/legal/privacy-policy" rel="nofollow noopener">Hostinger's privacy policy</a>). We use your address only to send new kitchen picks. We never sell, rent, or share it. Every email includes an unsubscribe link, and you can ask us to delete your address at any time.</p>
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


FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#c8643b"/><text x="32" y="44" font-family="Georgia,serif" font-size="38" font-weight="700" fill="#fff" text-anchor="middle">K</text></svg>
"""


# Hostinger serves the site with Apache/LiteSpeed, so .htaccess replaces Netlify's _headers.
HTACCESS = """# Generated by build.py — edit there.
Options -Indexes
ErrorDocument 404 /404.html
RewriteEngine On
# Never serve the deploy checkout's git data or the build sources.
RewriteRule (^|/)\\.git(/|$) - [R=404,L]
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
$file = dirname(__DIR__) . '/kff-subscribers.csv';
$fh = @fopen($file, 'a');
if ($fh) {
  if (flock($fh, LOCK_EX)) {
    fputcsv($fh, [gmdate('c'), strtolower($email)]);
    flock($fh, LOCK_UN);
  }
  fclose($fh);
}
header('Location: /thanks/', true, 303);
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
    (OUT / ".htaccess").write_text(HTACCESS, encoding="utf-8")
    (OUT / "subscribe.php").write_text(SUBSCRIBE_PHP, encoding="utf-8")
    (OUT / "privacy").mkdir(exist_ok=True)
    (OUT / "privacy" / "index.html").write_text(render_privacy(data), encoding="utf-8")
    (OUT / "thanks").mkdir(exist_ok=True)
    (OUT / "thanks" / "index.html").write_text(render_simple(
        data, "thanks/", "Thanks for signing up", "You're on the list",
        "Thanks for signing up. We'll send one short email whenever we add new kitchen picks, and every email has an unsubscribe link."),
        encoding="utf-8")
    (OUT / "404.html").write_text(render_simple(
        data, "404.html", "Page not found", "That page isn't here",
        "The pick you're looking for may have moved or been removed. Everything we currently recommend is on the home page."),
        encoding="utf-8")
    (OUT / "favicon.svg").write_text(FAVICON, encoding="utf-8")
    # Let the posting routines load the graphics cross-origin (canvas -> file upload on Pinterest/Facebook).
    (OUT / "_headers").write_text("/img/*\n  Access-Control-Allow-Origin: *\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {url}/sitemap.xml\n", encoding="utf-8")
    # Machine-readable feed: the posting routines read this as their queue.
    feed = [dict(p, page_url=f"{url}/{page_path(p)}", pin_image=f"{url}/img/{p['asin']}.png",
                 amazon_url=amazon_url(p["asin"], tag))
            for p in sorted(data["products"], key=lambda p: p["added"])]
    (OUT / "products.json").write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    newest = products[0]["added"]
    urls = [(f"{url}/", newest), (f"{url}/privacy/", PRIVACY_UPDATED)] + guide_urls + [(f"{url}/{page_path(p)}", p["added"]) for p in products]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{e(u)}</loc>{f'<lastmod>{m}</lastmod>' if m else ''}</url>\n" for u, m in urls)
        + "</urlset>\n", encoding="utf-8")
    print(f"Built public/ with {len(products)} products")


if __name__ == "__main__":
    main()
