#!/usr/bin/env python3
"""Add TikTok base, product-view, and affiliate-click tracking before deployment."""
from datetime import datetime, timezone
from pathlib import Path
import re
import sys

PUBLIC = Path(__file__).resolve().parent / "public"
PIXEL_ID = "DBLO06JC77U0QLCJSSEG"

PIXEL = f'''<!-- TikTok Pixel Code -->
<script>
!function (w, d, t) {{
  w.TiktokAnalyticsObject=t;var ttq=w[t]=w[t]||[];ttq.methods=["page","track","identify","instances","debug","on","off","once","ready","alias","group","enableCookie","disableCookie","holdConsent","revokeConsent","grantConsent"],ttq.setAndDefer=function(t,e){{t[e]=function(){{t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}}};for(var i=0;i<ttq.methods.length;i++)ttq.setAndDefer(ttq,ttq.methods[i]);ttq.instance=function(t){{for(var e=ttq._i[t]||[],n=0;n<ttq.methods.length;n++)ttq.setAndDefer(e,ttq.methods[n]);return e}},ttq.load=function(e,n){{var r="https://analytics.tiktok.com/i18n/pixel/events.js",o=n&&n.partner;ttq._i=ttq._i||{{}},ttq._i[e]=[],ttq._i[e]._u=r,ttq._t=ttq._t||{{}},ttq._t[e]=+new Date,ttq._o=ttq._o||{{}},ttq._o[e]=n||{{}};n=document.createElement("script");n.type="text/javascript";n.async=!0;n.src=r+"?sdkid="+e+"&lib="+t;e=document.getElementsByTagName("script")[0];e.parentNode.insertBefore(n,e)}};
  ttq.load("{PIXEL_ID}");
  ttq.page();
}}(window, document, "ttq");
</script>
<!-- End TikTok Pixel Code -->'''

PRODUCT_EVENTS = '''<!-- TikTok product events -->
<script>
  ttq.track('ViewContent', {
    content_id: window.location.pathname.replace(/^\\/+|\\/$/g, ''),
    content_type: 'product',
    content_name: document.title,
    currency: 'USD'
  });

  // Affiliate clicks are tracked site-wide by the separate handler below.
</script>
<!-- End TikTok product events -->'''

SITE_CLICK_EVENTS = '''<!-- TikTok affiliate click events -->
<script>
  document.addEventListener('click', function (event) {
    var link = event.target.closest && event.target.closest('a[href]');
    if (!link) return;
    var host;
    try { host = new URL(link.href, location.href).hostname.toLowerCase(); }
    catch (_) { return; }
    if (host !== 'amazon.com' && !host.endsWith('.amazon.com')) return;
    if (window.ttq) ttq.track('ClickButton', {
      content_type: 'affiliate_product',
      content_name: document.title
    });
  });
</script>
<!-- End TikTok affiliate click events -->'''

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
        relative = path.relative_to(PUBLIC).as_posix()

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

        # Replace the legacy product block so its old click listener cannot double count.
        text = re.sub(r"<!-- TikTok product events -->.*?<!-- End TikTok product events -->",
                      "", text, flags=re.DOTALL)
        text = re.sub(r"<!-- TikTok affiliate click events -->.*?<!-- End TikTok affiliate click events -->",
                      "", text, flags=re.DOTALL)
        events = (PRODUCT_EVENTS + "\n" if relative.startswith("picks/") else "") + SITE_CLICK_EVENTS
        text, count = re.subn(r"</body\s*>", lambda _: events + "\n</body>",
                              text, count=1, flags=re.IGNORECASE)
        if not count:
            print(f"Warning: no </body> found in {path}", file=sys.stderr)

        if relative == "privacy/index.html":
            if DISCLOSURE not in text and "</main>" in text:
                text = text.replace(
                    "</main>",
                    f"    <h2>TikTok Pixel</h2>\n    <p>{DISCLOSURE}</p>\n  </main>",
                    1,
                )
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

    print(f"TikTok Pixel and product events ensured; updated {updated} page(s)")


if __name__ == "__main__":
    main()
