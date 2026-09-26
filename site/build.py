#!/usr/bin/env python3
"""Build the Kitchen Finds & Favorites landing page from products.json.

Usage: python3 build.py          # validate products.json and write public/
       python3 build.py --check  # validate only, exit non-zero on problems

Standard library only, so it runs anywhere (routines, Netlify, locally).
"""
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "public"
TOP_PICKS = 6  # newest N products shown in "This Week's Top Picks"
EXCLUDED_ASINS = {"B07TVDFVV9"}  # Associates-excluded; never list
DISCLOSURE = "As an Amazon Associate, I earn from qualifying purchases."
PIN_DISCLOSURE = "#ad As an Amazon Associate I earn from qualifying purchases."


def load():
    data = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
    errors = []
    seen = set()
    cats = data["categories"]
    for i, p in enumerate(data["products"]):
        where = f"products[{i}] ({p.get('asin', '?')})"
        for field in ("asin", "name", "category", "image", "blurb", "added"):
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
        if p.get("category") not in cats:
            errors.append(f"{where}: unknown category '{p.get('category')}' (add it to 'categories')")
        if not str(p.get("image", "")).startswith("https://"):
            errors.append(f"{where}: image must be an https URL")
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
    return data, errors


def amazon_url(asin, tag):
    return f"https://www.amazon.com/dp/{asin}?tag={tag}"


def card(p, tag):
    e = html.escape
    return f"""      <article class="card" id="{e(p['asin'])}">
        <a class="img" href="{e(amazon_url(p['asin'], tag))}" rel="sponsored nofollow noopener" target="_blank">
          <img src="{e(p['image'])}" alt="{e(p['name'])}" loading="lazy" width="600" height="600">
        </a>
        <div class="body">
          <h3>{e(p['name'])}</h3>
          <p>{e(p['blurb'])}</p>
          <a class="btn" href="{e(amazon_url(p['asin'], tag))}" rel="sponsored nofollow noopener" target="_blank">Check price on Amazon →</a>
        </div>
      </article>"""


def render(data):
    site, tag, e = data["site"], data["site"]["associate_tag"], html.escape
    products = sorted(data["products"], key=lambda p: p["added"], reverse=True)
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
    og_image = e(top[0]["image"]) if top else ""
    top_cards = "\n".join(card(p, tag) for p in top)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(site['name'])} — Kitchen Organization Finds</title>
<meta name="description" content="{e(site['tagline'])}">
<link rel="canonical" href="{e(site['url'])}/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(site['name'])}">
<meta property="og:title" content="{e(site['name'])}">
<meta property="og:description" content="{e(site['tagline'])}">
<meta property="og:url" content="{e(site['url'])}/">
<meta property="og:image" content="{og_image}">
<style>
  :root {{ --bg:#fbf8f3; --card:#fff; --ink:#2b2622; --mut:#6f665d; --acc:#c8643b; --acc-ink:#fff; --bd:#ece4d8; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg:#1c1a18; --card:#262320; --ink:#f1ebe3; --mut:#b3a99d; --acc:#e07a4f; --acc-ink:#1c1a18; --bd:#3a3530; }} }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--ink); font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:0 16px; }}
  .disclosure {{ background:var(--ink); color:var(--bg); text-align:center; font-size:13px; padding:6px 16px; }}
  header {{ padding:48px 0 24px; text-align:center; }}
  h1 {{ font-size:clamp(28px,5vw,44px); line-height:1.15; }}
  header p {{ color:var(--mut); max-width:560px; margin:12px auto 0; }}
  nav {{ margin-top:16px; display:flex; gap:16px; justify-content:center; flex-wrap:wrap; font-size:14px; }}
  nav a {{ color:var(--acc); }}
  section {{ padding:24px 0; }}
  h2 {{ font-size:24px; margin-bottom:16px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:20px; }}
  .card {{ background:var(--card); border:1px solid var(--bd); border-radius:14px; overflow:hidden; display:flex; flex-direction:column; scroll-margin-top:16px; }}
  .card:target {{ outline:3px solid var(--acc); }}
  .img {{ background:#fff; display:block; aspect-ratio:1; }}
  .img img {{ width:100%; height:100%; object-fit:contain; padding:16px; }}
  .body {{ padding:16px; display:flex; flex-direction:column; gap:10px; flex:1; }}
  h3 {{ font-size:18px; line-height:1.3; }}
  .body p {{ color:var(--mut); font-size:15px; flex:1; }}
  .btn {{ display:inline-block; background:var(--acc); color:var(--acc-ink); text-decoration:none; font-weight:600; padding:10px 16px; border-radius:8px; text-align:center; }}
  .signup {{ background:var(--card); border:1px solid var(--bd); border-radius:14px; padding:28px 20px; text-align:center; margin:24px 0; }}
  .signup p {{ color:var(--mut); }}
  .signup form {{ display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-top:14px; }}
  .signup input[type=email] {{ padding:10px 12px; border:1px solid var(--bd); border-radius:8px; min-width:0; flex:0 1 280px; font:inherit; background:var(--bg); color:var(--ink); }}
  .signup button {{ border:0; cursor:pointer; font:inherit; }}
  .signup small {{ display:block; margin-top:10px; color:var(--mut); }}
  .hidden {{ position:absolute; left:-9999px; }}
  footer {{ border-top:1px solid var(--bd); padding:24px 0 40px; color:var(--mut); font-size:13px; }}
  footer a {{ color:var(--acc); }}
</style>
</head>
<body>
<div class="disclosure">{DISCLOSURE}</div>
<div class="wrap">
  <header>
    <h1>{e(site['name'])}</h1>
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
    <section class="signup" id="updates">
      <h2>Get the next 5 kitchen finds before anyone else</h2>
      <p>One short email whenever we add new picks. No spam, unsubscribe anytime.</p>
      <form name="updates" method="POST" data-netlify="true" netlify-honeypot="bot-field">
        <input type="hidden" name="form-name" value="updates">
        <p class="hidden"><label>Don't fill this out if you're human: <input name="bot-field"></label></p>
        <input type="email" name="email" placeholder="you@example.com" required aria-label="Email address">
        <button class="btn" type="submit">Get Updates</button>
      </form>
      <small>We only use this to send kitchen product picks — nothing else.</small>
    </section>
  </main>
  <footer>
    <p>{e(site['name'])} is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com. {DISCLOSURE}</p>
    <p style="margin-top:8px">Follow along on <a href="{e(site['pinterest'])}">Pinterest</a>.</p>
  </footer>
</div>
</body>
</html>
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
    url = data["site"]["url"]
    (OUT / "index.html").write_text(render(data), encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {url}/sitemap.xml\n", encoding="utf-8")
    # Machine-readable feed: the Pinterest routine reads this as its queue.
    feed = [dict(p, page_url=f"{url}/#{p['asin']}", amazon_url=amazon_url(p["asin"], data["site"]["associate_tag"]))
            for p in sorted(data["products"], key=lambda p: p["added"])]
    (OUT / "products.json").write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    newest = max(p["added"] for p in data["products"])
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{url}/</loc><lastmod>{newest}</lastmod></url>\n"
        "</urlset>\n", encoding="utf-8")
    print(f"Built public/ with {len(data['products'])} products")


if __name__ == "__main__":
    main()
