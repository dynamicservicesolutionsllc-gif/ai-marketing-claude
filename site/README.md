# Kitchen Finds & Favorites website

Live at https://kitchenfindsfavorites.com, hosted on Hostinger. The GitHub Actions workflow
`.github/workflows/deploy-hostinger.yml` uploads `site/public/` to `public_html/` over FTPS whenever it changes on `main`
(only changed files are sent). The old https://kitchenfindsfavorites.netlify.app address is being retired; see "Netlify" below.

## Pages

| Path | Page | Source |
|---|---|---|
| `/` | Home: top picks, every category, gift-guide teaser, email signup | `render_home` |
| `/picks/<slug>/` | One page per product (pins and posts link here) | `render_pick` |
| `/kitchen-organization/`, `/kitchen-gadgets/`, `/small-kitchen-appliances/`, `/drinkware/` | Category landing pages | `category_pages` in `products.json` |
| `/gift-guides/`, `/gift-guides/<slug>/` | Seasonal gift guides | `guides` in `products.json` |
| `/newsletter/` | Email signup landing page (link here from ads and bios) | `render_newsletter` |
| `/about/`, `/contact/`, `/privacy/` | Trust and compliance pages | `build.py` |

A new category works without a `category_pages` entry (slug and intro fall back to defaults), but add one for a good
URL and SEO intro. A gift guide is `{slug, nav, title, description, intro, updated, cover, asins[]}`; every ASIN must be a
live product, and the build rejects prices, star ratings, and best-seller claims in guide copy.

## Adding a product

1. Append an entry to `products.json` (`asin`, `name`, `category`, `graphic` {`label`, `headline`, 3 `points`}, `blurb`, `added`, and optionally
   `pin`: `title` ≤100 chars, `description` ≤500 chars starting with `#ad As an Amazon Associate I earn from qualifying purchases.`, `board`).
   Do **not** add price or star ratings — static Amazon prices/ratings violate the Associates agreement.
   Do **not** use Amazon-hosted product photos: Amazon only licenses them through its own tools/API. `graphics.py`
   renders an original square card (`public/img/<ASIN>-sq.png`) and a 1000x1500 pin graphic (`public/img/<ASIN>.png`).
2. `pip install pillow` (once), then `python3 build.py` — validates the data, renders new graphics, and regenerates `public/`.
   `--force-graphics` re-renders every graphic after a design change.
3. Commit `products.json` and `public/` together and get it onto `main` (the Hostinger deploy runs from `main`).

Each product gets its own page at `/picks/<slug>/` (slug from the product name), and pins/posts link there.
The landing page also keeps a `#<ASIN>` anchor per card, so older pins that link to anchors still work.
The newest 6 products appear under "This Week's Top Picks"; older ones move into their category section.
`build.py` also writes `/privacy/`, `/thanks/` (signup success page), `/404.html`, `/favicon.svg`, the sitemap (every indexable page), and JSON-LD structured data.
The site accent is `#ad512b` (light) / `#e07a4f` (dark) so buttons and links meet WCAG AA contrast; the graphics keep their original `#c8643b` orange.

## Compliance rules the build enforces

- The Associates disclosure is in a sticky bar on every page, in the footer, and as "Paid link" under every Amazon button.
- No prices, star ratings, review counts, or Amazon photos (`build.py` rejects them).
- Copy must not imply hands-on testing or personal use ("tested", "we use", …) — `build.py` rejects it.
- Spec claims in blurbs, graphic points, and pins (sizes, hours, temperatures) must match the current Amazon listing.

## Email list rules

## Server files (Hostinger)

`php/` is copied into `public/` on every build:
- `.htaccess`: forces https://kitchenfindsfavorites.com (no www), CORS on images for the posting routines, caching, 404 page,
  and blocks private files.
- `subscribe.php`: the signup form. Saves addresses to `kff-data/subscribers.csv` in the folder **next to** `public_html`
  (not reachable from the web; deploys never touch it). Download it from hPanel → File Manager.
- `contact.php`: the contact form. Emails help@kitchenfindsfavorites.com (reply goes to the sender) and keeps a copy in
  `kff-data/contact-messages.csv`.

## Email list rules

When emails start going out:
- Link to pages on this site, never straight to Amazon (Amazon restricts Special Links in emails).
- Every email needs the sender's name, a valid physical postal address, and a working unsubscribe link (CAN-SPAM).
- Keep the promise in the privacy policy: picks only, never sold or shared.

## Routine handoff

`build.py` also publishes `public/products.json` (live at `/products.json`), including each product's `page_url` (its `/picks/<slug>/` page) and
`pin_image`. The Pinterest and Facebook posting routines read it as their queue, link posts to `page_url`, and use `pin_image`.
The Pinterest routine
pins any ASIN not yet in its Posted Pins Log. To pull a product (e.g. it turns out Associates-excluded), the Pinterest
routine creates a Google Doc titled `KFF site removal request - <ASIN>`; the daily site routine removes the product and trashes the doc.

Routine prompts are versioned in `routines/`.

## Netlify

Netlify still deploys `site/public/` from `main` until the new domain is verified live. After that, replace the
`[build]`/`[[headers]]` config in `netlify.toml` with a catch-all redirect so old pins keep working and search engines move
their ranking to the new domain:

```toml
[build]
  base = "site"
  publish = "public"
  command = ""

[[redirects]]
  from = "/*"
  to = "https://kitchenfindsfavorites.com/:splat"
  status = 301
  force = true
```
