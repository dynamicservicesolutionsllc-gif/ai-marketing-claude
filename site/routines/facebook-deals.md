Facebook deal-group run for the Amazon affiliate site "Kitchen Finds & Favorites" (https://kitchenfindsfavorites.com). Facebook identity (updated 2026-11-03): Chrome's Facebook session acts as the Kitchen Finds & Favorites Page itself (https://www.facebook.com/1433493846508656), which Richard Tracy manages; the old Page 61594030243560 is gone. All posting, joining, replies and Reels happen as that Page. At the start of the run open facebook.com and check the active identity (top-right avatar/name): if it shows Richard Tracy, switch to the Kitchen Finds & Favorites Page from the profile menu; if the Page can't be selected, stop and report. Groups in the log were joined by Richard's old profile, so if a group shows "Join" for the Page, join it as the Page (same rules as new joins) and post only once it is joined or approved. Richard asked for this on 2026-10-30: post in Facebook deal groups three times a day (morning, midday, night) and join 5 new deal groups a day. Rewritten 2026-11-13 at Richard's request to follow the Amazon Associates Program Policies (updated April 14, 2026): posts now share the site's own product and guide pages, with no prices, no discount or deal claims, and no direct Amazon links. The goal is the first 3 qualifying Amazon Associates sales without getting the Page flagged for spam.

This is separate from the guide-posting routine (facebook-groups.md, kitchen/home groups). Both routines now link only to kitchenfindsfavorites.com. This one posts in groups made for deals and finds (name or About mentions deals, finds, codes, coupons or savings) whose rules allow links.

AMAZON POLICY RULES (these outrank everything below; when in doubt, leave it out):
- Never state a price, list price, percent off, savings amount, coupon, "deal", "sale", "Lightning Deal", "price drop", "lowest price" or stock status, in posts or in replies. Prices and availability may be shown only through Amazon's API, which this account does not have. Limited-time offers must be taken down the moment they end, so this routine does not mention them at all.
- Never state star ratings, review counts or "best seller" claims.
- Never post an amazon.com, amzn.to or a.co link in a group or a reply. Tagged Amazon links belong on the site and on the Page's own posts, not in groups other people own. Link only to kitchenfindsfavorites.com pages.
- Do not open amazon.com in this routine at all. Everything the posts need is in the site's own product feed.
- Never say or imply that Richard or the site tested, owns or uses a product.
- Never pay to boost or promote any of these posts.

Tools: Claude in Chrome (mcp__claude-in-chrome__*, load with ToolSearch in one call). If Chrome isn't connected or Facebook isn't signed in, stop and report it. Never type passwords.

Log: C:\Users\office\OneDrive\Documents\claud create\kff-facebook-deals-log.md (Groups table, Posts table, Run notes). Read it first. Edit it with Edit/Write, not shell redirection (OneDrive can drop shell writes).

Which run this is: morning (before 11 AM local), midday (11 AM–4 PM) or night (after 4 PM). Only the MORNING run joins new groups.

HARD LIMITS (never exceed):
- Morning run only: join at most 5 new groups.
- Each group gets at most 1 post per run and at most 3 posts per day (one per run). A group whose rules limit posts per day gets fewer, as its rules say.
- At most 10 group posts per run. Wait at least 2 minutes between posts.
- Never post the same item in the same group within 3 days. Never post the same item in more than 4 groups per run, and vary the wording between groups (reorder sentences, different opening) so posts aren't identical.
- Never answer participation questions or accept a group's rules agreement. If a join pops up questions or an agreement, close it without answering, mark the group "needs Richard" in the log and move on. Never comment on others' posts, send messages or friend requests, or collect anyone's personal information.
- Stop the whole run immediately if Facebook shows any warning: posting limited, "you're posting too fast", "we removed your post", a checkpoint, a restriction notice, a spam warning or a CAPTCHA. Log the exact wording under Run notes and report it. Don't retry later in the same run.
- Never post in "Kitchen Stuff" (groups/yourkitchenstuff) or any group whose rules ban links, affiliate links or self-promotion. If a post is removed by a group's admins, mark that group "do not post".

0. REPLY TO COMMENTS (every run, before anything else). Richard asked on 2026-10-30 for comments on his posts to be answered automatically. Open https://www.facebook.com/notifications and look for comments and replies on the Page's own posts and Reels from the last 24 hours. For each one not already in the log's Replies table:
   - Reply in the comment thread under the Page's post, as the Page, within the same post only. Never send DMs/Messenger messages, never comment on other people's posts, never send friend requests.
   - Product questions (size, capacity, compatibility, what's included, how it works): answer in 1–2 short, friendly sentences using only facts from that product's page on kitchenfindsfavorites.com. If the page doesn't answer it, say the full details are on the product page and give its link.
   - Price, deal or stock questions ("how much?", "is it still on sale?", "is it in stock?"): never quote a number or a deal status. Reply along the lines of "Prices change often, so the product page has a button that shows the current price on Amazon:" followed by the site page link.
   - When a commenter asks where to get it or asks for the link, give the kitchenfindsfavorites.com page link (page_url + ?utm_source=facebook&utm_medium=social&utm_campaign=reply) and end with "#ad As an Amazon Associate I earn from qualifying purchases."
   - Simple positive comments ("nice", "thanks", "ordered!"): a short thank-you, no link.
   - Anything else (complaints, arguments, personal or medical/safety questions, anything mentioning a problem with an order, rude or spam comments, anything you're unsure of): do NOT reply. List it in the report for Richard.
   - Never claim Richard owns or used the product, never promise anything, never ask anyone to buy.
   - At most 15 replies per run, 30+ seconds apart. Record each in the Replies table: date, post/group, commenter's first name, comment (short), reply (short).

0b. CLEAN UP OLD DEAL POSTS (every run until none are left, up to 10 per run, 30+ seconds apart). Posts made before 2026-11-13 state prices and limited-time deals and link straight to Amazon. Go through the log's Posts table, oldest first, for rows not yet marked "removed". Open the group, find the Page's own post, and delete it (post menu → Delete post / Move to trash). Delete only posts made by the Page itself. If the post is already gone or can't be found, mark the row "not found". Mark each handled row "removed" with the date. When no rows remain, note "cleanup complete" in Run notes and skip this step from then on.

1. JOIN NEW GROUPS (morning run only, up to 5): search Facebook groups (https://www.facebook.com/search/groups/?q=...) for terms such as "amazon deals", "amazon lightning deals", "kitchen deals", "home deals", "black friday deals", "deals and steals", "coupon deals usa", "holiday deals". Join only groups that are public, United States based (skip Canada/UK groups), have 1,000+ members (prefer 10K+), show posts within the last day, and are about deals. Open the group's About page and read its rules before posting; skip groups that ban links or affiliate posts or require a fee. Record name, URL, members, rules summary and status (joined / pending approval / needs Richard / do not post) in the Groups table.

2. CHOOSE CONTENT (3–5 items per run). Read https://kitchenfindsfavorites.com/products.json?nocache=<random> (fields: asin, name, blurb, suits, check, subcategory, added, page_url, pin_image). Do not open Amazon. Pick, in this order:
   - products added in the last 3 days;
   - until Dec 1: the Black Friday kitchen gift list https://kitchenfindsfavorites.com/gifts/black-friday-kitchen-gifts/ and the other gift guides under /gifts/ (describe them as gift ideas, never as deals or discounts);
   - buying guides at https://kitchenfindsfavorites.com/guides/<subcategory>/ for the subcategories with the most products;
   - older products, least recently posted first.
   Favor small, giftable, everyday items (gadgets, utensils, storage, small organizers, stocking stuffers); at most 1 item per run should be a larger appliance. Skip any item whose page returns an error.

3. POST: for each group with status joined or approved (fewest posts today first), until the per-run cap, post one item that group hasn't had in 3 days:
   - First line: "#ad As an Amazon Associate I earn from qualifying purchases."
   - Then 2–3 honest sentences in plain, friendly language drawn only from the page's own copy (name, blurb, suits, check): what it is, who it suits, and what to check before buying. Follow the AMAZON POLICY RULES above: no prices, discounts, deal or stock claims, ratings, review counts, "best seller", or "I tried/I use".
   - Close with a line such as "Details and a link to check the current price on Amazon are on the page:" followed by the link.
   - Link: the item's page_url (or guide URL) + ?utm_source=facebook&utm_medium=social&utm_campaign=dealgroup-<asin or guide key>. Only kitchenfindsfavorites.com links.
   - Let Facebook's link preview attach the site's own image. Post, then confirm it shows as posted or "submitted for approval". Record it in the Posts table: date, time, run (morning/midday/night), group, ASIN or guide, page, status (live / pending).
   - If a group's rules allow only posts that state a price or a discount, mark it "do not post" in the Groups table and move on; do not bend the rules above to fit a group.
   Facebook's composer: click the "Write something..." button, wait, type, wait ~4s for the link preview, click "Post". A group welcome popup can swallow typing; press Escape and re-open the composer if the text didn't land.

4. Finish with a short report: groups joined (and any "needs Richard" with their questions), posts made (group, item, live or pending), old deal posts removed and how many remain, anything skipped and why, and any Facebook warning.
