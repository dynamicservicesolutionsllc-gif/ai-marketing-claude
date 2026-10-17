#!/usr/bin/env python3
"""Build the Kitchen Finds & Favorites site from products.json.

Usage: python3 build.py          # validate products.json and write public/
       python3 build.py --check  # validate only, exit non-zero on problems

Writes the home page, one page per product (public/picks/<slug>/), category
landing pages, seasonal gift guides, About / Contact / Newsletter / Privacy pages,
sitemap, robots, the products.json feed the posting routines read, and the
Hostinger server files (.htaccess + the PHP form handlers in php/).

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
RESERVED = {"picks", "img", "privacy", "thanks", "about", "contact", "newsletter", "gift-guides", "_private", "kff-data"}
e = html.escape


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
        if re.search(r"\b(tested|we tried|i tried|i use|we use)\b", text, re.I):
            errors.append(f"{where}: copy implies hands-on testing/personal use — describe the product, not our use of it")
    page_slugs = set()
    for key in cats:
        s = cat_info(data, key)["slug"]
        if s in RESERVED or s in page_slugs:
            errors.append(f"category '{key}': page slug '{s}' is reserved or already used")
        page_slugs.add(s)
    for i, g in enumerate(data.get("guides", [])):
        where = f"guides[{i}] ({g.get('slug', '?')})"
        for field in ("slug", "title", "description", "intro", "updated"):
            if not str(g.get(field, "")).strip():
                errors.append(f"{where}: missing '{field}'")
        if g.get("slug") in page_slugs:
            errors.append(f"{where}: duplicate guide slug")
        page_slugs.add(g.get("slug"))
        if g.get("cover") and g["cover"] not in g.get("asins", []):
            errors.append(f"{where}: 'cover' must be one of the guide's ASINs")
        missing = [a for a in g.get("asins", []) if a not in seen]
        if missing:
            errors.append(f"{where}: ASINs not in products: {', '.join(missing)} — remove them from the guide")
        if len(g.get("asins", [])) - len(missing) < 3:
            errors.append(f"{where}: a guide needs at least 3 live products")
        text = " ".join(str(g.get(f, "")) for f in ("title", "description", "intro"))
        if re.search(r"\$\d|\bunder \$|\bprice[sd]?\b|\bstars?\b|best[- ]seller", text, re.I):
            errors.append(f"{where}: no prices, star ratings or best-seller claims in guide copy")
        if re.search(r"\b(tested|we tried|i tried|i use|we use)\b", text, re.I):
            errors.append(f"{where}: copy implies hands-on testing/personal use")
    return data, errors


def cat_info(data, key):
    """Landing-page settings for a category; categories added later fall back to sensible defaults."""
    info = (data.get("category_pages") or {}).get(key, {})
    label = data["categories"][key]
    return {"slug": info.get("slug") or slug(label), "nav": info.get("nav") or label,
            "title": info.get("title") or label, "intro": info.get("intro") or data["site"]["tagline"]}


def cat_path(data, key):
    return f"{cat_info(data, key)['slug']}/"


def guide_path(g):
    return f"gift-guides/{g['slug']}/"


def guide_products(g, by_asin):
    return [by_asin[a] for a in g["asins"] if a in by_asin]


def amazon_url(asin, tag):
    return f"https://www.amazon.com/dp/{asin}?tag={tag}"


def page_path(p):
    return f"picks/{slug(p['name'])}/"


def picture(p, base, eager=False):
    """Card image: WebP with a PNG fallback."""
    load = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
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
  .body { padding:16px; display:flex; flex-direction:column; gap:10px; flex:1; }
  h3 { font-size:18px; line-height:1.3; }
  h3 a { color:inherit; text-decoration:none; }
  h3 a:hover { text-decoration:underline; }
  .body p { color:var(--mut); font-size:15px; flex:1; }
  .btn { display:inline-block; background:var(--acc); color:var(--acc-ink); text-decoration:none; font-weight:600; padding:10px 16px; border-radius:8px; text-align:center; }
  .btn:hover { background:var(--acc-hover); }
  .paid { display:block; text-align:center; color:var(--mut); font-size:12px; margin-top:-4px; }
  .top { padding:20px 0 0; font-size:14px; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }
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
  .prose ul { padding-left:20px; }
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
  .mainnav { margin:0; justify-content:flex-end; gap:6px 14px; }
  @media (max-width:720px) { .mainnav { justify-content:flex-start; } }
  .crumbs { font-size:14px; color:var(--mut); padding-top:8px; }
  .intro { padding:28px 0 8px; text-align:left; }
  .intro h1 { margin-bottom:10px; }
  .intro p { color:var(--mut); max-width:720px; margin:0; }
  .intro .updated { font-size:13px; margin-top:8px; }
  .more { margin-top:14px; font-weight:600; }
  .more a { color:var(--acc); }
  .tiles { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:20px; }
  .tile { display:flex; flex-direction:column; background:var(--card); border:1px solid var(--bd); border-radius:14px; overflow:hidden; color:inherit; text-decoration:none; }
  .tile:hover { border-color:var(--acc); }
  .tile picture { display:block; aspect-ratio:3/2; overflow:hidden; background:#fbf8f3; }
  .tile img { width:100%; height:100%; object-fit:cover; object-position:center 30%; display:block; }
  .tile span { display:flex; flex-direction:column; gap:6px; padding:16px; font-size:15px; color:var(--mut); }
  .tile strong { color:var(--ink); font-size:18px; line-height:1.3; }
  .lead { background:var(--card); border:1px solid var(--bd); border-radius:14px; padding:32px 20px; margin:28px 0; text-align:center; }
  .lead > p { color:var(--mut); max-width:600px; margin:12px auto 0; }
  .lead form { display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-top:18px; }
  .lead input[type=email], .contact input, .contact textarea { padding:10px 12px; border:1px solid var(--bd); border-radius:8px; font:inherit; background:var(--bg); color:var(--ink); }
  .lead input[type=email] { min-width:0; flex:0 1 300px; }
  .lead button, .contact button { border:0; cursor:pointer; font:inherit; }
  .lead small { display:block; margin-top:10px; color:var(--mut); }
  .lead small a { color:var(--acc); }
  .benefits { list-style:none; max-width:560px; margin:20px auto 0; text-align:left; display:flex; flex-direction:column; gap:8px; }
  .benefits li::before { content:"✓ "; color:var(--acc); font-weight:700; }
  .contact { display:flex; flex-direction:column; gap:14px; margin:20px 0; }
  .contact label { display:flex; flex-direction:column; gap:4px; font-weight:600; }
  .contact input, .contact textarea { font-weight:400; width:100%; }
  .contact button { align-self:flex-start; }
  .err { color:#b3261e; font-weight:600; margin-top:10px; }
  @media (prefers-color-scheme: dark) { .err { color:#ff8a80; } }
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
{extra}<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="disclosure">{DISCLOSURE} <a href="/privacy/">Learn more</a></div>
<div class="wrap">
"""


