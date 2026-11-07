#!/usr/bin/env python3
"""Build photo-based product videos and native publishing queues. Does not post to social accounts."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageOps
from product_media import verified_photo

ROOT = Path(__file__).resolve().parent
DISCLOSURE = '#ad As an Amazon Associate I earn from qualifying purchases.'
PLATFORMS = ('pinterest', 'facebook', 'instagram', 'tiktok', 'youtube')
HEADERS = ['Title', 'Media URL', 'Pinterest board', 'Thumbnail', 'Description', 'Link', 'Publish date', 'Keywords']


def select_products(feed, day):
    eligible = [p for p in feed if p.get('sitestripe_url') and p.get('photo_review')]
    today = [p for p in eligible if p['added'] == day]
    if len(today) > 5 or len({p['asin'] for p in eligible}) != len(eligible):
        raise ValueError('Campaign must contain at most five unique new products per date')
    return eligible, today


def media_id(product):
    payload = {key: product[key] for key in ('asin', 'graphic', 'suits', 'check', 'photo_review')}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
    return f'{product["asin"]}-overview-{digest}'


def lines(text, font, draw, width):
    result, current = [], ''
    for word in text.split():
        trial = f'{current} {word}'.strip()
        if current and draw.textlength(trial, font=font) > width:
            result.append(current)
            current = word
        else:
            current = trial
    return result + [current]


def slide(product, heading, body, target):
    image = Image.new('RGB', (1080, 1920), '#fbf8f3')
    draw = ImageDraw.Draw(image)
    font = lambda size: ImageFont.truetype(str(ROOT / 'fonts/DejaVuSans.ttf'), size)
    draw.rectangle((0, 0, 1080, 160), fill='#7b3625')
    draw.text((540, 75), 'KITCHEN FINDS & FAVORITES', font=font(42), fill='white', anchor='mm')
    with Image.open(ROOT / f'assets/products/{product["asin"]}.jpg') as source:
        # Contain the exact approved photo; do not invent or distort the product.
        photo = ImageOps.contain(source.convert('RGB'), (980, 850))
        image.paste(photo, ((1080-photo.width)//2, 190+(850-photo.height)//2))
    y = 1090
    for text, size, max_lines in ((heading, 55, 3), (body, 42, 6)):
        while size > 28:
            wrapped = lines(text, font(size), draw, 940)
            if len(wrapped) <= max_lines:
                break
            size -= 2
        if len(wrapped) > max_lines:
            raise ValueError('Shorten campaign copy; it does not fit the video')
        for line in wrapped:
            draw.text((540, y), line, font=font(size), fill='#2b2622', anchor='mt')
            y += size+16
        y += 30
    draw.rectangle((0, 1720, 1080, 1920), fill='#7b3625')
    draw.text((540, 1760), '#ad · Research overview, not a hands-on demo', font=font(29), fill='white', anchor='mt')
    draw.text((540, 1810), 'As an Amazon Associate I earn', font=font(31), fill='white', anchor='mt')
    draw.text((540, 1855), 'from qualifying purchases.', font=font(31), fill='white', anchor='mt')
    image.save(target)


def make_video(product, output):
    if output.exists():
        return
    verified_photo(product, ROOT)
    content = [('Before you buy', product['name']), ('Product details', ' · '.join(product['graphic']['points'])),
               ('Check the fit', product['check']), ('Read the full product guide', 'KitchenFindsFavorites.com · Compare the exact variant before buying.')]
    with tempfile.TemporaryDirectory() as tmp:
        for n, (heading, body) in enumerate(content):
            slide(product, heading, body, Path(tmp)/f'{n}.png')
        playlist = Path(tmp)/'frames.txt'
        playlist.write_text(''.join(f"file '{n}.png'\nduration 6\n" for n in range(4))+"file '3.png'\n")
        output.parent.mkdir(parents=True, exist_ok=True)
        partial = output.with_suffix('.tmp.mp4')
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(playlist),
                        '-vf','fps=24,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','22',
                        '-t','24','-movflags','+faststart',str(partial)],check=True)
        partial.replace(output)


def campaign(product, base):
    creative = media_id(product)
    links = {platform: product['page_url']+'?'+urlencode({'utm_source':platform,'utm_medium':'organic_social','utm_campaign':creative}) for platform in PLATFORMS}
    description = product['pin']['description']
    return {'asin':product['asin'],'creative_id':creative,'video':f'{base}/videos/products/{creative}.mp4',
            'image':product['pin_image'],'page_url':product['page_url'],
            'platforms':{platform:{'status':'awaiting_native_duplicate_check_and_publish',
                                  'title':product['pin']['title'], 'description':description,
                                  'website_link':links[platform],
                                  'caption':description+' '+(links[platform] if platform in ('youtube','facebook') else 'Full guide: link in bio.'),
                                  'post_url':None} for platform in PLATFORMS}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date',default=datetime.now(ZoneInfo('America/New_York')).date().isoformat())
    args=parser.parse_args()
    feed=json.loads((ROOT/'public/products.json').read_text())
    eligible, today=select_products(feed,args.date)
    base=json.loads((ROOT/'products.json').read_text())['site']['url']
    for product in eligible:
        verified_photo(product,ROOT)
        make_video(product,ROOT/f'public/videos/products/{media_id(product)}.mp4')
    batch=[campaign(p,base) for p in today]
    folder=ROOT/'public/marketing'/args.date
    folder.mkdir(parents=True,exist_ok=True)
    # Do not emit an immediate-publication CSV. Schedule tomorrow onward via native UI after history checks.
    with (folder/'pinterest-review.csv').open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=HEADERS)
        writer.writeheader()
        for p, c in zip(today,batch):
            writer.writerow({'Title':p['pin']['title'],'Media URL':p['pin_image'],'Pinterest board':p['pin']['board'],
                             'Description':p['pin']['description'],'Link':c['platforms']['pinterest']['website_link'],
                             'Publish date':'','Keywords':p['subcategory'].replace('-',' ')})
    (folder/'campaigns.json').write_text(json.dumps({'date':args.date,'target_products':5,'ready_products':len(today),
        'status':'prepared_for_native_review' if today else 'blocked_no_verified_products',
        'csv_warning':'Review file only. Blank publish dates publish immediately on upload. Never upload without native duplicate checks.',
        'automatically_published_social_posts':0,'campaigns':batch},indent=2)+'\n')
    for p in eligible:
        p['product_video']=f'{base}/videos/products/{media_id(p)}.mp4'
    (ROOT/'public/products.json').write_text(json.dumps(feed,indent=2)+'\n')
    print(f'{len(today)}/5 verified products prepared for {args.date}; zero social posts claimed')


if __name__=='__main__':
    main()
