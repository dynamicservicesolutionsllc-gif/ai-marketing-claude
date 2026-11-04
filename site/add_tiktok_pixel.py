#!/usr/bin/env python3
"""Add the TikTok Pixel to generated site pages before deployment."""
from datetime import datetime, timezone
from pathlib import Path
import re
import sys

PUBLIC = Path(__file__).resolve().parent / "public"
PIXEL_ID = "DBLO06JC77U0QLCJSSEG"

PIXEL = f'''<!-- TikTok Pixel Code -->
<script>
!function (w, d, t) {{
  w.TiktokAnalyticsObject=t;var ttq=w[t]=w[t]||[];ttq.methods=["page","track","identify","instances","debug","on","off","once","ready","alias","group","enableCookie","disableCookie","holdConsent","revokeConsent","grantConsent"],ttq.setAndDefer=function(t,e){{t[e]=function(){{t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}}};for(var i=0;i<ttq.methods.length;i++)ttq.setAndDefer(ttq,ttq.methods[i]);ttq.load=function(e,n){{var r="https://analytics.tiktok.com/i18n/pixel/events.js";ttq._i=ttq._i||{{}},ttq._i[e]=[],ttq._i[e]._u=r,ttq._t=ttq._t||{{}},ttq._t[e]=+new Date,ttq._o=ttq._o||{{}},ttq._o[e]=n||{{}};n=document.createElement("script");n.type="text/javascript";n.async=!0;n.src=r+"?sdkid="+e+"&lib="+t;e=document.getElementsByTagName("script")[0];e.parentNode.insertBefore(n,e)}};
  ttq.load("{PIXEL_ID}");
  ttq.page();
}}(window, document, "ttq");
</script>
<!-- End TikTok Pixel Code -->'''

DISCLOSURE = (
    "We use TikTok Pixel to measure visits and interactions from TikTok "
    "content and ads. It may use cookies or similar technologies to collect "
    "browser or device information and page activity."
)


def main():
    if not PUBLIC.is_dir():
        sys.exit(f"Generated site directory not found: {PUBLIC}")

    updated = 0
    for path in PUBLIC.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        original = text

        if "<!-- TikTok Pixel Code -->" not in text:
            text, count = re.subn(
                r"</head\s*>",
                PIXEL + "\n</head>",
                text,
                count=1,
                flags=re.IGNORECASE,
            )
            if not count:
                print(f"Warning: no </head> found in {path}", file=sys.stderr)
                continue

        if path.relative_to(PUBLIC).as_posix() == "privacy/index.html":
            if DISCLOSURE not in text:
                if "</main>" in text:
                    text = text.replace(
                        "</main>",
                        f"    <h2>TikTok Pixel</h2>\n    <p>{DISCLOSURE}</p>\n  </main>",
                        1,
                    )
                else:
                    print(f"Warning: no </main> found in {path}", file=sys.stderr)

            today = datetime.now(timezone.utc).date().isoformat()
            text = re.sub(
                r"Last updated \d{4}-\d{2}-\d{2}\.",
                f"Last updated {today}.",
                text,
                count=1,
            )

        if text != original:
            path.write_text(text, encoding="utf-8")
            updated += 1

    print(f"TikTok Pixel {PIXEL_ID} ensured in generated HTML; updated {updated} page(s)")


if __name__ == "__main__":
    main()
