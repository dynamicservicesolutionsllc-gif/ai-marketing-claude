# Product discovery and import coordination

GitHub main is the source of truth. Hostinger serves the hostinger-deploy branch. Do not run a second Hostinger cron that independently edits the live catalog: those changes can be overwritten by deployment.

## Daily discovery

`.github/workflows/discover-products.yml` runs daily at 13:47 UTC and can be dispatched manually. It tests duplicate protection, validates the presence of Amazon Actions secrets, then discovers up to five new ASINs into `marketing-queue/product-candidates.json`. It excludes ASINs already in the live catalog, staging section, or durable queue. Only ASINs and our research metadata are committed; API titles, images, prices and offers are not persisted in this queue. Search position does not establish conversion likelihood.

Configure repository Actions secrets `AMAZON_CREATORS_CLIENT_ID` and `AMAZON_CREATORS_CLIENT_SECRET`. Optional Actions variable `AMAZON_CREDENTIAL_VERSION` defaults to 3.1 (North America). Never put credentials in issues, commits, reports or chat.

First CI run 42340349346 passed request-contract and duplicate-protection tests, then stopped at missing Amazon configuration. No live import was attempted. Credential presence and actual API authorization must be verified with a successful run before calling discovery operational.

## Publication

A discovered ASIN is a research candidate, not an approved product. Verify exact model, variant, seller/offer, current eligibility, existing-site duplication and product fit. Complete original editorial content, disclosures and licensed/original graphics. Only reviewed entries should enter `site/products.json`; rebuild `site/public` and commit the reviewed output to main. The existing deployment workflow publishes that output to Hostinger. Its current build step is conditional on Amazon credentials, so catalog-only commits are insufficient when that step is skipped.

This discovery workflow does not yet implement automatic promotion of candidates into the live catalog, social posting, or a replacement scheduler. Those remain separate integrations.

## Existing scheduler cleanup pending sign-in

- Remove only the paused duplicate `Pinterest Affiliate Pin Posting (Twice Daily) — on Frank's computer` after verifying its identity. Keep the active Pinterest task.
- Facebook saved prompt must use the current `site/routines/facebook-posting.md`: five runs daily, seven days weekly.
- Video saved prompt must use current `site/routines/short-videos.md` and preserve per-platform publishing history. YouTube freezer checklist WHUQ3J7nsGk is already published.