def signup_form(source):
    return f"""<form method="POST" action="/subscribe.php">
        <input type="hidden" name="source" value="{e(source)}">
        <p class="hidden"><label>Leave this empty: <input name="website" tabindex="-1" autocomplete="off"></label></p>
        <input type="email" name="email" placeholder="you@example.com" required autocomplete="email" aria-label="Email address">
        <button class="btn" type="submit">Get Updates</button>
      </form>
      <p class="err" id="signup-err" hidden></p>
      <small>We only use your email to send new kitchen picks, and never sell or share it. See our <a href="/privacy/">privacy policy</a>.</small>"""


def signup(source):
    return f"""    <section class="signup" id="updates">
      <h2>Get the next 5 kitchen finds before anyone else</h2>
      <p>One short email whenever we add new picks. No spam, unsubscribe anytime.</p>
      {signup_form(source)}
    </section>
"""


# Shows a message when a form handler redirects back with ?error=... (pages stay static HTML).
ERR_JS = """<script>(function(){var k=new URLSearchParams(location.search).get("error");if(!k)return;
var m={email:"Please enter a valid email address.",server:"Something went wrong on our side. Please try again in a minute.",
fields:"Please fill in your name, a valid email, and a message of at least 10 characters.",send:"Your message couldn't be sent. Please email us directly instead."};
document.querySelectorAll(".err").forEach(function(el){el.textContent=m[k]||m.server;el.hidden=false;});})();</script>
"""


