#!/usr/bin/env python3
"""Verify the TikTok Pixel in the deploy artifact and the live homepage response.

Run from the repository root or this directory:
    python3 site/verify_tiktok_deployment.py

This is read-only. It does not publish files, change Hostinger settings, or purge caches.
"""
from urllib.error import URLError
from urllib.request import Request, urlopen
import sys

PIXEL_ID = "DBLO06JC77U0QLCJSSEG"
DEPLOY_ARTIFACT_URL = (
    "https://raw.githubusercontent.com/"
    "dynamicservicesolutionsllc-gif/ai-marketing-claude/hostinger-deploy/index.html"
)
LIVE_URL = "https://kitchenfindsfavorites.com/"
MARKER = "TikTok Pixel Code"
TIMEOUT_SECONDS = 20


def fetch(url):
    request = Request(
        url,
        headers={
            "User-Agent": "KFF-TikTok-Pixel-Deployment-Check/1.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        body = response.read().decode("utf-8", errors="replace")
        return response.status, response.geturl(), body


def check(label, url):
    print(f"Checking {label}: {url}")
    try:
        status, final_url, body = fetch(url)
    except (URLError, TimeoutError, OSError) as exc:
        print(f"  ERROR: could not fetch page: {exc}")
        return False

    has_marker = MARKER in body
    has_pixel_id = PIXEL_ID in body
    print(f"  HTTP status: {status}; final URL: {final_url}")
    print(f"  {MARKER!r}: {'FOUND' if has_marker else 'MISSING'}")
    print(f"  Pixel ID {PIXEL_ID}: {'FOUND' if has_pixel_id else 'MISSING'}")

    if status != 200 or not has_marker or not has_pixel_id:
        print("  RESULT: FAIL")
        return False
    print("  RESULT: PASS")
    return True


def main():
    artifact_ok = check("hostinger-deploy artifact", DEPLOY_ARTIFACT_URL)
    live_ok = check("live Hostinger homepage", LIVE_URL)

    if artifact_ok and live_ok:
        print("\nBoth the deploy artifact and live homepage contain the TikTok Pixel.")
        return 0

    print("\nVerification failed or is incomplete.")
    if artifact_ok and not live_ok:
        print(
            "The GitHub deploy artifact is correct, but the live response is not. "
            "Check Hostinger's Git deployment directory/document root and purge "
            "Hostinger/CDN caches, then rerun this script."
        )
    elif not artifact_ok:
        print(
            "The deploy artifact is missing the Pixel or could not be fetched. "
            "Check the deployment workflow and hostinger-deploy branch first."
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
