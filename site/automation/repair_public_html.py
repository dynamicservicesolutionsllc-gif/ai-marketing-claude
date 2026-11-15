"""Repair deterministic affiliate markup on existing KFF public HTML pages."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DOMAIN = "kitchenfindsfavorites.com"
TAG = "kitchenfi0fde-20"
MEASUREMENT_ID = "G-G7WPSMPB7T"
STATEMENT = "As an Amazon Associate I earn from qualifying purchases."
DISCLOSURE = "#ad " + STATEMENT
SKIP = re.compile(r"<!--.*?-->|<(script|style|template|noscript)\b[^>]*>.*?</\1\s*>", re.I | re.S)
ELEMENT = re.compile(r"(<[^>]+>)")
HREF = re.compile(r"""(\s+href\s*=\s*)(["'])(.*?)\2""", re.I | re.S)
STATEMENT_WITH_PREFIX = re.compile(r"(?<!#ad )" + re.escape(STATEMENT))
ASIN_PATH = re.compile(r"/(?:dp|gp/product)/[A-Z\d]{10}(?:/|$)", re.I)


def checked_page(value):
    url = urllib.parse.urlsplit(value)
    host = url.hostname or ""
    if (url.scheme != "https" or url.username or url.password or url.port
            or not (host == DOMAIN or host.endswith("." + DOMAIN))
            or url.query or url.fragment):
        raise ValueError("Expected a verified KFF public HTTPS URL.")
    if host == DOMAIN:
        if not re.fullmatch(r"/(?:picks|microsites)/[a-z0-9-]+/", url.path):
            raise ValueError("Use a KFF product or microsite guide URL.")
    elif not re.fullmatch(r"[a-z0-9-]+\." + re.escape(DOMAIN), host) or url.path != "/":
        raise ValueError("Use the verified root of a KFF microsite.")
    return url


def microsite_slug(page):
    if page.hostname != DOMAIN:
        return page.hostname.split(".", 1)[0]
    if page.path.startswith("/microsites/"):
        return page.path.strip("/").split("/")[-1]
    return None


def update_anchor(element, page, found):
    attribute = HREF.search(element)
    if not attribute:
        return element
    raw = html.unescape(attribute[3])
    absolute = urllib.parse.urlsplit(urllib.parse.urljoin(page.geturl(), raw))
    if absolute.scheme != "https" or absolute.username or absolute.password or absolute.port:
        return element
    pairs = urllib.parse.parse_qsl(absolute.query, keep_blank_values=True)
    values = dict(pairs)
    if absolute.hostname in {"www.amazon.com", "amazon.com"} and (
        ASIN_PATH.search(absolute.path) or absolute.path.rstrip("/") == "/deals"
    ):
        found["affiliate_path"] = True
        found["direct_affiliate_links"] += 1
        if [value for key, value in pairs if key == "tag"] == [TAG]:
            return element
        pairs = [(key, value) for key, value in pairs if key != "tag"] + [("tag", TAG)]
        found["special_tags_fixed"] += 1
    elif absolute.hostname == DOMAIN and microsite_slug(page) and re.fullmatch(r"/picks/[a-z0-9-]+/?", absolute.path):
        found["affiliate_path"] = True
        parameters = {
            "utm_source": "microsite", "utm_medium": "referral", "utm_campaign": "kff_microsite_pages",
            "utm_content": microsite_slug(page)
        }
        missing = {key: value for key, value in parameters.items() if not values.get(key)}
        if not missing:
            return element
        pairs = [(key, value) for key, value in pairs if key not in missing] + list(missing.items())
        found["referrals_fixed"] += 1
    else:
        return element
    changed = absolute._replace(query=urllib.parse.urlencode(pairs)).geturl()
    return element[:attribute.start(3)] + html.escape(changed, quote=True) + element[attribute.end(3):]


def repair(source, public_url):
    page = checked_page(public_url)
    if not re.search(r"<html\b", source, re.I) or not re.search(r"<h1\b", source, re.I):
        raise ValueError("Expected an existing public HTML product or buying guide with a heading.")
    visible = SKIP.sub("", source)
    subdomain = page.hostname != DOMAIN
    if subdomain and not re.search(r"<title[^>]*>[^<]*Buying Guide\s*</title>", visible, re.I):
        raise ValueError("Subdomain is not a KFF buying-guide template.")
    if STATEMENT not in visible and not re.search(r"amazon\.com|kitchenfindsfavorites\.com/picks/", visible, re.I):
        raise ValueError("Page does not contain a KFF affiliate disclosure or a recognizable affiliate route.")

    found = {"disclosure_fixed": 0, "special_tags_fixed": 0, "referrals_fixed": 0,
             "affiliate_path": False, "direct_affiliate_links": 0, "analytics_added": False}
    parts = []
    cursor = 0
    for blocked in [*SKIP.finditer(source), None]:
        region = source[cursor:blocked.start() if blocked else len(source)]
        for idx, part in enumerate(ELEMENT.split(region)):
            if idx % 2 == 0:
                part, count = STATEMENT_WITH_PREFIX.subn(DISCLOSURE, part)
                found["disclosure_fixed"] += count
            elif re.match(r"<a\s", part, re.I):
                part = update_anchor(part, page, found)
            parts.append(part)
        if blocked:
            parts.append(blocked.group())
            cursor = blocked.end()
    changed = "".join(parts)
    if DISCLOSURE not in SKIP.sub("", changed) and found["affiliate_path"]:
        addition = '<p class="disclosure">' + DISCLOSURE + '</p>'
        changed, count = re.subn(r"<main\b[^>]*>", lambda match: match.group() + addition, changed, count=1, flags=re.I)
        found["disclosure_fixed"] += count
    if (microsite_slug(page) and found["affiliate_path"]
            and not re.search(r"googletagmanager\.com/(?:gtag|gtm)|\b(?:G|GTM)-[A-Z0-9]{6,}", source)
            and not re.search(r'<meta\b[^>]*content=["\'][^"\']*noindex', visible, re.I)):
        tracking = (
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={MEASUREMENT_ID}"></script>'
            f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
            f"gtag('js',new Date());gtag('config','{MEASUREMENT_ID}');</script>"
        )
        if found["direct_affiliate_links"]:
            tracking += r"""<script>document.addEventListener('click',function(event){
const link=event.target.closest('a[href]');
if(!link)return;
const url=new URL(link.href,location.origin);
if(!['amazon.com','www.amazon.com'].includes(url.hostname)||!url.searchParams.get('tag'))return;
const asin=(url.pathname.match(/\/(?:dp|gp\/product)\/([A-Z0-9]{10})(?:\/|$)/i)||[])[1]||'';
gtag('event','amazon_click',{asin:asin,link_page:location.pathname,transport_type:'beacon'});
});</script>"""
        changed, count = re.subn(r"</head\s*>", lambda match: tracking + match.group(), changed, count=1, flags=re.I)
        found["analytics_added"] = bool(count)
    return changed, found


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def transfer(credentials, relative_path, payload):
    base = urllib.parse.urlsplit(credentials["url"])
    if (base.scheme != "https" or not base.hostname or base.username or base.password
            or base.query or base.fragment):
        raise ValueError("Unexpected Hostinger upload endpoint.")
    if not re.fullmatch(r"(?:(?:picks|microsites)/[a-z0-9-]+/|[a-z0-9-]+/)?index\.html", relative_path):
        raise ValueError("Only an existing exact HTML entrypoint can be uploaded.")
    url = credentials["url"].rstrip("/") + "/" + relative_path + "?override=true"
    headers = {
        "X-Auth": credentials["auth_key"], "X-Auth-Rest": credentials["rest_auth_key"],
        "Tus-Resumable": "1.0.0", "Upload-Offset": "0"
    }
    opener = urllib.request.build_opener(NoRedirect)
    create = urllib.request.Request(url, headers={**headers, "Upload-Length": str(len(payload))}, method="POST")
    with opener.open(create, timeout=25) as response:
        if response.status != 201:
            raise ValueError(f"Upload start expected HTTP 201, got {response.status}.")
    send = urllib.request.Request(url, data=payload, method="PATCH",
                                  headers={**headers, "Content-Type": "application/offset+octet-stream"})
    with opener.open(send, timeout=25) as response:
        if response.status != 204 or response.headers.get("Upload-Offset") != str(len(payload)):
            raise ValueError("Hostinger did not confirm all bytes.")
    return {"uploaded_bytes": len(payload), "status": 204}


def document_path(page, shared_root=False):
    if page.hostname == DOMAIN:
        return page.path.lstrip("/") + "index.html"
    if shared_root:
        return microsite_slug(page) + "/index.html"
    return "index.html"



def repair_batch(entries, credentials=None):
    def repair_file(entry):
        path = entry["path"]
        target = entry["url"]
        try:
            verified_page = checked_page(target)
            if path != document_path(verified_page, shared_root=True):
                raise ValueError("The path does not match the verified Hostinger document root.")
            original = entry["source"]
            if len(original.encode("utf-8")) > 900000:
                raise ValueError("The source HTML exceeds the repair size limit.")
            revised, findings = repair(original, target)
            result = {"path": path, "url": target, **findings}
            if revised == original:
                return {**result, "status": "unchanged"}
            payload = revised.encode("utf-8")
            fingerprint = sha256(payload.rstrip()).hexdigest()
            if credentials is None:
                return {**result, "status": "repairable", "expected_sha256": fingerprint}
            transfer(credentials, path, payload)
            return {**result, "status": "uploaded", "expected_sha256": fingerprint}
        except urllib.error.HTTPError as error:
            return {"path": path, "url": target, "status": "upload_failed", "detail": f"HTTP {error.code}"}
        except urllib.error.URLError as error:
            return {"path": path, "url": target, "status": "upload_failed", "detail": type(error.reason).__name__}
        except ValueError as error:
            return {"path": path, "url": target, "status": "skipped", "detail": str(error)}

    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(repair_file, entries))


