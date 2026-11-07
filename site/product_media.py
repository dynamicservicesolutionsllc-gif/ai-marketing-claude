"""Photo requirements for new SiteStripe products; never download product images."""
import hashlib
from pathlib import Path
from urllib.parse import urlsplit


def verified_photo(entry, site_root):
    review = entry.get('photo_review') or {}
    if review.get('exact_product') is not True:
        raise ValueError('An approved photo of the exact product is required')
    for field in ('source_url', 'rights_basis', 'rights_evidence', 'author', 'license'):
        if not isinstance(review.get(field), str) or not review[field].strip():
            raise ValueError(f'Missing photo {field}')
    source = urlsplit(review['source_url'])
    if source.scheme != 'https' or not source.hostname or source.hostname.endswith(('amazon.com', 'media-amazon.com')):
        raise ValueError('Use a permitted non-Amazon photo source')
    if review['rights_basis'] not in {'owned', 'written-permission', 'commercial-license', 'public-domain'}:
        raise ValueError('Photo reuse permission must be documented')
    path = Path(site_root) / 'assets' / 'products' / f'{entry["asin"]}.jpg'
    if not path.is_file():
        raise ValueError(f'Missing approved product photo: {path.name}')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if review.get('sha256') != digest:
        raise ValueError('Photo changed or its approval hash is missing')
    from PIL import Image
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        if min(image.size) < 800:
            raise ValueError('Product photo must be at least 800 pixels on both sides')
    return dict(review, exact_product=True)
