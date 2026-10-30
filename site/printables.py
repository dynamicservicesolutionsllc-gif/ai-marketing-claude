#!/usr/bin/env python3
"""Generate the email sign-up printable: assets/printables/small-kitchen-measuring-checklist.pdf.

Run after editing the checklist text: `pip install reportlab` (once), then `python3 printables.py`.
build.py copies the PDF into public/printables/. The PDF contains no Amazon links: the Associates
agreement doesn't allow affiliate links in offline material or downloadable files.
"""
from pathlib import Path

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets" / "printables" / "small-kitchen-measuring-checklist.pdf"
ORANGE, INK, MUTED, CREAM, LINE = HexColor("#c8643b"), HexColor("#2b2622"), HexColor("#6f665d"), HexColor("#fbf8f3"), HexColor("#d9cfc2")

SECTIONS = [
    ("Drawers", "For utensil trays, bins and liners", ["Inside width", "Inside depth (front to back)", "Usable height under the opening", "Hinges, rails or dividers in the way", "Longest utensil you store"]),
    ("Cabinets & pantry shelves", "For containers, risers, bins and turntables", ["Inside width", "Shelf depth", "Height between shelves", "Door swing / lip at the front", "Tallest jar or box you store"]),
    ("Under the sink", "For pull-out organizers and mats", ["Cabinet inside width", "Space left of the drain pipe", "Space right of the drain pipe", "Clearance below the drain trap", "Door opening (hinges, center post)"]),
    ("Counter & sink", "For dish racks and small appliances", ["Free counter width beside the sink", "Free counter depth", "Sink opening, shorter side", "Clearance under upper cabinets", "Distance to nearest outlet"]),
    ("Fridge side & walls", "For magnetic racks and wall storage", ["Clear width beside the fridge", "Magnet sticks to the fridge? (Y / N)", "Free wall space (width x height)"]),
]
TIPS = ["Measure the inside, not the outside: walls, rails and hinges eat space.",
        "Leave a little clearance so drawers and doors still open smoothly.",
        "Write down your tallest and widest items, not just the space.",
        "Compare with the current product listing before you buy; sizes change."]


