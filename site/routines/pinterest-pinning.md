You are continuing Frank's Amazon Associates + Pinterest affiliate marketing automation for his Pinterest business account "kitchenfindsfavorites" (Kitchen Finds & Favorites). This is the daily evening pinning run. Pinterest is the main traffic engine for this site, so steady daily volume matters.

STRATEGY (confirmed by Frank 2026-10-12, updated 2026-10-18): pins link to the site https://kitchenfindsfavorites.com so Frank owns the audience (email signup) — NEVER directly to Amazon. The site links out to Amazon with tag kitchenfi0fde-20. Every page (buying guides, holiday gift guides and products) has 3–4 different pins — different image, headline and title — because Pinterest rewards fresh pins even when they lead to the same page. The site generates them all; this run only publishes them.

COMPLIANCE (Amazon Associates policies — see project doc `claude/compliance-checklist.md`):
- Never download or upload Amazon product photos. Use only the pin image the queue gives you (`image`): original graphics or licensed stock photos hosted on kitchenfindsfavorites.com.
- No prices, star ratings, review counts, or "#1 best seller" claims in pin titles/descriptions. Use the queue's title and description as written.
- Every description starts with "#ad As an Amazon Associate I earn from qualifying purchases." (the queue already does).

This session is attached to the "amzon associate" Claude project. First read the project docs `claude/pinterest-posting-automation.md` (description-field editing technique, board names, the "Posted Pins Log", excluded-ASIN list) and `claude/compliance-checklist.md`. Where the playbook says to link pins to Amazon, pick products yourself, use products.json as the queue, or extract Amazon images, THIS prompt supersedes it.

Per run:
1. In the linked computer's browser, open https://kitchenfindsfavorites.com/pins.json. It is the queue, already in priority order (`order`). Each entry has: id, kind (gift | guide | product), page (guide key or ASIN), page_url, link (page URL with UTM tags — use this as the pin's destination), image (1000x1500), title, description, board.
2. Take the first entries, in `order`, whose `id` is NOT in the Posted Pins Log (older log rows use the ASIN as the id; they match the queue's product entries whose id is the ASIN). Take up to 5, and never two entries with the same `page` in one run (skip to the next entry instead). If nothing is left, log "queue empty" under Run notes and stop (normal skip).
3. For each queued pin:
   a. If kind is "product": open https://www.amazon.com/dp/<page> and confirm via SiteStripe "Get Link" that it is not an Associates-excluded product and is still available. Verify with a screenshot of the SiteStripe flyout (real category + commission rate), not a text search. If it is excluded: add it to the excluded-ASIN list in the playbook, create a Google Doc titled exactly "KFF site removal request - <ASIN>" (body: the reason) so the morning routine removes it from the site, and skip it. Gift and guide pins link to the site's own guide pages and need no SiteStripe check.
   b. Open page_url and confirm it loads on the live site. If not, skip it (retried next run).
   c. Create and publish the pin: image = `image` (fetch it into a File/DataTransfer and dispatch `change` on Pinterest's file input); title and description exactly as given; board = `board` (create the board if it doesn't exist yet — e.g. "Kitchen Gift Ideas for Home Cooks" for gift pins); destination link = `link`. Verify every field by screenshot before publishing. Before you click Publish, the destination link field MUST start with https://kitchenfindsfavorites.com/ — if it is empty, an amazon.com/amzn.to link, or anything else, fix it to `link`; never publish a pin that links to Amazon.
   d. Append a row to the Posted Pins Log in `claude/pinterest-posting-automation.md`: date, pin id, title, board, destination (`link`).
4. Space pins at least 2–3 minutes apart. If Pinterest shows a rate-limit or spam warning, stop for this run and note it under Run notes.

If the computer/browser isn't reachable or Pinterest errors out repeatedly, do NOT force a bad post: log it under "Run notes" and stop. Do not touch Amazon Associates tax information — that is Frank's own task, never automate it.

Only message Frank if something needs his attention (computer unreachable for multiple runs in a row, the queue has been empty for 2+ runs, or a rate-limit/spam warning appeared).
