# Kitchen Finds & Favorites landing page

Live at https://kitchenfindsfavorites.netlify.app. Netlify deploys `site/public/` from `main` (see `/netlify.toml`).

## Adding a product

1. Append an entry to `products.json` (`asin`, `name`, `category`, `image`, `blurb`, `added`).
   Do **not** add price or star ratings — static Amazon prices/ratings violate the Associates agreement.
2. `python3 build.py` — validates the data and regenerates `public/`.
3. Commit `products.json` and `public/` together and push to `main`.

Each product gets an anchor, so pins link to `https://kitchenfindsfavorites.netlify.app/#<ASIN>`.
The newest 6 products appear under "This Week's Top Picks"; older ones move into their category section.
