You are continuing Frank's Amazon Associates + Facebook affiliate marketing automation for his Facebook Page "Kitchen Finds & Favorites" (https://www.facebook.com/61594030243560). This is a recurring posting run — Mon/Wed/Fri/Sun evenings, ~8:30pm ET.

STRATEGY (confirmed by Frank 2026-10-12): posts link to the landing page https://kitchenfindsfavorites.com so Frank owns the audience — NOT directly to Amazon. The landing page links out to Amazon with tag kitchenfi0fde-20. This run only posts products that are already live on the site.

COMPLIANCE (Amazon Associates policies — see project doc `claude/compliance-checklist.md`):
- Never attach Amazon product photos. Attach only the site's original graphic for the product (the feed's `pin_image`).
- No prices, star ratings, review counts, or "#1 best seller" claims. Never boost/promote these posts with paid ads.
- Post copy starts with "#ad As an Amazon Associate I earn from qualifying purchases."

This session is attached to the "amzon associate" Claude project. First read `claude/facebook-page-setup.md` (composer technique, publish verification via the Content Library, Posted Log) and `claude/compliance-checklist.md`. Where the playbook says to link to Amazon or extract Amazon images, THIS prompt supersedes it.

Per run:
1. In the linked computer's browser, open https://kitchenfindsfavorites.com/products.json. Pick ONE product whose ASIN is not in the Facebook Posted Log, oldest "added" first; prefer one already pinned on Pinterest (its eligibility is confirmed).
2. Confirm Associates eligibility via a SiteStripe screenshot on its Amazon page (real category + commission rate). If excluded, skip it and pick the next one.
3. Open the Page's real post composer ("What's on your mind?" — NOT the "Share a thought..." note bubble). Write: the disclosure sentence, 2–3 genuine sentences about the product, the product's page_url followed by ?utm_source=facebook&utm_medium=social&utm_campaign=<ASIN> on its own line (so clicks are attributed to Facebook), then 2–3 hashtags. The only link in the post is that kitchenfindsfavorites.com link — never an amazon.com or amzn.to link. Attach pin_image via an in-page <img crossOrigin> → canvas → Blob/File → file-input `change` (the technique in the playbook). Publish publicly.
4. Verify it published in https://www.facebook.com/professional_dashboard/content/content_library/ before logging. A "Speak With People Directly" promo dialog after posting is normal — dismiss with "Not now."
5. Append a row to the Posted Log in `claude/facebook-page-setup.md` (date, product, ASIN, link = the UTM-tagged page_url) and a short Run notes entry.

If the computer/browser isn't reachable or posting fails repeatedly, do NOT force a bad post: log it under "Run notes" and stop. Do not touch Amazon Associates tax or payment settings. Do not delete any post.

Only message Frank if something needs his attention (computer unreachable for multiple runs in a row, or no un-posted products left).
