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
PRIVACY_UPDATED = "2026-10-12"  # bump when the privacy text changes
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
    return data, errors


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
  :root { --bg:#fbf8f3; --card:#fff; --ink:#2b2622; --mut:#6f665d; --acc:#c8643b; --acc-ink:#fff; --bd:#ece4d8; }
  @media (prefers-color-scheme: dark) { :root { --bg:#1c1a18; --card:#262320; --ink:#f1ebe3; --mut:#b3a99d; --acc:#e07a4f; --acc-ink:#1c1a18; --bd:#3a3530; } }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--ink); font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  .wrap { max-width:1080px; margin:0 auto; padding:0 16px; }
  .disclosure { position:sticky; top:0; z-index:10; background:var(--ink); color:var(--bg); text-align:center; font-size:13px; padding:6px 16px; }
  .disclosure a { color:inherit; }
  header { padding:48px 0 24px; text-align:center; }
  h1 { font-size:clamp(28px,5vw,44px); line-height:1.15; }
  h1 .sub { display:block; font-size:clamp(16px,2.4vw,20px); font-weight:600; color:var(--acc); margin-top:8px; }
  header p { color:var(--mut); max-width:560px; margin:12px auto 0; }
  nav { margin-top:16px; display:flex; gap:16px; justify-content:center; flex-wrap:wrap; font-size:14px; }
  nav a, .crumbs a, .brand { color:var(--acc); }
  section { padding:24px 0; }
  h2 { font-size:24px; margin-bottom:16px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:20px; }
  .card { background:var(--card); border:1px solid var(--bd); border-radius:14px; overflow:hidden; display:flex; flex-direction:column; scroll-margin-top:48px; }
  .card:target { outline:3px solid var(--acc); }
  .img { background:#fbf8f3; display:block; aspect-ratio:1; }
  .img picture { display:block; width:100%; height:100%; }
  .img img { width:100%; height:100%; object-fit:cover; display:block; }
  .body { padding:16px; display:flex; flex-direction:column; gap:10px; flex:1; }
  h3 { font-size:18px; line-height:1.3; }
  h3 a { color:inherit; text-decoration:none; }
  h3 a:hover { text-decoration:underline; }
  .body p { color:var(--mut); font-size:15px; flex:1; }
  .btn { display:inline-block; background:var(--acc); color:var(--acc-ink); text-decoration:none; font-weight:600; padding:10px 16px; border-radius:8px; text-align:center; }
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
  .prose ul { padding-left:20px; }
  .prose a { color:var(--acc); }
  .signup { background:var(--card); border:1px solid var(--bd); border-radius:14px; padding:28px 20px; text-align:center; margin:24px 0; }
  .signup p { color:var(--mut); }
  .signup form { display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-top:14px; }
  .signup input[type=email] { padding:10px 12px; border:1px solid var(--bd); border-radius:8px; min-width:0; flex:0 1 280px; font:inherit; background:var(--bg); color:var(--ink); }
  .signup button { border:0; cursor:pointer; font:inherit; }
  .signup small { display:block; margin-top:10px; color:var(--mut); }
  .signup small a { color:var(--acc); }
  .hidden { position:absolute; left:-9999px; }
  footer { border-top:1px solid var(--bd); padding:24px 0 40px; color:var(--mut); font-size:13px; }
  footer a { color:var(--acc); }
"""


def head(site, title, description, path, og_image, og_alt, og_w, og_h, extra=""):
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
<meta property="og:type" content="website">
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
<div class="disclosure">{DISCLOSURE} <a href="/privacy/">Learn more</a></div>
<div class="wrap">
"""


def signup():
    return """    <section class="signup" id="updates">
      <h2>Get the next 5 kitchen finds before anyone else</h2>
      <p>One short email whenever we add new picks. No spam, unsubscribe anytime.</p>
      <form name="updates" method="POST" data-netlify="true" netlify-honeypot="bot-field">
        <input type="hidden" name="form-name" value="updates">
        <p class="hidden"><label>Don't fill this out if you're human: <input name="bot-field"></label></p>
        <input type="email" name="email" placeholder="you@example.com" required aria-label="Email address">
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
    nav = " ".join(f'<a href="#{e(k)}">{e(v)}</a>' for k, v in data["categories"].items()
                   if any(p["category"] == k and p["asin"] not in top_asins for p in products))
    top_cards = "\n".join(card(p, tag, eager=i < EAGER) for i, p in enumerate(top))
    title = f"Small Kitchen Organization & Gadget Picks | {site['name']}"
    return head(site, title, site["tagline"], "", f"{site['url']}/img/og.png",
                f"{site['name']} — {site['tagline']}", OG_W, OG_H, site_ld(site, products) + "\n") + f"""  <header>
    <h1>{e(site['name'])}<span class="sub">Organization, gadgets &amp; small appliances for small kitchens</span></h1>
    <p>{e(site['tagline'])}</p>
    <nav>{nav}</nav>
  </header>
  <main>
    <section id="top-picks">
      <h2>This Week's Top Picks</h2>
      <div class="grid">
{top_cards}
      </div>
    </section>
{chr(10).join(sections)}
{signup()}  </main>
""" + foot(site)


def describe(text, limit=155):
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:—-") + "…"


def render_pick(data, p, products):
    site, tag = data["site"], data["site"]["associate_tag"]
    label = data["categories"][p["category"]]
    base = "../../"
    more = [q for q in products if q["category"] == p["category"] and q["asin"] != p["asin"]][:3]
    more_html = ""
    if more:
        cards = "\n".join(card(q, tag, base) for q in more)
        more_html = f'    <section>\n      <h2>More {e(label)}</h2>\n      <div class="grid">\n{cards}\n      </div>\n    </section>\n'
    crumbs = ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": site["name"], "item": f"{site['url']}/"},
        {"@type": "ListItem", "position": 2, "name": label, "item": f"{site['url']}/#{p['category']}"},
        {"@type": "ListItem", "position": 3, "name": p["name"], "item": f"{site['url']}/{page_path(p)}"}]})
    points = "".join(f"<li>{e(pt)}</li>" for pt in p["graphic"]["points"])
    title = f"{p['name']} | {site['name']}"
    return head(site, title, describe(p["blurb"]), page_path(p), f"{site['url']}/img/{p['asin']}.png",
                p["graphic"]["headline"], 1000, 1500, crumbs + "\n") + f"""  <div class="top">
    <a class="brand" href="{base}">{e(site['name'])}</a>
    <span class="crumbs"><a href="{base}">Home</a> › <a href="{base}#{e(p['category'])}">{e(label)}</a></span>
  </div>
  <main>
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


def render_privacy(data):
    site = data["site"]
    return head(site, f"Privacy Policy | {site['name']}", f"How {site['name']} handles cookies, affiliate links, and email sign-ups.",
                "privacy/", f"{site['url']}/img/og.png", site["name"], OG_W, OG_H) + f"""  <div class="top"><a class="brand" href="../">{e(site['name'])}</a></div>
  <main class="prose">
    <h1>Privacy Policy</h1>
    <p>Last updated {PRIVACY_UPDATED}.</p>
    <h2>Affiliate links and cookies</h2>
    <p>{e(site['name'])} is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com. {DISCLOSURE}</p>
    <p>When you click a product link on this site you go to Amazon.com. Third parties, including Amazon, may place and read cookies on your browser, or use web beacons, to collect information such as which link you clicked and whether a purchase followed, so that we can be credited for the referral. That information is handled under <a href="https://www.amazon.com/gp/help/customer/display.html?nodeId=468496" rel="nofollow noopener">Amazon's Privacy Notice</a>. We never see your Amazon account, payment details, or what you personally bought.</p>
    <p>This site itself sets no tracking or advertising cookies and runs no analytics scripts.</p>
    <h2>Email sign-up</h2>
    <p>If you join our email list, we collect only the email address you enter. The form is processed by our host, Netlify (see <a href="https://www.netlify.com/privacy/" rel="nofollow noopener">Netlify's privacy policy</a>). We use your address only to send new kitchen picks. We never sell, rent, or share it. Every email includes an unsubscribe link, and you can ask us to delete your address at any time.</p>
    <h2>Hosting and server logs</h2>
    <p>Our host may log standard request data (such as IP address, browser type, and pages requested) to keep the site running and secure.</p>
    <h2>Children</h2>
    <p>This site is not directed to children under 13, and we do not knowingly collect their information.</p>
    <h2>Contact</h2>
    <p>Questions or deletion requests: message us on <a href="{e(site['facebook'])}">Facebook</a> or <a href="{e(site['pinterest'])}">Pinterest</a>, or reply to any email we send you.</p>
    <h2>Changes</h2>
    <p>If this policy changes, we will update the date above.</p>
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
    (OUT / "privacy").mkdir(exist_ok=True)
    (OUT / "privacy" / "index.html").write_text(render_privacy(data), encoding="utf-8")
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
    urls = [(f"{url}/", newest), (f"{url}/privacy/", PRIVACY_UPDATED)] + [(f"{url}/{page_path(p)}", p["added"]) for p in products]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{e(u)}</loc>{f'<lastmod>{m}</lastmod>' if m else ''}</url>\n" for u, m in urls)
        + "</urlset>\n", encoding="utf-8")
    print(f"Built public/ with {len(products)} products")


if __name__ == "__main__":
    main()
