# SiteStripe product imports (no Amazon API required)

The approved import ledger is `sitestripe.json`. It is empty until an actual SiteStripe link and reviewed product content are available. No example links are live imports.

1. In Amazon while signed into the Associates account, open the exact product/variant and choose SiteStripe > Text > Long Link. Use tracking ID `kitchenfi0fde-20`. This importer requires a long link so it can validate ASIN and tag without visiting Amazon. It cannot generate SiteStripe links or verify the seller by itself.
2. Add a reviewed entry to the ledger. Copy the site's existing product structure: `asin`, `name`, `category`, `subcategory`, `blurb`, `added`, `award`, `graphic` (label, headline, exactly three points), `pin` (title, description, board), `suits`, and `check`.
3. Add `sitestripe_url` unchanged, `approved: true`, exact `variant`, confirmed `seller`, `verified_at` (YYYY-MM-DD), authorized manufacturer `source_url`, `content_rights: "original-editorial-graphic"`, and `editorial_reason`. Use original copy and factual, sourced specifications. Do not copy Amazon images, reviews, ratings or prices. Approval means these checks were actually completed, not merely that the fields are filled.
4. Run `python3 site/import_sitestripe.py site/imports/sitestripe.json` to validate. The entire batch must pass before any write. Existing/live or staged ASINs are rejected.
5. Commit the reviewed ledger to main. The deploy workflow validates and applies the ledger to its temporary catalog, builds original graphics and site output without Amazon API access, pushes the built output to hostinger-deploy and invokes Hostinger's existing webhook. The supplied link is preserved in product buttons, cards, comparisons and the public product feed.

Keep ledger entries across builds: the runner starts from the committed base catalog on every run. If folding an entry into `site/products.json`, remove the same entry from the ledger in that commit. Do not run competing Hostinger cron catalog edits. The public feed is the rendered union; the importer does not commit generated catalog mutations back to main.

The missing-credential Amazon discovery workflow has no automatic daily schedule now. It can still be run manually if API access is granted later. Daily deployment continues through the existing deploy workflow. Product research and SiteStripe link collection require a verified input; this setup does not automatically select five new products or publish social posts.
