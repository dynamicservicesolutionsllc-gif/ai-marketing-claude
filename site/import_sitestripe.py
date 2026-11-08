#!/usr/bin/env python3
"""Import reviewed editorial products with supplied SiteStripe links. No Amazon requests."""
import argparse
import copy
from datetime import date, datetime
from zoneinfo import ZoneInfo
from collections import Counter
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from affiliate_links import validate_sitestripe_url
from product_media import verified_photo

ROOT = Path(__file__).resolve().parent
DAILY_PRODUCT_LIMIT = 15


def prepare_import(data, entries):
    if not isinstance(entries, list):
        raise ValueError('Import file must contain a JSON array')
    counts = Counter(entry.get('added') for entry in entries)
    if any(count > DAILY_PRODUCT_LIMIT for count in counts.values()):
        raise ValueError(f'At most {DAILY_PRODUCT_LIMIT} new products may be released per day')
    result = copy.deepcopy(data)
    tag = data['site']['associate_tag']
    seen = {p['asin'] for p in data['products']}
    staged = {p['asin'] for p in data.get('staging', {}).get('products', [])}
    for entry in entries:
        if entry.get('approved') is not True:
            raise ValueError('Each entry must be reviewed and approved')
        asin = entry.get('asin', '')
        if not re.fullmatch(r'B0[A-Z0-9]{8}', asin) or asin in seen or asin in staged:
            raise ValueError(f'Invalid, existing or staged ASIN: {asin}')
        supplied_link = entry.get('sitestripe_url')
        affiliate_url = supplied_link or f'https://www.amazon.com/dp/{asin}/ref=nosim?tag={tag}'
        validate_sitestripe_url(affiliate_url, asin, tag)
        for field in ('variant', 'seller', 'editorial_reason'):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError(f'Missing verified {field}')
        date.fromisoformat(entry['verified_at'])
        source = urlsplit(entry.get('source_url', ''))
        if source.scheme != 'https' or not source.hostname or 'amazon.' in source.hostname:
            raise ValueError('Provide the manufacturer or other authorized specification source')
        if entry.get('content_rights') != 'original-editorial-graphic':
            raise ValueError('This importer requires original editorial graphics')
        allowed = ('asin', 'name', 'category', 'subcategory', 'blurb', 'added', 'award',
                   'graphic', 'pin', 'suits', 'check', 'sitestripe_url')
        product = {k: entry[k] for k in allowed if k in entry}
        # Keep the existing link key for compatibility with the builder and feeds.
        product['sitestripe_url'] = affiliate_url
        product['photo_review'] = verified_photo(entry, ROOT)
        product['source_review'] = {k: entry[k] for k in ('variant', 'seller', 'verified_at', 'source_url', 'content_rights', 'editorial_reason')}
        product['source_review']['link_source'] = 'supplied' if supplied_link else 'generated_from_asin'
        result['products'].append(product)
        seen.add(asin)
    # Reuse all existing site content, taxonomy, disclosure and duplicate checks.
    import build
    _, errors = build.load(result)
    if errors:
        raise ValueError('\n'.join(errors))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--apply', action='store_true', help='Write only after the entire batch validates')
    args = parser.parse_args()
    original = json.loads((ROOT / 'products.json').read_text())
    entries = json.loads(args.input.read_text())
    today = datetime.now(ZoneInfo('America/New_York')).date()
    # Release only the reviewed entries whose editorial publication date has arrived.
    if not isinstance(entries, list):
        raise ValueError('Import file must contain a JSON array')
    entries = [entry for entry in entries if date.fromisoformat(entry['added']) <= today]
    result = prepare_import(original, entries)
    if args.apply and entries:
        target = ROOT / 'products.json'
        tmp = target.with_suffix('.tmp')
        tmp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
        tmp.replace(target)
    print(f'{len(entries)} SiteStripe products validated; ' + ('catalog updated' if args.apply and entries else 'catalog unchanged'))


if __name__ == '__main__':
    main()
