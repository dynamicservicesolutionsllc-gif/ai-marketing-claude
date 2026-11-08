# Kitchen Finds & Favorites landing page

Live at https://kitchenfindsfavorites.com, hosted on Hostinger. On every push to `main` that touches `site/public/`, the
`Deploy site to Hostinger` GitHub Action copies `site/public/` to the `hostinger-deploy` branch, then calls Hostinger's
Git auto-deployment webhook, which pulls that branch into `public_html`. The original blank WordPress install was moved
(not deleted) to `~/domains/kitchenfindsfavorites.com/wordpress-backup-2026-10-17/`. The old https://kitchenfindsfavorites.netlify.app 301-redirects every
path to the same path on the new domain (see `/netlify.toml`), so existing pins keep working.

## Adding a product

1. Append an entry to `products.json` (`asin`, `name`, `category`, `subcategory`, `award`, `graphic` {`label`, `headline`, 3 `points`}, `blurb`, `added`, and optionally
   `pin`: `title` ≤100 chars, `description` ≤500 chars starting with `#ad As an Amazon Associate I earn from qualifying purchases.`, `board`).
   Do **not** add price or star ratings — static Amazon prices/ratings violate the Associates agreement.
   Do **not** use Amazon-hosted product photos: Amazon only licenses them through its own tools/API. `graphics.py`
   renders an original square card (`public/img/<ASIN>-sq.png`) and a 1000x1500 pin graphic (`public/img/<ASIN>.png`).
   **Similar-item photos:** `build.py` (or `python site/stock_photos.py` directly) downloads a free Pixabay photo of the same *kind* of item for each
   product that doesn't have one (the same photo the TikTok/YouTube videos use: same product-type table and per-ASIN pick as
   `stock.py` in the video folder) into `assets/products/<ASIN>.jpg`, with credits in `assets/products/photos.json`. Commit both.
   The card, pin graphics and two extra product pins then show that photo, badged "Similar item shown", and the product page
   captions it ("Photo shows a similar …, not this exact product") with a Pixabay credit. The API key is never committed:
   `PIXABAY_API_KEY`, `--key-file PATH`, `site/.pixabay-key` (gitignored), or the video folder's key at
   `~/Documents/claud create/videos/.pixabay-key`; with no key the build just skips this step. `--check` lists products still without a photo;
   a product whose name matches no type in `PRODUCT_TYPES` gets no automatic photo (add a type to fix it).
   **No photo, not published:** `build.py` leaves every product without a photo out of the public build (pages, `products.json`,
   `pins.json`, gift/guide picks and comparisons that name it). Automatic picks are often the wrong item, so check each one by eye;
   ASINs in `assets/products/hold.json` are skipped by the automatic fetch and stay hidden until a photo is hand-picked.
2. `pip install pillow` (once), then `python3 build.py` — validates the data, renders new graphics, and regenerates `public/`.
   `--force-graphics` re-renders every graphic after a design change.
3. Commit `products.json` and `public/` together and get it onto `main` (the GitHub Action deploys it to Hostinger).

