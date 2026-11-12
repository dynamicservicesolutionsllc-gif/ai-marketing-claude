import json, html, re, pathlib, collections
root=pathlib.Path(__file__).resolve().parent
data=json.loads((root/'products.json').read_text(encoding='utf-8'))
groups=collections.defaultdict(list)
for p in data['products']:
    if p.get('subcategory'): groups[p['subcategory']].append(p)
out=root/'public'/'buying-guides'
count=0
for slug, items in sorted(groups.items()):
    if len(items)<3: continue
    title=slug.replace('-',' ').title()
    path=out/slug/'index.html'
    path.parent.mkdir(parents=True,exist_ok=True)
    cards=[]
    for p in items[:8]:
        name=html.escape(p['name'])
        desc=html.escape(p.get('blurb',''))
        fit=html.escape(p.get('suits',''))
        check=html.escape(p.get('check',''))
        link='/picks/'+re.sub(r'[^a-z0-9]+','-',p['name'].lower()).strip('-')+'/'
        # Existing product-page slugs can differ from names: do not invent destination.
        cards.append(f'<article><h3><a href="{link}">{name}</a></h3><p>{desc}</p><p><strong>Who it may suit:</strong> {fit}</p><p><strong>What to check:</strong> {check}</p></article>')
    body=''.join(cards)
    doc=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>How to Choose {title} | Kitchen Finds &amp; Favorites</title><meta name="description" content="Compare practical features and buying considerations for {title.lower()}. See our kitchen buying guide."><link rel="canonical" href="https://kitchenfindsfavorites.com/buying-guides/{slug}/"><style>body{{font:17px/1.6 system-ui,Arial,sans-serif;color:#25332e;max-width:900px;margin:auto;padding:24px;background:#fafbf9}}a{{color:#17633d}}article{{background:#fff;border:1px solid #ddd;border-radius:12px;padding:20px;margin:18px 0}}h1{{line-height:1.2}}footer{{font-size:14px;margin-top:35px}}</style></head><body><nav><a href="/">Kitchen Finds &amp; Favorites</a> / <a href="/buying-guides/">Buying guides</a></nav><main><h1>How to Choose {title}</h1><p>Start with your available space, intended use, cleaning requirements and the manufacturer's specifications. These products are examples to compare, not a claim that we tested or ranked them by sales.</p><h2>Products and practical buying considerations</h2>{body}<h2>Before you buy</h2><p>Measure the installation or storage area, check compatibility and dimensions on the current product listing, and read recent customer feedback. Product specifications and availability can change.</p><p><a href="/buying-guides/">Explore more kitchen buying guides</a></p></main><footer><p>As an Amazon Associate I earn from qualifying purchases.</p></footer></body></html>"""
    path.write_text(doc,encoding='utf-8')
    count+=1
print('Generated',count,'distinct buying guides')
