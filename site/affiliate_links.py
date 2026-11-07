"""Validate explicit Amazon US SiteStripe long links without fetching Amazon."""
import re
from urllib.parse import parse_qs, urlsplit


def validate_sitestripe_url(url, asin, tag):
    if not isinstance(url, str) or any(c.isspace() for c in url):
        raise ValueError('SiteStripe link must be a single URL')
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.netloc not in {'amazon.com', 'www.amazon.com'}
            or parts.fragment):
        raise ValueError('Use the HTTPS Amazon.com long link from SiteStripe')
    match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})(?:/|$)', parts.path)
    if not match or match.group(1) != asin:
        raise ValueError('SiteStripe link must match the product ASIN')
    if parse_qs(parts.query).get('tag') != [tag]:
        raise ValueError('SiteStripe tracking tag does not match this website')
    return url  # Preserve all parameters exactly; never reconstruct a supplied link.


def product_affiliate_url(product, tag):
    if product.get('sitestripe_url'):
        return validate_sitestripe_url(product['sitestripe_url'], product['asin'], tag)
    return f'https://www.amazon.com/dp/{product["asin"]}?tag={tag}'
