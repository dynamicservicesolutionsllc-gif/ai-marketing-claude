Facebook deal-group run for the Amazon affiliate site "Kitchen Finds & Favorites" (https://kitchenfindsfavorites.com). Chrome is signed in to the personal Facebook profile "Richard Tracy", which posts in deal groups. Richard asked for this on 2026-10-30: post verified Amazon kitchen/home deals (Lightning Deals first) in Facebook deal groups three times a day (morning, midday, night) and join 5 new deal groups a day. The goal is the first 3 qualifying Amazon Associates sales without getting the profile flagged for spam.

This is separate from the guide-posting routine (facebook-groups.md, kitchen/home groups, site links only). This routine posts direct, tagged Amazon product links, so it only posts in groups made for deals (name or About mentions deals, finds, codes, coupons or savings) whose rules allow Amazon links.

Tools: Claude in Chrome (mcp__claude-in-chrome__*, load with ToolSearch in one call). If Chrome isn't connected or Facebook/Amazon isn't signed in, stop and report it. Never type passwords.

Log: C:\Users\office\OneDrive\Documents\claud create\kff-facebook-deals-log.md (Groups table, Posts table, Run notes). Read it first. Edit it with Edit/Write, not shell redirection (OneDrive can drop shell writes).

Which run this is: morning (before 11 AM local), midday (11 AM–4 PM) or night (after 4 PM). Only the MORNING run joins new groups.

HARD LIMITS (never exceed):
- Morning run only: join at most 5 new groups.
- Each group gets at most 1 post per run and at most 3 posts per day (one per run). A group whose rules limit posts per day gets fewer, as its rules say.
- At most 10 group posts per run. Wait at least 2 minutes between posts.
- Never post the same ASIN in the same group within 3 days. Never post the same ASIN in more than 4 groups per run, and vary the wording between groups (reorder sentences, different opening) so posts aren't identical.
- Never answer participation questions or accept a group's rules agreement. If a join pops up questions or an agreement, close it without answering, mark the group "needs Richard" in the log and move on. Never comment on others' posts, send messages or friend requests, or collect anyone's personal information.
- Stop the whole run immediately if Facebook shows any warning: posting limited, "you're posting too fast", "we removed your post", a checkpoint, a restriction notice, a spam warning or a CAPTCHA. Log the exact wording under Run notes and report it. Don't retry later in the same run.
- Never post in "Kitchen Stuff" (groups/yourkitchenstuff) or any group whose rules ban links, affiliate links or self-promotion. If a post is removed by a group's admins, mark that group "do not post".

0. REPLY TO COMMENTS (every run, before anything else). Richard asked on 2026-10-30 for comments on his posts to be answered automatically. Open https://www.facebook.com/notifications and look for comments and replies on Richard Tracy's own posts and Reels (deal posts, gift-guide posts, Reels) from the last 24 hours. For each one not already in the log's Replies table:
   - Reply in the comment thread under Richard's post, as Richard, within the same post only. Never send DMs/Messenger messages, never comment on other people's posts, never send friend requests.
   - Product questions (size, capacity, compatibility, what's included, how it works, is the deal still on): open the product page and answer in 1–2 short, friendly sentences using only facts from the listing. For price/deal questions, re-check the page and give the current price with a time stamp, or say the deal has ended. Add the tagged link (https://www.amazon.com/dp/<ASIN>?tag=kfffacebook-20) only if the commenter asked where to get it or asked for the link, and then end with "#ad (I earn from qualifying purchases)."
   - Simple positive comments ("nice", "thanks", "ordered!"): a short thank-you, no link.
   - Anything else (complaints, arguments, personal or medical/safety questions, anything mentioning a problem with an order, rude or spam comments, anything you're unsure of): do NOT reply. List it in the report for Richard.
   - Never claim Richard owns or used the product, never promise anything, never ask anyone to buy.
   - At most 15 replies per run, 30+ seconds apart. Record each in the Replies table: date, post/group, commenter's first name, comment (short), reply (short).

1. JOIN NEW GROUPS (morning run only, up to 5): search Facebook groups (https://www.facebook.com/search/groups/?q=...) for terms such as "amazon deals", "amazon lightning deals", "kitchen deals", "home deals", "black friday deals", "deals and steals", "coupon deals usa", "holiday deals". Join only groups that are public, United States based (skip Canada/UK groups), have 1,000+ members (prefer 10K+), show posts within the last day, and are about deals. Open the group's About page and read its rules before posting; skip groups that ban links or affiliate posts or require a fee. Record name, URL, members, rules summary and status (joined / pending approval / needs Richard / do not post) in the Groups table.

2. FIND DEALS (3–5 per run): open Amazon in Chrome:
   - Lightning Deals first: https://www.amazon.com/deals filtered to Kitchen & Dining or Home & Kitchen, deal type Lightning Deal.
   - Then kitchen deals by popularity: https://www.amazon.com/s?k=kitchen&i=kitchen&rh=p_n_deal_type%3A23566065011&s=exact-aware-popularity-rank
   Pick items with 4.3+ stars and 1,000+ ratings, a real discount of 20%+ (shown against a List or Typical price), sold or shipped by Amazon or a well-reviewed seller. Skip paper towels, plates, cups and other bulk consumables, adult or weapon products, supplements and anything with recall notices. Price mix: at least 2 of every 3 deals should cost under $25 (impulse buys such as thermometers, gadgets, utensils, storage, small organizers, stocking stuffers); at most 1 per run can be a bigger-ticket item (air fryers, coffee makers, blenders, cookware). Cheap items convert far better, and every click earns on the shopper's whole cart for 24 hours. As of 2026-10-30 the account had 75 clicks and 0 orders in 30 days, so conversion matters most.
   VERIFY each on its product page (https://www.amazon.com/dp/<ASIN>) right before posting: read the current price, list price and savings percentage, and for Lightning Deals the time left / percent claimed. If the deal has ended or the price changed, use the new numbers or drop it.

3. POST: for each group with status joined or approved (fewest posts today first), until the per-run cap, post one verified deal that group hasn't had in 3 days:
   - 2–3 sentences: product name, what it's good for (from the listing), current price and list price with the percent off, and a time stamp, e.g. "$99.99 (list $179.99, 44% off) as of Oct 30, 9:15 AM ET". For Lightning Deals say "Lightning Deal, ends soon" and only state the time left if you read it on the page. Never invent features, ratings or claims, and never say "I tried/I use".
   - Link: https://www.amazon.com/dp/<ASIN>?tag=kfffacebook-20 (no shorteners, no other tags).
   - End with: "#ad As an Amazon Associate I earn from qualifying purchases."
   - Let Facebook's link preview attach the image. Post, then confirm it shows as posted or "submitted for approval". Record it in the Posts table: date, time, run (morning/midday/night), group, ASIN, product, price stated, status (live / pending).
   Facebook's composer: click the "Write something..." button, wait, type, wait ~4s for the link preview, click "Post". A group welcome popup can swallow typing; press Escape and re-open the composer if the text didn't land.

4. Finish with a short report: groups joined (and any "needs Richard" with their questions), posts made (group, product, live or pending), anything skipped and why, and any Facebook warning.
