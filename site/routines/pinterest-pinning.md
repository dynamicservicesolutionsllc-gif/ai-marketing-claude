You are continuing Frank's Amazon Associates + Pinterest affiliate marketing automation for his Pinterest business account "kitchenfindsfavorites" (Kitchen Finds & Favorites). This task runs twice a day (about 11:17 AM and 8:17 PM ET). Pinterest is the main traffic engine for this site, so steady daily volume matters, but the account is new: volume ramps up gradually to avoid Pinterest's spam limits.

STRATEGY (confirmed by Frank 2026-10-12, updated 2026-10-18): pins link to the site https://kitchenfindsfavorites.com so Frank owns the audience (email signup) — NEVER directly to Amazon. The site links out to Amazon with tag kitchenfi0fde-20. Every page (buying guides, holiday gift guides and products) has 3–4 different pins — different image, headline and title — because Pinterest rewards fresh pins even when they lead to the same page. The site generates them all; this run only publishes them.

COMPLIANCE (Amazon Associates policies — see project doc `claude/compliance-checklist.md`):
- Never download or upload Amazon product photos. Use only the pin image the queue gives you (`image`): original graphics or licensed stock photos hosted on kitchenfindsfavorites.com.
- No prices, star ratings, review counts, or "#1 best seller" claims in pin titles/descriptions. Use the queue's title and description as written.
- Every description starts with "#ad As an Amazon Associate I earn from qualifying purchases." (the queue already does).

This session is attached to the "amzon associate" Claude project. First read the project docs `claude/pinterest-posting-automation.md` (description-field editing technique, board names, the "Posted Pins Log", excluded-ASIN list) and `claude/compliance-checklist.md`. Where the playbook says to link pins to Amazon, pick products yourself, use products.json as the queue, or extract Amazon images, THIS prompt supersedes it.

PACING (confirmed by Frank 2026-10-18). Use today's date and this run's time in America/New_York:
- Through Oct 25, 2026: evening run only, up to 5 pins. A morning run before Oct 26 stops right away (normal skip, no Run notes entry needed).
- Oct 26 – Nov 1: up to 4 pins per run (morning + evening = 8/day).
- Nov 2 – Nov 8: up to 5 pins per run (10/day).
- From Nov 9: up to 6 pins per run (12/day).
- Back-off: if the Run notes record a Pinterest rate-limit or spam warning in the last 3 days, use the previous step's cap (never below 3) and say so in Run notes. After 3 clean days, return to the schedule.

BOARDS: use the queue's `board`. If it doesn't exist yet, create it once with that exact name, public, with this description:
- Pantry Organization Ideas: "Pantry and spice organization ideas for small kitchens: airtight containers, can racks, turntables and spice racks."
- Under Sink Organization: "Under-sink organizer ideas: pull-out shelves that fit around pipes, leak mats and sink caddies."
- Small Kitchen Storage Ideas: "Small kitchen storage ideas: drawer organizers, dish racks and pot and lid organizers that fit tight spaces."
- Coffee Bar Ideas: "Coffee and tea at home: milk frothers, electric kettles and coffee bar ideas for small kitchens."
- Holiday Gift Ideas for Cooks: "Practical holiday gift ideas for home cooks: stocking stuffers, first-apartment kitchen gifts and useful tools."
Don't create any other new boards.

Per run:
1. In the linked computer's browser, open https://kitchenfindsfavorites.com/pins.json. It is the queue, already in priority order (`order`). If pins.json returns 404 (the update isn't merged yet), use https://kitchenfindsfavorites.com/products.json instead for this run: queue = products whose ASIN isn't in the log, oldest `added` first, image = pin_image, title/description/board from each product's pin, link = page_url. Each entry has: id, kind (gift | guide | product), page (guide key or ASIN), page_url, link (page URL with UTM tags — use this as the pin's destination), image (1000x1500), title, description, board.
2. Take the first entries, in `order`, whose `id` is NOT in the Posted Pins Log (older log rows use the ASIN as the id; they match the queue's product entries whose id is the ASIN). Take up to this run's cap (see PACING), never two entries with the same `page` in one run, and skip pages already pinned earlier today (check the log's dates); skip to the next entry instead. If nothing is left, log "queue empty" under Run notes and stop (normal skip).
3. For each queued pin:
   a. If kind is "product": open https://www.amazon.com/dp/<page> and confirm via SiteStripe "Get Link" that it is not an Associates-excluded product and is still available. Verify with a screenshot of the SiteStripe flyout (real category + commission rate), not a text search. If it is excluded: add it to the excluded-ASIN list in the playbook, create a Google Doc titled exactly "KFF site removal request - <ASIN>" (body: the reason) so the morning routine removes it from the site, and skip it. Gift and guide pins link to the site's own guide pages and need no SiteStripe check.
   b. Open page_url and confirm it loads on the live site. If not, skip it (retried next run).
   c. Create and publish the pin: image = `image` (fetch it into a File/DataTransfer and dispatch `change` on Pinterest's file input); title and description exactly as given; board = `board` (if it doesn't exist yet, create it as described under BOARDS); destination link = `link`. Verify every field by screenshot before publishing. Before you click Publish, the destination link field MUST start with https://kitchenfindsfavorites.com/ — if it is empty, an amazon.com/amzn.to link, or anything else, fix it to `link`; never publish a pin that links to Amazon.
   d. Append a row to the Posted Pins Log in `claude/pinterest-posting-automation.md`: date, pin id, title, board, destination (`link`).
4. Space pins at least 3 minutes apart. If Pinterest shows a rate-limit or spam warning, stop for this run and note it under Run notes with the date (the back-off rule uses it).

If the computer/browser isn't reachable or Pinterest errors out repeatedly, do NOT force a bad post: log it under "Run notes" and stop. Do not touch Amazon Associates tax information — that is Frank's own task, never automate it.

Only message Frank if something needs his attention (computer unreachable for multiple runs in a row, the queue has been empty for 2+ runs, or a rate-limit/spam warning appeared).