def topbar(data, crumbs=""):
    """Brand + main navigation on every page except the home page (which has its own header)."""
    site = data["site"]
    return f"""  <div class="top">
    <a class="brand" href="/">{e(site['name'])}</a>
    <nav class="mainnav" aria-label="Main">{main_nav(data)}</nav>
  </div>
{f'  <p class="crumbs">{crumbs}</p>{chr(10)}' if crumbs else ''}"""


def main_nav(data):
    keys = [k for k in data["categories"] if any(p["category"] == k for p in data["products"])]
    links = [f'<a href="/{cat_path(data, k)}">{e(cat_info(data, k)["nav"])}</a>' for k in keys]
    if data.get("guides"):
        links.append('<a href="/gift-guides/">Gift Guides</a>')
    links.append('<a href="/newsletter/">Get Updates</a>')
    return " ".join(links)


def foot(site):
    return f"""  <footer>
    <p>{e(site['name'])} is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com. {DISCLOSURE} Product details can change — check the current listing on Amazon before you buy.</p>
    <p style="margin-top:8px">Follow along on <a href="{e(site['pinterest'])}">Pinterest</a> and <a href="{e(site['facebook'])}">Facebook</a> · <a href="/about/">About</a> · <a href="/contact/">Contact</a> · <a href="/newsletter/">Newsletter</a> · <a href="/privacy/">Privacy policy</a></p>
  </footer>
</div>
{ERR_JS}</body>
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
            sections.append(f'    <section id="{e(key)}">\n      <h2>{e(label)}</h2>\n      <div class="grid">\n{cards}\n      </div>\n'
                            f'      <p class="more"><a href="/{cat_path(data, key)}">See all {e(cat_info(data, key)["nav"].lower())} picks →</a></p>\n    </section>')
    nav = main_nav(data)
    top_cards = "\n".join(card(p, tag, eager=i < EAGER) for i, p in enumerate(top))
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
{chr(10).join(sections)}
{guides_teaser(data)}{signup("home")}  </main>
""" + foot(site)


def describe(text, limit=155):
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:—-") + "…"


def render_pick(data, p, products):
    site, tag = data["site"], data["site"]["associate_tag"]
    label = data["categories"][p["category"]]
    base = "/"
    more = [q for q in products if q["category"] == p["category"] and q["asin"] != p["asin"]][:3]
    more_html = ""
    if more:
        cards = "\n".join(card(q, tag, base) for q in more)
        more_html = f'    <section>\n      <h2>More {e(label)}</h2>\n      <div class="grid">\n{cards}\n      </div>\n    </section>\n'
    crumbs = ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": site["name"], "item": f"{site['url']}/"},
        {"@type": "ListItem", "position": 2, "name": label, "item": f"{site['url']}/{cat_path(data, p['category'])}"},
        {"@type": "ListItem", "position": 3, "name": p["name"], "item": f"{site['url']}/{page_path(p)}"}]})
    points = "".join(f"<li>{e(pt)}</li>" for pt in p["graphic"]["points"])
    title = f"{p['name']} | {site['name']}"
    return head(site, title, describe(p["blurb"]), page_path(p), f"{site['url']}/img/{p['asin']}.png",
                p["graphic"]["headline"], 1000, 1500, crumbs + "\n") + topbar(
        data, f'<a href="/">Home</a> › <a href="/{cat_path(data, p["category"])}">{e(label)}</a>') + f"""  <main id="main">
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
{more_html}{signup("pick")}  </main>
""" + foot(site)


