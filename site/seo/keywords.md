# Keyword map

One target query per page. Research via web search of the live results (no Amazon fetches). The guide's `keyword` field in
`products.json` holds the primary query; an optional `headline` sets the page's <title>/H1 when it differs from the
short `title` used on cards, breadcrumbs and pins.

| Page | Primary query | Secondary queries | Applied | Evidence |
|---|---|---|---|---|
| /guides/food-prep-tools/ | time saving kitchen gadgets | kitchen gadgets that save time, meal prep tools, time-saving kitchen tools | 2026-11-01: title/H1 "Time-Saving Kitchen Gadgets for Faster Meal Prep", description, intro, types H2, new FAQ "Which kitchen gadgets save the most time?" | Page-one results for these queries are dominated by "time-saving kitchen gadgets/tools" and "meal prep tools" list titles (HGTV, Brit+Co, GadgetReview, Farm & Fleet, Unexpectedly Domestic, Scary Mommy); "food prep gadgets" phrasing rarely appears. |
| /guides/baking-essentials/ (new) | baking essentials for beginners | baking tools for beginners, must have baking tools, basic baking tools list | 2026-11-01: new hand-picked buying guide (10 existing products from cooking-tools, blenders-and-mixers, food-prep-tools); title/H1 "Baking Essentials for Beginners: 10 Tools to Start" | Page one for these queries is all beginner list posts (Silver Spoon, Baking Mad, Bake School, Sweet & Savory, Kindly Unspoken, Fox News, Cuisine at Home); the site had the tools but no page for the query — only the gift-intent "gifts for bakers" list. |
| /guides/pantry-storage/ | best pantry organizers | pantry storage containers, small pantry organization ideas, pantry organization ideas | 2026-11-10: title/H1 "Best Pantry Organizers and Storage Containers", description, intro, types H2 "Which pantry organizers do you need?", new FAQ "What are the best pantry organizers for a small pantry?" | Page one for "best pantry organizers and storage containers" is led by "best pantry organizers" list titles (Bustle, Real Homes, Tasting Table, Gear Patrol, CNN Underscored); "small pantry organization ideas" results are tip/list posts (Little House Living, Savvy and Sorted, Happy Happy Nester). The guide covers bins, can racks and turntables, not just containers, so "organizers" fits the page better than "storage containers". |

## Candidates for later runs

- small kitchen appliances for small spaces (countertop-cooking — already aligned)
- kitchen drawer organizer ideas / small kitchen organization ideas (drawer-organizers)
- under sink organizer (under-sink-storage)

## Pinterest search phrases (`pin_keywords`)

Applied 2026-11-02 to all 14 buying guides' Pinterest pins (titles of the "how to choose" pin, plus a closing "Save for later: …" sentence in each guide pin description). Phrases follow Pinterest's own topic pages and board names in search results ("kitchen drawer organization ideas", "under sink storage ideas", "kitchen sink organizers", "baking gadgets", "coffee bar ideas"), which favour "… ideas" phrasing over the "best …" phrasing Google rewards.

| Guide | Pinterest phrases |
|---|---|
| /guides/drawer-organizers/ | kitchen drawer organization ideas; small kitchen organization; utensil drawer organizer |
| /guides/under-sink-storage/ | under sink organization ideas; under kitchen sink storage; kitchen sink organizer |
| /guides/dish-drying-racks/ | dish rack ideas for small kitchens; small kitchen counter organization; over the sink dish rack |
| /guides/pantry-storage/ | pantry organization ideas; small pantry storage; airtight food storage containers |
| /guides/spice-racks/ | spice organization ideas; spice rack ideas for small kitchens; spice cabinet organization |
| /guides/cookware-organizers/ | pots and pans organization ideas; pot lid organizer; kitchen cabinet organization |
| /guides/food-prep-tools/ | time-saving kitchen gadgets; meal prep tools; useful kitchen gadgets |
| /guides/cooking-tools/ | kitchen essentials list; digital meat thermometer; kitchen scale for baking |
| /guides/baking-essentials/ | baking essentials for beginners; baking tools list; must have baking tools |
| /guides/coffee-and-tea/ | coffee bar ideas; lattes at home; tea station ideas |
| /guides/blenders-and-mixers/ | immersion blender uses; hand mixer for baking; small kitchen appliances |
| /guides/countertop-cooking/ | small appliances for small spaces; small kitchen appliances; apartment kitchen essentials |
| /guides/insulated-drinkware/ | insulated tumbler and water bottle ideas; tumbler with handle and straw; water bottle ideas |
| /guides/air-fryer-accessories/ | air fryer accessories; air fryer must haves; air fryer liners |

Board follow-up (not automated; boards are managed in Pinterest by the posting task): "Small Kitchen Gadgets We Love", "Drinkware & Tumblers We Love" and "Kitchen Organization Must-Haves" have non-search names. Renaming them in Pinterest would break the queue's `board` match, so any rename must change the `board` values in products.json and the posting routine's board list in the same step.
