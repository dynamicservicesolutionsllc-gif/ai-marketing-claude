Daily Facebook group run for Frank's Amazon affiliate site "Kitchen Finds & Favorites" (https://kitchenfindsfavorites.com, Facebook Page https://www.facebook.com/1433493846508656). Chrome is signed in to the personal profile "Richard Tracy", which posts in groups. Richard asked for this on 2026-10-29: post the site's new products, guides and free printable in Facebook groups that allow links, and find 2–3 new groups a day (raised to up to 5 a day, 20 active groups max, on 2026-11-02 so volume grows across more groups). The goal is the first qualifying Amazon Associates sales and email sign-ups, without getting the profile flagged for spam.

Folder access: since 2026-11-02 runs can read C:\Users\office\kff-site directly, so attach images from public\img. If a read is ever blocked again, use the same image from https://kitchenfindsfavorites.com/img/<ASIN>.png saved to the scratchpad, and say so in the report.

Tools: Claude in Chrome (mcp__claude-in-chrome__*, load with ToolSearch). If Chrome isn't connected or Facebook isn't signed in, stop and report it. Never type passwords. PowerShell only for `git -C C:\Users\office\kff-site pull --ff-only origin main` (read-only use of the repo; never commit from this run).

Log: C:\Users\office\OneDrive\Documents\claud create\kff-facebook-groups-log.md (edit it with Edit/Write, not shell redirection; OneDrive can drop shell writes). It has a Groups table and a Posts table. Read it first; every decision below depends on it.

HARD LIMITS (never exceed):
- Join at most 5 new groups per run, and keep at most 20 groups with status joined or approved (if at 20, only join to replace a "do not post" group).
- At most 1 post per group per day, and at most 15 group posts per run in total. Volume grows by adding groups, never by posting more often in one group.
- Never post the same page in the same group within 7 days.
- Wait at least 3 minutes between posts.
- Never answer a group's participation questions, accept or agree to group rules, comment on other people's posts, send messages or friend requests, or collect anyone's personal information or email address. If a group pops up questions or a rules agreement, close it without answering, mark the group "needs Richard" in the log, and move on.
- Stop the whole run immediately if Facebook shows any warning: posting limited, "you're posting too fast", "we removed your post", a checkpoint, a restriction notice or a CAPTCHA. Log the exact wording under Run notes and report it.

0. CHECK THE LAST RUNS FIRST: for every post in the Posts table marked pending, open that group, look under the group's "Your content" / "Pending" posts and in the feed, and update its status to approved, declined or removed. A post still pending after 3 days counts as declined. Then update the group's Track record in the Groups table as "<approved>/<posted>" (for example 3/4). A group with 2 or more declined or removed posts gets status "do not post"; note why. If a group removed a post AND Facebook showed a warning, stop the run as below.

1. SYNC: run the git pull above so the local images match the live site. Open https://kitchenfindsfavorites.com/products.json?nocache=<random> for today's products (each has page_url and pin_image; the same image is at C:\Users\office\kff-site\site\public\img\<ASIN>.png).

2. FIND NEW GROUPS (up to 5, within the 20-group cap): search Facebook groups for terms like "amazon finds kitchen", "amazon home finds", "kitchen gadgets", "kitchen organization ideas", "holiday gift ideas", "thanksgiving recipes and tips", "baking ideas". Only join a group that is public, has 1,000+ members, shows 5+ posts a day, is about kitchens, home, deals or holidays, and whose About/rules do NOT ban self-promotion, links or affiliate posts. Skip "Kitchen Stuff" (groups/yourkitchenstuff) and any group already in the log. After joining, record name, URL, members, rules summary and status (joined / needs Richard / pending approval) in the Groups table.

3. POST: rank the groups with status joined or approved by Track record, best approval rate first (new groups with no record go after proven groups but before any group under 50%), oldest last-post first within a tie. Post down that list until the per-run cap. Joining replacement groups in step 2 matters most when groups drop to "do not post".
   Match content to the group: recipe, cooking and holiday groups get the free Thanksgiving Hosting Timeline or the Thanksgiving checklist first (useful, not a sales pitch, so admins approve it); "finds", deals and home-accessory groups get products and gift guides.
   a. Choose content that group hasn't had in 7 days, in this priority (after the group-type match above):
      - a product added today or yesterday (its page_url + utm, image = local <ASIN>.png);
      - until Nov 26: the Thanksgiving Hosting Timeline freebie https://kitchenfindsfavorites.com/thanksgiving-timeline/ (image C:\Users\office\kff-site\site\public\img\pins\gift-thanksgiving-kitchen-checklist-c.jpg) or the Thanksgiving checklist /gifts/thanksgiving-kitchen-checklist/;
      - until Dec 1: the Black Friday list /gifts/black-friday-kitchen-gifts/;
      - the bakers guide /gifts/gifts-for-bakers/ or another gift guide.
      Gift guide images: C:\Users\office\kff-site\site\public\img\pins\gift-<key>-a.jpg (or -b/-c/-d).
   b. Write 2–3 honest sentences in plain, friendly language, drawn from the page's own copy (no prices, ratings, review counts, "best seller", "deal" or sale claims, and no "I tried/I use" claims). Any post that links to a product or guide page starts with "#ad As an Amazon Associate I earn from qualifying purchases." Link only to kitchenfindsfavorites.com, never to amazon.com or amzn.to, with ?utm_source=facebook&utm_medium=social&utm_campaign=<short-page>-<short-group>.
   c. End about one post in three with: "If this helps, I'd really appreciate a like on our page, Kitchen Finds & Favorites: https://www.facebook.com/1433493846508656".
   d. Attach the image with the file_upload tool on the composer's Photo/video input, post, and confirm the post appears (or shows "submitted for approval"). Record it in the Posts table: date, group, page, campaign tag, status (live / pending).

4. Finish with a short report: groups joined (and any marked "needs Richard" with their questions), posts made (group, page, live or pending), anything skipped and why, and any Facebook warning. Only flag Richard if something needs him.