def render_privacy(data):
    site = data["site"]
    return head(site, f"Privacy Policy | {site['name']}", f"How {site['name']} handles cookies, affiliate links, and email sign-ups.",
                "privacy/", f"{site['url']}/img/og.png", site["name"], OG_W, OG_H) + topbar(data) + f"""  <main id="main" class="prose">
    <h1>Privacy Policy</h1>
    <p>Last updated {PRIVACY_UPDATED}.</p>
    <h2>Affiliate links and cookies</h2>
    <p>{e(site['name'])} is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com. {DISCLOSURE}</p>
    <p>When you click a product link on this site you go to Amazon.com. Third parties, including Amazon, may place and read cookies on your browser, or use web beacons, to collect information such as which link you clicked and whether a purchase followed, so that we can be credited for the referral. That information is handled under <a href="https://www.amazon.com/gp/help/customer/display.html?nodeId=468496" rel="nofollow noopener">Amazon's Privacy Notice</a>. We never see your Amazon account, payment details, or what you personally bought.</p>
    <p>This site itself sets no tracking or advertising cookies and runs no analytics scripts.</p>
    <h2>Email sign-up</h2>
    <p>If you join our email list, we collect only the email address you enter, the date, and which page you signed up from. It is stored privately on our own web hosting account (Hostinger), not in a third-party marketing tool. We use your address only to send new kitchen picks. We never sell, rent, or share it. Every email includes an unsubscribe link, and you can ask us to delete your address at any time.</p>
    <h2>Contact form</h2>
    <p>If you use our contact form, we receive your name, email address, and message by email so we can reply. We keep a copy only as long as we need it to answer you.</p>
    <h2>Hosting and server logs</h2>
    <p>Our host may log standard request data (such as IP address, browser type, and pages requested) to keep the site running and secure.</p>
    <h2>Children</h2>
    <p>This site is not directed to children under 13, and we do not knowingly collect their information.</p>
    <h2>Contact</h2>
    <p>Questions or deletion requests: email <a href="mailto:{e(site['email'])}">{e(site['email'])}</a>, use our <a href="/contact/">contact form</a>, or reply to any email we send you.</p>
    <h2>Changes</h2>
    <p>If this policy changes, we will update the date above.</p>
  </main>
""" + foot(site)


def render_simple(data, path, title, heading, body):
    """Small noindex utility page (form success, 404) with a way back into the picks."""
    site = data["site"]
    return head(site, f"{title} | {site['name']}", site["tagline"], path, f"{site['url']}/img/og.png",
                site["name"], OG_W, OG_H, noindex=True) + topbar(data) + f"""  <main id="main" class="prose">
    <h1>{e(heading)}</h1>
    <p>{body}</p>
    <p><a class="btn" href="/#top-picks">See this week's top picks</a></p>
  </main>
""" + foot(site)


def crumbs_ld(site, trail):
    return ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": name, "item": f"{site['url']}/{path}"}
        for i, (name, path) in enumerate([(site["name"], "")] + trail)]})


