# Kitchen Finds & Favorites landing page

Live at https://kitchenfindsfavorites.netlify.app. Netlify deploys `site/public/` from `main` (see `/netlify.toml`).

## Adding a product

1. Append an entry to `products.json` (`asin`, `name`, `category`, `image`, `blurb`, `added`, and optionally
   `pin`: `title` ≤100 chars, `description` ≤500 chars starting with `#ad As an Amazon Associate I earn from qualifying purchases.`, `board`).
   Do **not** add price or star ratings — static Amazon prices/ratings violate the Associates agreement.
2. `python3 build.py` — validates the data and regenerates `public/`.
3. Commit `products.json` and `public/` together and get it onto `main` (Netlify deploys from `main`).

Each product gets an anchor, so pins link to `https://kitchenfindsfavorites.netlify.app/#<ASIN>`.
The newest 6 products appear under "This Week's Top Picks"; older ones move into their category section.

## Routine handoff

`build.py` also publishes `public/products.json` (live at `/products.json`). The Pinterest posting routine reads it as its queue
and pins any ASIN not yet in its Posted Pins Log. To pull a product (e.g. it turns out Associates-excluded), the Pinterest
routine creates a Google Doc titled `KFF site removal request - <ASIN>`; the daily site routine removes the product and trashes the doc.

Routine prompts are versioned in `routines/`.
