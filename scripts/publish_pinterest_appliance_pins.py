#!/usr/bin/env python3
"""Publish the three approved appliance Pins through the official Pinterest API.

A missing or invalid token prevents publishing. The script resolves the named boards,
checks each board for matching titles/destination pages, then creates image Pins from
the associated YouTube Short thumbnails. It does not download or repost the videos.
"""
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

API = "https://api.pinterest.com/v5"
TOKEN = os.environ.get("PINTEREST_ACCESS_TOKEN", "").strip()
QUEUE_PATH = sys.argv[1] if len(sys.argv) > 1 else "campaigns/pinterest/black-friday-appliances-2026.json"


def request(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = Request(API + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=45) as res:
            raw = res.read()
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1200]
        raise RuntimeError(f"Pinterest API {method} {path} returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Pinterest API request failed: {exc}") from exc


def pages(path):
    bookmark = None
    while True:
        params = {"page_size": "250"}
        if bookmark:
            params["bookmark"] = bookmark
        data = request("GET", path + "?" + urlencode(params))
        yield from data.get("items", [])
        bookmark = data.get("bookmark")
        if not bookmark:
            break


def slug(url):
    parts = [p for p in urlparse(url).path.split("/") if p]
    return parts[-1].casefold() if len(parts) >= 2 else ""


def title_key(value):
    return re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).strip()


def canonical(url):
    if not url:
        return ""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme.casefold(), parsed.netloc.casefold(), parsed.path.rstrip("/") or "/", "", "", ""))


def main():
    with open(QUEUE_PATH, encoding="utf-8") as f:
        queue = json.load(f)

    if not TOKEN:
        print("SKIPPED: GitHub secret PINTEREST_ACCESS_TOKEN is not configured. No Pins were created.")
        return 0

    boards = list(pages("/boards"))
    board_by_slug = {slug(b.get("url", "")): b for b in boards}
    created = 0
    skipped = 0

    for pin in queue["pins"]:
        board_slug = slug(pin["board_url"])
        board = board_by_slug.get(board_slug)
        if not board:
            raise RuntimeError(f"Could not resolve Pinterest board URL: {pin['board_url']}")
        board_id = board["id"]
        wanted_title = title_key(pin["title"])
        wanted_link = canonical(pin["destination_url"])
        existing = list(pages(f"/boards/{board_id}/pins"))
        duplicate = next((p for p in existing if
            title_key(p.get("title", "")) == wanted_title or
            canonical(p.get("link", "")) == wanted_link), None)
        if duplicate:
            print(f"SKIPPED duplicate on {board_slug}: existing Pin {duplicate.get('id', '(id unavailable)')}")
            skipped += 1
            continue

        payload = {
            "board_id": board_id,
            "title": pin["title"],
            "description": pin["description"],
            "link": pin["destination_url"],
            "media_source": {
                "source_type": "image_url",
                "url": pin["media_image_url"],
                "is_standard": True
            }
        }
        result = request("POST", "/pins", payload)
        pin_id = result.get("id")
        if not pin_id:
            raise RuntimeError(f"Pinterest returned no Pin ID for {pin['key']}; response omitted from logs.")
        print(f"CREATED {pin['key']}: https://www.pinterest.com/pin/{pin_id}/")
        created += 1

    print(f"Finished: {created} Pin(s) created; {skipped} duplicate(s) skipped.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