def render_listing(data, path, title, h1, description, intro, items, trail, extra_html="", source="listing"):
    """Landing page for a category or gift guide: intro, product grid, email capture."""
    site, tag = data["site"], data["site"]["associate_tag"]
    item_ld = ld({"@context": "https://schema.org", "@type": "ItemList", "name": h1,
                  "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": p["name"],
                                       "url": f"{site['url']}/{page_path(p)}"} for i, p in enumerate(items)]})
    crumbs = " › ".join([f'<a href="/">Home</a>'] + [f'<a href="/{pth}">{e(n)}</a>' for n, pth in trail[:-1]] + [e(trail[-1][0])])
    cards = "\n".join(card(p, tag, "/", eager=i < EAGER) for i, p in enumerate(items))
    return head(site, f"{title} | {site['name']}", description, path, f"{site['url']}/img/og.png",
                f"{site['name']} — {h1}", OG_W, OG_H, crumbs_ld(site, trail) + "\n" + item_ld + "\n") + topbar(data, crumbs) + f"""  <main id="main">
    <header class="intro">
      <h1>{e(h1)}</h1>
      <p>{e(intro)}</p>
{extra_html}    </header>
    <section>
      <div class="grid">
{cards}
      </div>
    </section>
{signup(source)}  </main>
""" + foot(site)


def render_category(data, key, products):
    info = cat_info(data, key)
    items = [p for p in products if p["category"] == key]
    return render_listing(data, cat_path(data, key), info["title"], data["categories"][key],
                          describe(info["intro"]), info["intro"], items, [(data["categories"][key], cat_path(data, key))],
                          source=f"category/{key}")


def render_guide(data, g, by_asin):
    extra = f'      <p class="updated">Updated {e(g["updated"])} · Product details and availability can change, so check each listing on Amazon.</p>\n'
    return render_listing(data, guide_path(g), g["title"], g["title"], g["description"], g["intro"],
                          guide_products(g, by_asin), [("Gift Guides", "gift-guides/"), (g["title"], guide_path(g))],
                          extra, source=f"guide/{g['slug']}")


def guide_tiles(data, by_asin):
    tiles = []
    for g in data.get("guides", []):
        first = by_asin.get(g.get("cover")) or guide_products(g, by_asin)[0]
        tiles.append(f"""      <a class="tile" href="/{guide_path(g)}">
        <picture><source srcset="/img/{e(first['asin'])}-sq.webp" type="image/webp"><img src="/img/{e(first['asin'])}-sq.png" alt="" loading="lazy" width="800" height="800"></picture>
        <span><strong>{e(g['title'])}</strong>{e(describe(g['description'], 110))}</span>
      </a>""")
    return "\n".join(tiles)


def guides_teaser(data):
    if not data.get("guides"):
        return ""
    by_asin = {p["asin"]: p for p in data["products"]}
    return f"""    <section id="gift-guides">
      <h2>Gift Guides</h2>
      <div class="tiles">
{guide_tiles(data, by_asin)}
      </div>
    </section>
"""


def render_guides_index(data):
    site = data["site"]
    by_asin = {p["asin"]: p for p in data["products"]}
    desc = "Kitchen gift guides for home cooks, coffee lovers, and stocking stuffers — practical picks that fit small kitchens."
    return head(site, f"Kitchen Gift Guides | {site['name']}", desc, "gift-guides/", f"{site['url']}/img/og.png",
                site["name"], OG_W, OG_H, crumbs_ld(site, [("Gift Guides", "gift-guides/")]) + "\n") + topbar(
        data, '<a href="/">Home</a> › Gift Guides') + f"""  <main id="main">
    <header class="intro">
      <h1>Kitchen Gift Guides</h1>
      <p>{e(desc)}</p>
    </header>
    <section>
      <div class="tiles">
{guide_tiles(data, by_asin)}
      </div>
    </section>
{signup("gift-guides")}  </main>
""" + foot(site)