Each product gets its own page at `/picks/<slug>/` (slug from the product name), and pins/posts link there.
Each entry in `subcategories` becomes a buying-guide landing page at `/guides/<key>/`: disclosure callout, quick-picks table
(the products' `award` labels), "how we chose" criteria, a section per product, buying guide, FAQ (with FAQPage schema), and
related guides. Optional guide fields: `headline` (search-targeted `<title>`/H1, ≤52 chars; `title` stays on cards, crumbs and pins) and long-form sections: `quick_answer` (callout under the intro), `measure` + `measure_note`
(a "measure these" checklist), `related` (other subcategory keys to list under "Related buying guides" after the same-category ones), `types` (a type comparison table plus "choose / skip it if" lists; each type's optional `pick` is an
ASIN from the same guide) and `reviewed` (YYYY-MM-DD last-reviewed date, shown as "Updated" when newer than the products). A guide may instead hand-pick existing products with `picks` (list of `{asin, award, why}`, like gift guides) to target a cross-category query (e.g. `baking-essentials`); those products keep their home subcategory, and no product may list a picks guide as its subcategory. Each guide has a header photo at `assets/guides/<key>.jpg` (a free-license Unsplash stock photo that shows no branded products; credited on the page) — `build.py` renders WebP/JPEG sizes into `public/img/guides/`. `build.py` rejects a subcategory with no products, a title over 60 characters, or guide copy with prices,
star ratings, or testing claims.
The landing page also keeps a `#<ASIN>` anchor per card, so older pins that link to anchors still work.
The newest 6 products appear under "This Week's Top Picks"; older ones move into their category section.
`build.py` also writes `/subscribe.php` (email sign-up; addresses are appended to `kff-subscribers.csv` one level above `public_html`, never web-readable), `/.htaccess` (HTTPS, CORS for graphics, blocks `.git`), `/privacy/`, `/thanks/` (signup success page), `/404.html`, `/favicon.svg`, the sitemap (every indexable page), and JSON-LD structured data: Organization/WebSite/ItemList on the homepage, CollectionPage on category hubs, BreadcrumbList + Article + ItemList (+ FAQPage) on guides and comparisons, BreadcrumbList on product pages (Home › category › guide › product, same as the visible crumbs), AboutPage/ContactPage. `ld()` rejects Product/Review/Offer markup and any price or rating keys.
Hand-written articles committed straight into `public/` (e.g. `/thanksgiving-prep-plan/`, `/learn/freezer-tray-buying-checklist/`) must be listed in `STATIC_ARTICLES` in `build.py`: the build adds them to the sitemap (lastmod = the page's "Published Month D, YYYY" line) and inserts/refreshes an Article + BreadcrumbList JSON-LD block (plus FAQPage when the page has a "Frequently asked questions" h2 followed by h3 question / p answer pairs) between `<!-- kff:static-ld -->` markers. The page needs an `<h1>`, a meta description and that Published line, or the build stops.
Image loading: each page gives `fetchpriority="high"` to exactly one image, its first visible one (the guide header photo, the product photo, or the first gift/guide tile on the homepage and hubs); a few more above-the-fold images load eagerly and the rest lazy-load.
The site accent is `#ad512b` (light) / `#e07a4f` (dark) so buttons and links meet WCAG AA contrast; the graphics keep their original `#c8643b` orange.

## Compliance rules the build enforces

- The Associates disclosure is in a sticky bar on every page, in the footer, and as "Paid link" under every Amazon button.
- No prices, star ratings, review counts, or Amazon photos (`build.py` rejects them).
- Copy must not imply hands-on testing or personal use ("tested", "we use", …) — `build.py` rejects it.
- Spec claims in blurbs, graphic points, and pins (sizes, hours, temperatures) must match the current Amazon listing.

## Email list rules

The signup form posts to `subscribe.php` on Hostinger, which stores addresses in `~/domains/kitchenfindsfavorites.com/kff-subscribers.csv` (download it from hPanel File Manager). When emails start going out:
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

## Official Amazon product photos (currently inactive)

The current Hostinger deployment workflow builds offline and does not call Amazon's Creators API. Product photos in site/social creatives must follow the rights checks described in the product-import guide. The separate `Amazon Creators API discovery` workflow can queue up to one candidate ASIN per run when eligible Creators API credentials are stored in GitHub Actions secrets; it does not fetch photos, write to `products.json`, or publish products. Any Amazon Product Advertising Content returned by the API must be used only within the scope of Amazon's license and for the site. The API credentials are never committed to the repository.

## Holiday gift guides

`gift_guides` in `products.json` → pages at `/gifts/<key>/` (listed first on the homepage). Each guide hand-picks existing
products by ASIN with its own `award` and `why` (gift note). Same rules as buying guides: no prices, star ratings, price
claims ("under $25") or testing claims — `build.py` rejects them. Header photos live in `assets/guides/<key>.jpg`. Each gift guide links to the buying guides its picks come from, and each buying guide links to the gift guides that feature its picks.

## Pinterest queue (`/pins.json`)

`pins.py` (run by `build.py`) gives every page several distinct pins, because Pinterest rewards fresh pins even to the
same page: 4 photo designs per buying/gift guide (photo-top, dark, colour + checklist, big-number) and, per product, the
original pin plus a dark and a colour design (the colour one links to the product's section in its guide). Images go to
`public/img/pins/<id>.jpg`; links carry `utm_source=pinterest&utm_campaign=<pin id>`. Queue order: each page's lead pin
first (gift guides, then guides, then products), then the remaining variants. The Pinterest routine (twice daily) publishes the
first unposted ids, ramping from 5/day to 12/day by Nov 9 (see routines/pinterest-pinning.md for the schedule and
back-off rule; never the same page twice in a day). Guide pins go to keyword boards set per subcategory (`board`). A guide's optional `pin_keywords` (2–4 Pinterest search phrases, ≤40 chars each) lead its "how to choose" pin title and close every guide pin description ("Save for later: …"); the guide pin's main title uses the search-targeted `headline` when set. Pin ids, order, images, links and boards don't change. `--force-graphics` re-renders pin images.

## Click tracking

Every Amazon link click sends a GA4 `amazon_click` event (asin, placement, channel, link_page) and a beacon to
`/click.php`, which appends `time, page, ASIN, channel, placement, pin/campaign` to `public_html/.data/clicks.csv`
(blocked from the web by `.htaccess`; no IP, cookies or personal data). Channel comes from `utm_source` (kept for the
visit) or the referrer. If `site.channel_tags` has a tracking ID for a channel (e.g. `"pinterest": "kitchenfi-pin-20"`),
links clicked during that visit use it, so Associates reports split sales by channel. Create the IDs in Associates
Central → Manage Your Tracking IDs first; leave a channel empty to keep the main tag.

## Email printable

`printables.py` generates `assets/printables/small-kitchen-measuring-checklist.pdf` (no Amazon links — not allowed in
downloadable files). The sign-up box offers it and `/thanks/` links to it.
