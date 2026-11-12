"""Fail deployment when a published Amazon product link lacks an approved Associates tag."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, parse_qs
import json
import sys

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
site = data["site"]
allowed = {site["associate_tag"], *site.get("channel_tags", {}).values()}
errors = []
count = 0

class Audit(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
    def handle_starttag(self, tag, attrs):
        global count
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        parsed = urlparse(href)
        host = (parsed.hostname or "").lower()
        if host not in {"amazon.com", "www.amazon.com", "smile.amazon.com"}:
            return
        count += 1
        tags = parse_qs(parsed.query).get("tag", [])
        if len(tags) != 1 or tags[0] not in allowed:
            errors.append(f"{self.path}: missing or invalid Associates tag: {href[:200]}")

for path in (ROOT / "public").rglob("*.html"):
    Audit(path.relative_to(ROOT)).feed(path.read_text(encoding="utf-8", errors="replace"))

print(f"Audited {count} Amazon links across generated HTML pages; failures: {len(errors)}")
for error in errors[:30]:
    print("ERROR:", error, file=sys.stderr)
if errors:
    sys.exit(1)