def batch_cli():
    parser = argparse.ArgumentParser(description="Repair verified KFF HTML entrypoints in a shared document root.")
    parser.add_argument("--batch", required=True, type=Path, help="JSON array of url, relative path, and complete current HTML source.")
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", help="Read temporary Hostinger upload credentials from stdin.")
    args = parser.parse_args()
    entries = json.loads(args.batch.read_text())
    credentials = json.load(sys.stdin) if args.apply else None
    results = repair_batch(entries, credentials)
    args.report.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({status: sum(row["status"] == status for row in results)
                      for status in sorted({row["status"] for row in results})}))



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("public_url")
    parser.add_argument("output", type=Path)
    parser.add_argument("--upload-path", help="Exact relative path from the Hostinger file read. Credentials arrive on stdin.")
    parser.add_argument("--shared-root", action="store_true", help="Use the verified main Hostinger document root for a subdomain.")
    args = parser.parse_args()
    original = args.source.read_bytes().decode("utf-8")
    normalized, result = repair(original, args.public_url)
    args.output.write_bytes(normalized.encode("utf-8"))
    result["changed"] = original != normalized
    if args.upload_path and result["changed"]:
        page = checked_page(args.public_url)
        expected_path = document_path(page, shared_root=args.shared_root)
        if args.upload_path != expected_path:
            raise ValueError("The upload path must match the verified source page.")
        result.update(transfer(json.load(sys.stdin), args.upload_path, normalized.encode("utf-8")))
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        if "--batch" in sys.argv:
            batch_cli()
        else:
            main()
    except urllib.error.HTTPError as error:
        sys.exit(f"Hostinger upload failed with HTTP {error.code}.")
    except urllib.error.URLError as error:
        sys.exit(f"Hostinger upload could not connect ({type(error.reason).__name__}).")
