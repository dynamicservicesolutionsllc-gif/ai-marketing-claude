# Kitchen Finds & Favorites landing page

Live at https://kitchenfindsfavorites.netlify.app. Netlify deploys `site/public/` from `main` (see `/netlify.toml`).

## Adding a product

1. Append an entry to `products.json` (`asin`, `name`, `category`, `graphic` {`label`, `headline`, 3 `points`}, `blurb`, `added`, and optionally
   `pin`: `title` ≤100 chars, `description` ≤500 chars starting with `#ad As an Amazon Associate I earn from qualifying purchases.`, `board`).
   Do **not** add price or star ratings — static Amazon prices/ratings violate the Associates agreement.
   Do **not** use Amazon-hosted product photos: Amazon only licenses them through its own tools/API. `graphics.py`
   renders an original square card (`public/img/<ASIN>-sq.png`) and a 1000x1500 pin graphic (`public/img/<ASIN>.png`).
2. `pip install pillow` (once), then `python3 build.py` — validates the data, renders new graphics, and regenerates `public/`.
   `--force-graphics` re-renders every graphic after a design change.
3. Commit `products.json` and `public/` together and get it onto `main` (Netlify deploys from `main`).

Each product gets its own page at `/picks/<slug>/` (slug from the product name), and pins/posts link there.
The landing page also keeps a `#<ASIN>` anchor per card, so older pins that link to anchors still work.
The newest 6 products appear under "This Week's Top Picks"; older ones move into their category section.
`build.py` also writes `/privacy/`, `/favicon.svg`, the sitemap (every page), and JSON-LD structured data.

## Compliance rules the build enforces

- The Associates disclosure is in a sticky bar on every page, in the footer, and as "Paid link" under every Amazon button.
- No prices, star ratings, review counts, or Amazon photos (`build.py` rejects them).
- Copy must not imply hands-on testing or personal use ("tested", "we use", …) — `build.py` rejects it.
- Spec claims in blurbs, graphic points, and pins (sizes, hours, temperatures) must match the current Amazon listing.

## Email list rules

The signup form collects addresses through Netlify Forms. When emails start going out:
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
