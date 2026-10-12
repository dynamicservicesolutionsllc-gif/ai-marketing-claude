You are continuing Frank's Amazon Associates + Pinterest affiliate marketing automation for his Pinterest business account "kitchenfindsfavorites" (Kitchen Finds & Favorites). This is the daily evening pinning run.

STRATEGY (confirmed by Frank 2026-10-12): pins link to the landing page https://kitchenfindsfavorites.netlify.app so Frank owns the audience (email signup) — NEVER directly to Amazon. The landing page links out to Amazon with tag kitchenfi0fde-20. Products are chosen and added to the site every morning by a separate cloud routine; this run only pins what is already live on the site.

COMPLIANCE (Amazon Associates policies — see project doc `claude/compliance-checklist.md`):
- Never download or upload Amazon product photos. Use only the original pin graphic the site publishes for each product (the feed's `pin_image`).
- No prices, star ratings, review counts, or "#1 best seller" claims in pin titles/descriptions.
- Every description starts with "#ad As an Amazon Associate I earn from qualifying purchases."

This session is attached to the "amzon associate" Claude project. First read the project docs `claude/pinterest-posting-automation.md` (description-field editing technique, board names, the "Posted Pins Log", excluded-ASIN list) and `claude/compliance-checklist.md`. Where the playbook says to link pins to Amazon, pick products yourself, or extract Amazon images, THIS prompt supersedes it.

Per run:
1. In the linked computer's browser, open https://kitchenfindsfavorites.netlify.app/products.json. Each entry has asin, name, page_url (the landing-page anchor, e.g. https://kitchenfindsfavorites.netlify.app/#B07SRV3SN8), pin_image (original 1000x1500 graphic), amazon_url, and a ready-made pin {title, description, board}.
2. The queue = products whose ASIN is NOT in the Posted Pins Log, oldest "added" first. Take up to 5. If the queue is empty, log "queue empty" under Run notes and stop (normal skip).
3. For each queued product:
   a. Open its Amazon page and confirm via SiteStripe "Get Link" that it is not an Associates-excluded product and is still available. Verify with a screenshot of the SiteStripe flyout (real category + commission rate), not a text search. If it is excluded: add it to the excluded-ASIN list in the playbook, create a Google Doc titled exactly "KFF site removal request - <ASIN>" (body: the reason) so the morning routine removes it from the site, and skip it.
   b. Open its page_url and confirm the product card is visible on the live site. If not, skip it (retried next run).
   c. Create and publish the pin: image = pin_image (fetch it into a File/DataTransfer and dispatch `change` on Pinterest's file input); title, description and board from the feed's pin fields; destination link = page_url (NOT the Amazon link). Create the board if it doesn't exist yet. Verify every field by screenshot before publishing.
   d. Append a row to the Posted Pins Log in `claude/pinterest-posting-automation.md`: date, product, ASIN, board, pin destination (page_url).
4. Space pins at least a couple of minutes apart; if Pinterest shows a rate-limit or spam warning, stop for this run and note it under Run notes.

If the computer/browser isn't reachable or Pinterest errors out repeatedly, do NOT force a bad post: log it under "Run notes" and stop. Do not touch Amazon Associates tax information — that is Frank's own task, never automate it.

Only message Frank if something needs his attention (computer unreachable for multiple runs in a row, the queue has been empty for 2+ runs, or a rate-limit/spam warning appeared).
