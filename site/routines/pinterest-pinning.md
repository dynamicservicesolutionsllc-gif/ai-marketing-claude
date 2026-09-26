You are continuing Frank's Amazon Associates + Pinterest affiliate marketing automation for his Pinterest business account "kitchenfindsfavorites" (Kitchen Finds & Favorites). This is the daily evening pinning run.

STRATEGY (since 2026-09-22): pins link to the landing page https://kitchenfindsfavorites.netlify.app — NEVER directly to Amazon. The landing page links out to Amazon with tag kitchenfi0fde-20. Products are chosen and added to the site every morning by a separate cloud routine; this run only pins what is already live on the site.

This session is attached to the "amzon associate " Claude project. First read the project doc `claude/pinterest-posting-automation.md` — the playbook for image-extraction and description-field editing techniques, board names, disclosure wording, the "Posted Pins Log", and the excluded-ASIN list. Where the playbook says to link pins to Amazon or to pick products yourself, THIS prompt supersedes it.

Per run:
1. In the linked computer's browser, open https://kitchenfindsfavorites.netlify.app/products.json. It lists every product on the site with asin, name, image, page_url (the landing-page anchor, e.g. https://kitchenfindsfavorites.netlify.app/#B07SRV3SN8), amazon_url, and usually a ready-made pin {title, description, board}.
2. The queue = products whose ASIN is NOT in the Posted Pins Log, oldest "added" first. Take up to 5. If the queue is empty, log "queue empty" under Run notes and stop (normal skip).
3. For each queued product:
   a. Open its Amazon page and confirm via SiteStripe "Get Link" that it is not an Associates-excluded product and is still available. If it is excluded: add it to the excluded-ASIN list in the playbook, create a Google Doc in Google Drive titled exactly "KFF site removal request - <ASIN>" (body: the reason) so the morning routine removes it from the site, and skip it.
   b. Open its page_url and confirm the product card is visible on the live site. If not, skip it (it will be retried next run).
   c. Create and publish the pin: image = the product's main image (use the playbook's extraction technique if the feed image won't upload); title and description from the feed's pin fields if present, otherwise write them (description MUST start with "#ad As an Amazon Associate I earn from qualifying purchases." then 2–3 genuine sentences and 2–3 hashtags); destination link = page_url (NOT the Amazon link); board = the feed's pin.board or the best-fitting existing board.
   d. Append a row to the Posted Pins Log in `claude/pinterest-posting-automation.md`: date, product, ASIN, board, pin destination (page_url), compliance verdict.
4. Space pins at least a couple of minutes apart; if Pinterest shows a rate-limit or spam warning, stop for this run and note it under Run notes.

If the computer/browser isn't reachable or Pinterest errors out repeatedly, do NOT force a bad post: log it under "Run notes" and stop. Do not touch Amazon Associates tax information — that is Frank's own task, never automate it.

Only message Frank if something needs his attention (computer unreachable for multiple runs in a row, the queue has been empty for 2+ runs, or a rate-limit/spam warning appeared).