def render_about(data):
    site = data["site"]
    cats = ", ".join(cat_info(data, k)["nav"].lower() for k in data["categories"])
    return head(site, f"About | {site['name']}", f"How {site['name']} chooses the kitchen products it features, and how the site is funded.",
                "about/", f"{site['url']}/img/og.png", site["name"], OG_W, OG_H) + topbar(data) + f"""  <main id="main" class="prose">
    <h1>About {e(site['name'])}</h1>
    <p>{e(site['name'])} is a curated collection of kitchen products for small, busy kitchens: {e(cats)}. The goal is simple: help you find the one tool or storage fix that solves a real problem in your kitchen, without wading through endless search results.</p>
    <h2>How we choose products</h2>
    <ul>
      <li>We look for products that solve a specific, everyday kitchen problem and suit kitchens with limited space.</li>
      <li>We research each product's Amazon listing, specifications, and the experiences shared in customer reviews before adding it.</li>
      <li>We describe products from their listings and published details. We do not claim to have personally tested every item.</li>
      <li>We don't post prices or ratings because they change often. Every product links to its current Amazon listing so you can check the latest details.</li>
    </ul>
    <h2>How the site is funded</h2>
    <p>{e(site['name'])} is a participant in the Amazon Services LLC Associates Program. {DISCLOSURE} This doesn't change what you pay, and it is how we keep the site free and ad-free.</p>
    <h2>Get in touch</h2>
    <p>Questions, corrections, or product suggestions are welcome. Email <a href="mailto:{e(site['email'])}">{e(site['email'])}</a> or use our <a href="/contact/">contact form</a>.</p>
    <p><a class="btn" href="/#top-picks">See this week's top picks</a></p>
  </main>
""" + foot(site)


def render_contact(data):
    site = data["site"]
    return head(site, f"Contact | {site['name']}", f"Contact {site['name']} with questions, corrections, or product suggestions.",
                "contact/", f"{site['url']}/img/og.png", site["name"], OG_W, OG_H) + topbar(data) + f"""  <main id="main" class="prose">
    <h1>Contact Us</h1>
    <p>Questions, corrections, or a product you think belongs here? Send us a message and we'll reply by email, usually within two business days. You can also email <a href="mailto:{e(site['email'])}">{e(site['email'])}</a> directly.</p>
    <p>Questions about an order, shipping, or a return go to Amazon, since purchases are made there and we can't see or change orders.</p>
    <form class="contact" id="form" method="POST" action="/contact.php">
      <p class="hidden"><label>Leave this empty: <input name="website" tabindex="-1" autocomplete="off"></label></p>
      <label>Name <input name="name" required maxlength="100" autocomplete="name"></label>
      <label>Email <input type="email" name="email" required maxlength="254" autocomplete="email"></label>
      <label>Message <textarea name="message" required minlength="10" maxlength="5000" rows="7"></textarea></label>
      <p class="err" hidden></p>
      <button class="btn" type="submit">Send message</button>
    </form>
    <p><small>We use your details only to reply to you. See our <a href="/privacy/">privacy policy</a>.</small></p>
  </main>
""" + foot(site)


def render_newsletter(data, products):
    site, tag = data["site"], data["site"]["associate_tag"]
    latest = "\n".join(card(p, tag, "/") for p in products[:3])
    desc = "Join the Kitchen Finds & Favorites email list: new kitchen organization, gadget, and small appliance picks in one short email."
    return head(site, f"Get New Kitchen Finds by Email | {site['name']}", desc, "newsletter/", f"{site['url']}/img/og.png",
                site["name"], OG_W, OG_H) + topbar(data) + f"""  <main id="main">
    <section class="lead" id="updates">
      <h1>Get the next 5 kitchen finds before anyone else</h1>
      <p>We add new small-kitchen picks every week. Join the list and get them in one short email: no spam, no daily blasts, unsubscribe anytime.</p>
      <ul class="benefits">
        <li><strong>New picks first.</strong> See new organization fixes, gadgets, and small appliances as soon as they're added.</li>
        <li><strong>Seasonal gift guides.</strong> Holiday and occasion guides for the home cooks in your life.</li>
        <li><strong>Small-kitchen focus.</strong> Every pick is chosen for kitchens with limited space.</li>
      </ul>
      {signup_form("newsletter")}
    </section>
    <section>
      <h2>The latest picks</h2>
      <div class="grid">
{latest}
      </div>
    </section>
  </main>
""" + foot(site)


FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#c8643b"/><text x="32" y="44" font-family="Georgia,serif" font-size="38" font-weight="700" fill="#fff" text-anchor="middle">K</text></svg>
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
    import graphics  # needs Pillow; only required for a full build
    graphics.render_all(data, OUT, force="--force-graphics" in sys.argv)
    url, tag = data["site"]["url"], data["site"]["associate_tag"]
    products = sorted(data["products"], key=lambda p: p["added"], reverse=True)
    (OUT / "index.html").write_text(render_home(data, products), encoding="utf-8")
    # Rebuild product pages from scratch so removed products don't leave stale pages.
    shutil.rmtree(OUT / "picks", ignore_errors=True)
    for p in products:
        d = OUT / page_path(p)
        d.mkdir(parents=True)
        (d / "index.html").write_text(render_pick(data, p, products), encoding="utf-8")
    # Category landing pages and gift guides: rebuilt from scratch so renamed/removed ones don't linger.
    by_asin = {p["asin"]: p for p in products}
    pages = {}
    for key in data["categories"]:
        if any(p["category"] == key for p in products):
            pages[cat_path(data, key)] = render_category(data, key, products)
    if data.get("guides"):
        shutil.rmtree(OUT / "gift-guides", ignore_errors=True)
        pages["gift-guides/"] = render_guides_index(data)
        for g in data["guides"]:
            pages[guide_path(g)] = render_guide(data, g, by_asin)
    pages["privacy/"] = render_privacy(data)
    pages["about/"] = render_about(data)
    pages["contact/"] = render_contact(data)
    pages["newsletter/"] = render_newsletter(data, products)
    pages["contact/sent/"] = render_simple(
        data, "contact/sent/", "Message sent", "Thanks, your message is on its way",
        "We've received your message and will reply by email, usually within two business days.")
    for path, page in pages.items():
        (OUT / path).mkdir(parents=True, exist_ok=True)
        (OUT / path / "index.html").write_text(page, encoding="utf-8")
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
    # Hostinger server files: .htaccess (HTTPS, CORS for /img, caching, 404) and the PHP form handlers.
    (OUT / "_headers").unlink(missing_ok=True)  # Netlify-only; netlify.toml sets the same header there
    for f in (ROOT / "php").iterdir():
        shutil.copyfile(f, OUT / f.name)
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {url}/sitemap.xml\n", encoding="utf-8")
    # Machine-readable feed: the posting routines read this as their queue.
    feed = [dict(p, page_url=f"{url}/{page_path(p)}", pin_image=f"{url}/img/{p['asin']}.png",
                 amazon_url=amazon_url(p["asin"], tag))
            for p in sorted(data["products"], key=lambda p: p["added"])]
    (OUT / "products.json").write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    newest = products[0]["added"]
    def newest_of(items):
        return max(p["added"] for p in items)
    urls = [(f"{url}/", newest)]
    urls += [(f"{url}/{cat_path(data, k)}", newest_of([p for p in products if p["category"] == k]))
             for k in data["categories"] if any(p["category"] == k for p in products)]
    if data.get("guides"):
        urls.append((f"{url}/gift-guides/", max(g["updated"] for g in data["guides"])))
        urls += [(f"{url}/{guide_path(g)}", g["updated"]) for g in data["guides"]]
    urls += [(f"{url}/newsletter/", None), (f"{url}/about/", None), (f"{url}/contact/", None),
             (f"{url}/privacy/", PRIVACY_UPDATED)]
    urls += [(f"{url}/{page_path(p)}", p["added"]) for p in products]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{e(u)}</loc>{f'<lastmod>{m}</lastmod>' if m else ''}</url>\n" for u, m in urls)
        + "</urlset>\n", encoding="utf-8")
    print(f"Built public/ with {len(products)} products")


if __name__ == "__main__":
    main()