def main():
    for name in ("DejaVuSans", "DejaVuSans-Bold", "DejaVuSerif-Bold"):
        pdfmetrics.registerFont(TTFont(name, str(ROOT / "fonts" / f"{name}.ttf")))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=letter)
    c.setTitle("Small-Kitchen Measuring Checklist")
    c.setAuthor("Kitchen Finds & Favorites")
    w, h = letter
    c.setFillColor(CREAM)
    c.rect(0, 0, w, h, stroke=0, fill=1)
    c.setFillColor(ORANGE)
    c.rect(0, h - 14, w, 14, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont("DejaVuSerif-Bold", 24)
    c.drawString(40, h - 58, "Small-Kitchen Measuring Checklist")
    c.setFont("DejaVuSans", 10.5)
    c.setFillColor(MUTED)
    c.drawString(40, h - 76, "Measure once, buy the right size. Fill this in with a tape measure before you shop")
    c.drawString(40, h - 90, "for organizers, racks or small appliances.")
    y = h - 120
    col_w = (w - 80 - 20) / 2
    x_positions = [40, 40 + col_w + 20]
    col, y_start = 0, y
    ys = [y, y]
    for title, sub, rows in SECTIONS:
        col = 0 if ys[0] >= ys[1] else 1
        x, y = x_positions[col], ys[col]
        c.setFillColor(ORANGE)
        c.setFont("DejaVuSans-Bold", 12.5)
        c.drawString(x, y, title.upper())
        c.setFillColor(MUTED)
        c.setFont("DejaVuSans", 8.5)
        c.drawString(x, y - 12, sub)
        y -= 30
        for r in rows:
            c.setStrokeColor(MUTED)
            c.setLineWidth(0.8)
            c.rect(x, y - 2, 9, 9, stroke=1, fill=0)
            c.setFillColor(INK)
            c.setFont("DejaVuSans", 9.5)
            c.drawString(x + 15, y, r)
            c.setStrokeColor(LINE)
            c.line(x + 15, y - 9, x + col_w, y - 9)
            c.setFillColor(MUTED)
            c.setFont("DejaVuSans", 7.5)
            if "(Y / N)" not in r:
                c.drawRightString(x + col_w, y, "in / cm")
            y -= 27
        ys[col] = y - 14
    y = min(ys) - 4
    c.setFillColor(Color(0.78, 0.39, 0.23, alpha=0.08))
    c.roundRect(40, y - 92, w - 80, 96, 10, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont("DejaVuSans-Bold", 11)
    c.drawString(56, y - 16, "Before you buy")
    c.setFont("DejaVuSans", 9.5)
    for i, t in enumerate(TIPS):
        c.drawString(56, y - 34 - i * 15, f"•  {t}")
    c.setFillColor(MUTED)
    c.setFont("DejaVuSans", 8.5)
    c.drawCentredString(w / 2, 30, "Kitchen Finds & Favorites · kitchenfindsfavorites.com · Free to print for personal use")
    c.showPage()
    c.save()
    print(f"Wrote {OUT}")


TG_OUT = ROOT / "assets" / "printables" / "thanksgiving-hosting-timeline.pdf"
# Food-safety figures follow USDA guidance (fridge thawing, 165°F, leftovers).
TG_STEPS = [
    ("3 weeks before", ["Settle the guest count and the menu", "Check you have a roasting pan, a meat thermometer and serving dishes", "Order any tools or dishes you're missing", "Order or buy the turkey (allow about 1 lb per guest)"]),
    ("2 weeks before", ["Shop for pantry items: broth, canned goods, spices, baking supplies", "Plan the oven schedule: what bakes when, and what can go in a slow cooker", "Make and freeze pie dough or rolls"]),
    ("1 week before", ["Clear fridge space for the turkey and make-ahead dishes", "Print or bookmark every recipe", "Write the shopping list for fresh ingredients"]),
    ("Thaw time (frozen turkey)", ["Thaw in the fridge: about 1 day for every 4 to 5 lb", "A 16 lb turkey needs about 4 days, so start the Sunday before", "Keep it on a tray on the bottom shelf"]),
    ("2 days before", ["Buy fresh produce, dairy and herbs", "Make cranberry sauce", "Chop onions, celery and herbs for stuffing"]),
    ("1 day before", ["Bake pies", "Assemble make-ahead sides", "Set the table and lay out serving dishes and utensils"]),
    ("Thanksgiving Day", ["Count back from dinner time to set when the turkey goes in", "Check the turkey with a thermometer: 165°F in the thickest part", "Rest the turkey about 30 minutes; make gravy from the drippings", "Keep mashed potatoes or stuffing warm in a slow cooker"]),
    ("After dinner", ["Refrigerate leftovers within 2 hours", "Use leftovers within 3 to 4 days, or freeze them"]),
]


def thanksgiving_timeline():
    c = canvas.Canvas(str(TG_OUT), pagesize=letter)
    c.setTitle("Thanksgiving Hosting Timeline")
    c.setAuthor("Kitchen Finds & Favorites")
    w, h = letter
    c.setFillColor(CREAM)
    c.rect(0, 0, w, h, stroke=0, fill=1)
    c.setFillColor(ORANGE)
    c.rect(0, h - 14, w, 14, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont("DejaVuSerif-Bold", 24)
    c.drawString(40, h - 58, "Thanksgiving Hosting Timeline")
    c.setFont("DejaVuSans", 10.5)
    c.setFillColor(MUTED)
    c.drawString(40, h - 76, "A countdown from three weeks out to dinner time. Check things off as you go.")
    col_w = (w - 80 - 20) / 2
    x_positions = [40, 40 + col_w + 20]
    ys = [h - 106, h - 106]
    for i, (title, rows) in enumerate(TG_STEPS):
        col = i // 4
        x, y = x_positions[col], ys[col]
        c.setFillColor(ORANGE)
        c.setFont("DejaVuSans-Bold", 12)
        c.drawString(x, y, title.upper())
        y -= 20
        for r in rows:
            c.setStrokeColor(MUTED)
            c.setLineWidth(0.8)
            c.rect(x, y - 2, 9, 9, stroke=1, fill=0)
            c.setFillColor(INK)
            c.setFont("DejaVuSans", 8.8)
            line = ""
            for word in r.split():
                trial = (line + " " + word).strip()
                if pdfmetrics.stringWidth(trial, "DejaVuSans", 8.8) > col_w - 18:
                    c.drawString(x + 15, y, line)
                    y -= 12
                    line = word
                else:
                    line = trial
            c.drawString(x + 15, y, line)
            y -= 18
        ys[col] = y - 12
    y = min(ys) - 4
    c.setFillColor(Color(0.78, 0.39, 0.23, alpha=0.08))
    c.roundRect(40, y - 64, w - 80, 68, 10, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont("DejaVuSans-Bold", 11)
    c.drawString(56, y - 16, "Notes for your dinner")
    c.setStrokeColor(LINE)
    for i in range(2):
        c.line(56, y - 36 - i * 18, w - 56, y - 36 - i * 18)
    c.setFillColor(MUTED)
    c.setFont("DejaVuSans", 8.5)
    c.drawCentredString(w / 2, 44, "Kitchen tools for the day: kitchenfindsfavorites.com/gifts/thanksgiving-kitchen-checklist/")
    c.drawCentredString(w / 2, 30, "Kitchen Finds & Favorites · kitchenfindsfavorites.com · Free to print for personal use")
    c.showPage()
    c.save()
    print(f"Wrote {TG_OUT}")


if __name__ == "__main__":
    main()
    thanksgiving_timeline()
