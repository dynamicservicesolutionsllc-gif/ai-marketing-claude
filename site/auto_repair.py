#!/usr/bin/env python3
"""Conservative automatic repair for Git-managed KFF static HTML.

Only edits local source files explicitly supplied by KFF_SITE_ROOT.
No fabricated products, Amazon links, product claims, SEO keywords, or prices.
An unchanged source file is never uploaded.
"""
import json, os, re, html, pathlib, sys
from html.parser import HTMLParser

ROOT=pathlib.Path(os.environ.get("KFF_SITE_ROOT","")).resolve() if os.environ.get("KFF_SITE_ROOT") else None
REPORT=pathlib.Path(__file__).parent/"repair-report.json"
DISCLOSURE="As an Amazon Associate I earn from qualifying purchases."

class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.title=[];self.h1=[];self.in_title=False;self.in_h1=False;self.links=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=="title":self.in_title=True
        if tag=="h1":self.in_h1=True
        if tag=="a" and a.get("href"):self.links.append(a["href"])
    def handle_endtag(self,tag):
        if tag=="title":self.in_title=False
        if tag=="h1":self.in_h1=False
    def handle_data(self,data):
        if self.in_title:self.title.append(data)
        if self.in_h1:self.h1.append(data)

def repair(path):
    original=path.read_text(encoding="utf-8")
    if not re.search(r"<html\b",original,re.I) or not re.search(r"</head\s*>",original,re.I):
        return [],"not-standard-html"
    p=Page();p.feed(original)
    text=original
    changes=[]
    h1=html.unescape(" ".join(p.h1)).strip()
    title=html.unescape(" ".join(p.title)).strip()
    if not title and h1 and len(h1)<=100:
        text=re.sub(r"</head\s*>","<title>"+html.escape(h1)+"</title>\n</head>",text,count=1,flags=re.I)
        changes.append("missing-title-from-existing-h1")
    if not re.search(r'<meta\s+[^>]*name\s*=\s*["\\']description["\\']',text,re.I) and h1 and len(h1)>=25:
        # No invented marketing copy: use existing on-page H1 exactly.
        description=h1[:155]
        text=re.sub(r"</head\s*>",'<meta name="description" content="'+html.escape(description,quote=True)+'">\n</head>',text,count=1,flags=re.I)
        changes.append("missing-description-from-existing-h1")
    # Add disclosure only when page already has a verified-form tagged Amazon link.
    tagged=any(re.search(r"^https?://(?:www\.)?amazon\.com/[^\s]*[?&](?:amp;)?tag=(?:kitchenfi0fde-20|kfffacebook-20)(?:&|$)",u,re.I) for u in p.links)
    plain=html.unescape(re.sub(r"<[^>]*>"," ",text)).lower()
    if tagged and DISCLOSURE.lower() not in plain:
        # Simple addition near the start of the body; site CSS handles typography.
        text=re.sub(r"<body([^>]*)>",lambda m:m.group(0)+'\n<p class="affiliate-disclosure">#ad '+DISCLOSURE+'</p>',text,count=1,flags=re.I)
        if text!=original:changes.append("missing-associate-disclosure")
    if not changes:return [],"no-safe-change"
    if os.environ.get("KFF_REPAIR_DRY_RUN","1")!="0":
        return changes,"dry-run"
    path.write_text(text,encoding="utf-8")
    return changes,"modified"

def main():
    report={"root":str(ROOT) if ROOT else None,"files":[],"status":"source-unavailable"}
    if not ROOT or not ROOT.is_dir():
        REPORT.write_text(json.dumps(report,indent=2)+"\n")
        print("No site-source directory: no live repairs were attempted.")
        return
    report["status"]="processed"
    for path in sorted(ROOT.rglob("*.html")):
        if path.is_symlink() or not path.is_file() or len(path.relative_to(ROOT).parts)>8 or path.stat().st_size>750000:continue
        try:
            changes,status=repair(path)
            if changes:report["files"].append({"path":str(path.relative_to(ROOT)),"changes":changes,"status":status})
        except Exception as exc:
            report["files"].append({"path":str(path.relative_to(ROOT)),"status":"error","error":str(exc)[:120]})
    REPORT.write_text(json.dumps(report,indent=2)+"\n")
    print("Repair candidates:",len(report["files"]))
    if any(f["status"]=="error" for f in report["files"]):sys.exit(1)
if __name__=="__main__":main()
