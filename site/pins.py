#!/usr/bin/env python3
"""Build the Pinterest queue: 3–4 different pins per page (fresh image + title each), written to public/pins.json.

Pinterest rewards fresh pins even when they lead to the same page, so every buying guide and gift guide gets four
photo-based pin designs with different headlines, and every product gets its original pin plus two new designs
(one of which links to the product's section in its buying guide). Each pin links with UTM tags so clicks can be
attributed to Pinterest and to the individual pin (see track_js in build.py).

Images: public/img/pins/<pin id>.jpg (1000x1500, Pinterest 2:3). Guide photos are the licensed Unsplash header
photos in assets/guides/; product pins use only original graphics, never Amazon photos.

Queue order: `wave` 0 first (each page's lead pin, gift guides before buying guides before products), then waves 1–3.
The Pinterest routine pins the first entries whose `id` is not in its Posted Pins Log.
"""
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw

from graphics import ACCENTS, CREAM, INK, MUTED, ORANGE, _check, _fit, _font

ROOT = Path(__file__).resolve().parent
W, H = 1000, 1500
PIN_DISCLOSURE = "#ad As an Amazon Associate I earn from qualifying purchases."
GIFT_ACCENT = (150, 52, 52)
SMALL = {"a", "an", "and", "as", "at", "for", "in", "of", "on", "or", "the", "to", "with"}

# Hand-written hooks for the seasonal gift guides (variants b, c, d). No price claims.
GIFT_HOOKS = {
    "gifts-for-home-cooks": [
        ("GIFT IDEAS", "Kitchen Gifts They'll Use Every Week", "Useful Kitchen Gifts for Home Cooks: Tools They'll Use Every Week",
         "Skip the gadgets that end up in a closet. These are practical upgrades for people who cook every day, from an instant-read thermometer to a family-size air fryer."),
        ("FOR THE COOK WHO HAS EVERYTHING", "Practical Upgrades for Everyday Cooking", "Gift Ideas for the Home Cook Who Has Everything",
         "Upgrades of everyday tools tend to land best: a reliable thermometer, a precise baking scale and heat-resistant silicone mitts."),
        ("HOLIDAY GIFT GUIDE", "Gifts for Bakers, Grillers and Soup Lovers", "Gifts for Bakers, Grillers and Soup Lovers: A Practical Home Cook Gift Guide",
         "A baking scale for consistent bread, an instant-read thermometer for the holiday roast and an immersion blender kit for soup season.")],
    "first-apartment-kitchen-gifts": [
        ("HOUSEWARMING GIFTS", "Housewarming Gifts for a Small Kitchen", "Housewarming Gift Ideas for a Small Apartment Kitchen",
         "Useful basics sized for a small counter: a compact dish rack, an electric kettle and airtight containers for a first pantry."),
        ("KITCHEN STARTER KIT", "What Every First Kitchen Is Missing", "What Every First Apartment Kitchen Needs: Practical Gift Ideas",
         "Drying dishes, opening cans, storing leftovers. The everyday basics a first kitchen is almost always missing, all rental-friendly."),
        ("COOKING FOR ONE OR TWO", "Small-Space Kitchen Gifts That Get Used", "First Apartment Kitchen Gifts for Cooking for One or Two",
         "A 2-quart slow cooker, a glass kettle and a compact dish rack: gifts sized for a studio or first apartment.")],
    "stocking-stuffers-for-cooks": [
        ("STOCKING STUFFERS", "Small Gifts for People Who Love to Cook", "Stocking Stuffer Ideas for Home Cooks: Small Kitchen Tools They'll Use",
         "Compact, useful tools for the cook in your life: an instant-read thermometer, a milk frother, a sharp can opener and more."),
        ("FOR COFFEE LOVERS AND GRILLERS", "Stocking Stuffers for Coffee Lovers and Grillers", "Stocking Stuffers for Coffee Lovers and Grillers",
         "A handheld milk frother and a slide-lid coffee tumbler for coffee lovers, and an instant-read thermometer for the grill."),
        ("LITTLE GIFTS, BIG HELP", "Kitchen Gadgets Cooks Actually Use", "Kitchen Gadget Stocking Stuffers Cooks Actually Use",
         "Skip novelty gadgets. These small tools save time on everyday jobs like shredding chicken, frothing milk and checking doneness.")],
    "black-friday-kitchen-gifts": [
        ("BLACK FRIDAY SHOPPING LIST", "Kitchen Gifts Worth Putting on Your List", "Black Friday Shopping List: Practical Kitchen Gifts They'll Use Every Week",
         "Go into Black Friday with a short list: an air fryer, a 7-quart slow cooker, a personal blender and insulated tumblers people use every week."),
        ("CYBER MONDAY GIFT IDEAS", "Bigger Kitchen Gifts for Everyday Cooks", "Cyber Monday Kitchen Gift Ideas: Air Fryer, Slow Cooker, Blender and More",
         "Bigger gifts that earn their counter space: a compact 6-quart air fryer, a family-size slow cooker and a KitchenAid hand mixer."),
        ("GIFTS FOR EVERYONE ON YOUR LIST", "From Coffee Drinkers to Holiday Hosts", "Kitchen Gifts for Everyone on Your List: Coffee Drinkers, Bakers and Hosts",
         "A glass kettle for tea and coffee drinkers, a hand mixer for bakers and a big slow cooker for the family holiday host.")],
    "thanksgiving-kitchen-checklist": [
        ("THANKSGIVING PREP", "Tools to Have Before Thanksgiving Day", "Thanksgiving Prep: Kitchen Tools to Have Before the Big Day",
         "A meat thermometer for the turkey, a fat separator for gravy and a slow cooker to free up the oven for sides."),
        ("FIRST TIME HOSTING?", "The Thanksgiving Host's Kitchen Checklist", "First Time Hosting Thanksgiving? The Kitchen Tools That Make It Easier",
         "Hosting is mostly a timing problem. These tools take the guesswork out of the turkey and keep the sides warm until dinner."),
        ("SMOOTHER GRAVY, JUICIER TURKEY", "Thanksgiving Turkey and Gravy Tools", "Thanksgiving Turkey and Gravy Tools: Thermometer, Fat Separator and More",
         "Know when the turkey is done with an instant-read thermometer, then pour the drippings through a fat separator for smoother gravy.")],
    "gifts-for-bakers": [
        ("COOKIE SEASON", "Baking Tools for Cookie Season", "Holiday Baking Tools for Cookie Season: Practical Gifts for Bakers",
         "Fresh baking sheets, silicone baking mats and a big pastry mat for rolling out sugar cookies and pie crust."),
        ("GIFTS FOR BAKERS", "Practical Upgrades Every Baker Uses", "Practical Gifts for Bakers: Upgrades They'll Use Every Batch",
         "A digital scale for consistent results, a hand mixer that stores in a drawer and glass measuring cups for every recipe."),
        ("PIE AND COOKIE HELPERS", "Roll, Measure and Bake With Less Mess", "Pie and Cookie Baking Helpers: Pastry Mat, Scale and Baking Sheets",
         "A 28 by 20 inch pastry mat with printed measurements makes rolling pie crust and cookies neater and easier to size.")],
}
# Pin wording for gift guides that aren't gift lists (e.g. a hosting checklist). Default is the gift wording.
GUIDE_PIN_LABELS = {
    "thanksgiving-kitchen-checklist": ("HOSTING CHECKLIST", "See the checklist →", "Kitchen Tools"),
}
CATEGORY_TAGS = {
    "organization": "#kitchenorganization #smallkitchen #organizedhome",
    "gadgets": "#kitchengadgets #cookingtips #kitchentools",
    "appliances": "#smallappliances #smallkitchen #kitchenessentials",
    "drinkware": "#waterbottle #tumbler #hydration",
}


def title_case(text):
    words = text.split()
    return " ".join(w if (i and w.lower() in SMALL) else w[:1].upper() + w[1:] for i, w in enumerate(words))


def article(noun):
    return "an" if noun[:1].lower() in "aeiou" else "a"


def clip(text, n):
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0].rstrip(",;:–-") + "…"


def description(body, tags):
    """Pin description: disclosure first, then 1–3 sentences, then hashtags; trimmed by sentence to 500 chars."""
    sentences = re.split(r"(?<=[.!?])\s+", body.strip())
    while sentences:
        text = f"{PIN_DISCLOSURE} {' '.join(sentences)} {tags}".strip()
        if len(text) <= 500:
            return text
        sentences.pop()
    return f"{PIN_DISCLOSURE} {tags}"[:500]


def first_sentences(text, n=2):
    return " ".join(re.split(r"(?<=[.!?])\s+", text.strip())[:n])


# ------------------------------------------------------------------ drawing
def _photo(path, w, h):
    im = Image.open(path).convert("RGB")
    sw, sh = im.size
    if sw / sh > w / h:  # too wide: crop sides
        nw = round(sh * w / h)
        im = im.crop(((sw - nw) // 2, 0, (sw - nw) // 2 + nw, sh))
    else:
        nh = round(sw * h / w)
        im = im.crop((0, (sh - nh) // 2, sw, (sh - nh) // 2 + nh))
    return im.resize((w, h), Image.LANCZOS)


def _rounded(im, r):
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.size[0], im.size[1]], r, fill=255)
    return im, mask


def _cta(d, y, text, fill=ORANGE, ink="white"):
    d.rounded_rectangle([190, y, W - 190, y + 108], 54, fill=fill)
    d.text((W / 2, y + 54), text, font=_font("DejaVuSans-Bold.ttf", 44), fill=ink, anchor="mm")


def _footer(d, color, text="KITCHENFINDSFAVORITES.COM"):
    d.text((W / 2, H - 55), text, font=_font("DejaVuSans-Bold.ttf", 28), fill=color, anchor="mm")


def guide_pin(photo, style, kicker, headline, accent, checks=(), number=None, cta="Read the guide →"):
    """Four looks so a page's pins don't read as duplicates: a) photo top, b) dark, c) colour + checklist, d) big number."""
    if style == "a":
        im = Image.new("RGB", (W, H), CREAM)
        im.paste(_photo(photo, W, 760), (0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([60, 700, W - 60, 790], 22, fill=accent)
        f, lines = _fit(d, kicker, "DejaVuSans-Bold.ttf", 36, W - 180, 1)
        d.text((W / 2, 745), lines[0], font=f, fill="white", anchor="mm")
        f, lines = _fit(d, headline, "DejaVuSerif-Bold.ttf", 84, W - 120, 3)
        d.multiline_text((W / 2, 1010), "\n".join(lines), font=f, fill=INK, anchor="mm", align="center", spacing=16)
        _cta(d, 1240, cta)
        _footer(d, MUTED)
    elif style == "b":
        im = Image.new("RGB", (W, H), INK)
        d = ImageDraw.Draw(im)
        f, lines = _fit(d, kicker, "DejaVuSans-Bold.ttf", 38, W - 140, 2)
        d.multiline_text((W / 2, 150), "\n".join(lines), font=f, fill=(224, 122, 79), anchor="mm", align="center", spacing=6)
        f, lines = _fit(d, headline, "DejaVuSerif-Bold.ttf", 90, W - 120, 3)
        d.multiline_text((W / 2, 420), "\n".join(lines), font=f, fill=CREAM, anchor="mm", align="center", spacing=18)
        ph, mask = _rounded(_photo(photo, 880, 560), 30)
        im.paste(ph, (60, 680), mask)
        d = ImageDraw.Draw(im)
        _cta(d, 1290, cta)
        _footer(d, (179, 169, 157))
    elif style == "c":
        im = Image.new("RGB", (W, H), accent)
        d = ImageDraw.Draw(im)
        f, lines = _fit(d, kicker, "DejaVuSans-Bold.ttf", 36, W - 140, 2)
        d.multiline_text((W / 2, 120), "\n".join(lines), font=f, fill="white", anchor="mm", align="center", spacing=6)
        f, lines = _fit(d, headline, "DejaVuSerif-Bold.ttf", 80, W - 120, 3)
        d.multiline_text((W / 2, 330), "\n".join(lines), font=f, fill="white", anchor="mm", align="center", spacing=16)
        ph, mask = _rounded(_photo(photo, 880, 400), 28)
        im.paste(ph, (60, 520), mask)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([60, 950, W - 60, 1270], 28, fill=CREAM)
        y = 985
        for item in list(checks)[:4]:
            f, lines = _fit(d, item, "DejaVuSans.ttf", 40, W - 280, 1)
            _check(d, 125, y + 30, 20)
            d.text((170, y + 30), lines[0], font=f, fill=INK, anchor="lm")
            y += 72
        _cta(d, 1300, cta, fill=CREAM, ink=INK)
        _footer(d, (255, 255, 255))
    else:  # "d"
        im = Image.new("RGB", (W, H), CREAM)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, 24], fill=accent)
        if number:
            d.text((W / 2, 250), str(number), font=_font("DejaVuSerif-Bold.ttf", 260), fill=ORANGE, anchor="mm")
        f, lines = _fit(d, kicker, "DejaVuSans-Bold.ttf", 36, W - 140, 2)
        d.multiline_text((W / 2, 445), "\n".join(lines), font=f, fill=accent, anchor="mm", align="center", spacing=6)
        f, lines = _fit(d, headline, "DejaVuSerif-Bold.ttf", 82, W - 120, 3)
        d.multiline_text((W / 2, 640), "\n".join(lines), font=f, fill=INK, anchor="mm", align="center", spacing=16)
        im.paste(_photo(photo, W, 470), (0, 840))
        d = ImageDraw.Draw(im)
        _cta(d, 1330, cta)
    return im


def product_pin(g, accent, style, headline, kicker):
    """Two new looks for a product (original pin stays as variant a): b) dark, c) colour."""
    bg, fg, sub = (INK, CREAM, (224, 122, 79)) if style == "b" else (accent, (255, 255, 255), (255, 255, 255))
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    f, lines = _fit(d, kicker.upper(), "DejaVuSans-Bold.ttf", 40, W - 160, 2)
    d.multiline_text((W / 2, 170), "\n".join(lines), font=f, fill=sub, anchor="mm", align="center", spacing=6)
    f, lines = _fit(d, headline, "DejaVuSerif-Bold.ttf", 96, W - 120, 3)
    d.multiline_text((W / 2, 470), "\n".join(lines), font=f, fill=fg, anchor="mm", align="center", spacing=18)
    panel = CREAM if style == "c" else (58, 52, 47)
    text = INK if style == "c" else CREAM
    d.rounded_rectangle([60, 760, W - 60, 1150], 30, fill=panel)
    y = 810
    for pt in g["points"][:3]:
        f, lines = _fit(d, pt, "DejaVuSans.ttf", 46, W - 280, 1)
        _check(d, 130, y + 30, 22)
        d.text((180, y + 30), lines[0], font=f, fill=text, anchor="lm")
        y += 110
    _cta(d, 1220, "See why we picked it →", fill=ORANGE if style == "b" else CREAM, ink="white" if style == "b" else INK)
    d.text((W / 2, 1420), "#ad · As an Amazon Associate I earn from qualifying purchases",
           font=_font("DejaVuSans.ttf", 24), fill=(179, 169, 157) if style == "b" else (255, 255, 255), anchor="mm")
    return im


# ------------------------------------------------------------------ queue
def build(data, out, url, force=False):
    from build import gift_path, guide_path, page_path, gift_products, guide_products  # noqa: circular-safe at call time
    img_dir = out / "img" / "pins"
    img_dir.mkdir(parents=True, exist_ok=True)
    assets = ROOT / "assets" / "guides"
    year = max(p["added"] for p in data["products"])[:4]
    pins = []

    def add(pid, kind, page_key, page_url, image_url, title, desc, board, wave, render=None, fragment=""):
        path = img_dir / f"{pid}.jpg"
        if render and (force or not path.exists()):
            render().save(path, "JPEG", quality=86, optimize=True, progressive=True)
        link = f"{page_url}?utm_source=pinterest&utm_medium=social&utm_campaign={pid}{fragment}"
        pins.append({"id": pid, "kind": kind, "page": page_key, "page_url": page_url, "link": link,
                     "image": image_url or f"{url}/img/pins/{pid}.jpg", "title": clip(title, 100),
                     "description": desc, "board": board, "wave": wave})

    # Gift guides (seasonal: first in each wave)
    for key, gg in data.get("gift_guides", {}).items():
        items = gift_products(data, key)
        page = f"{url}/{gift_path(key)}"
        photo = assets / f"{key}.jpg"
        tags = gg.get("hashtags", "#giftideas #kitchengifts")
        board = data["site"].get("gift_board", "Holiday Gift Ideas for Cooks")
        n = len(items)
        label, cta, noun = GUIDE_PIN_LABELS.get(key, ("HOLIDAY GIFT GUIDE", "See the gift ideas →", "Useful Ideas"))
        add(f"gift-{key}-a", "gift", key, page, None, f"{gg['title']}: {n} {noun} ({year})",
            description(first_sentences(gg["intro"]), tags), board, 0,
            lambda label=label, cta=cta: guide_pin(photo, "a", label, gg["title"], GIFT_ACCENT, cta=cta))
        for i, (style, (kicker, headline, title, body)) in enumerate(zip("bcd", GIFT_HOOKS.get(key, []))):
            add(f"gift-{key}-{style}", "gift", key, page, None, title, description(body, tags), board, i + 1,
                (lambda st=style, k=kicker, h=headline, cta=cta: guide_pin(photo, st, k, h, GIFT_ACCENT,
                                                                             checks=[x["award"] for x in items], number=n,
                                                                             cta=cta)))

    # Buying guides
    for key, s in data["subcategories"].items():
        items = guide_products(data["products"], key)
        page = f"{url}/{guide_path(key)}"
        photo = assets / f"{key}.jpg"
        accent = ACCENTS.get(s["category"], ORANGE)
        noun = s.get("noun", "Kitchen Organizer")
        tags = s.get("hashtags", CATEGORY_TAGS.get(s["category"], ""))
        board = s.get("board", "Small Kitchen Gadgets We Love")
        n = len(items)
        add(f"guide-{key}-a", "guide", key, page, None, f"{s['title']} ({year}): {n} Picks Compared",
            description(f"{s['description']} See all {n} picks and how they compare.", tags), board, 0,
            lambda: guide_pin(photo, "a", f"{n} PICKS COMPARED", s["title"], accent))
        add(f"guide-{key}-b", "guide", key, page, None, f"How to Choose {article(noun)} {noun} for a Small Kitchen",
            description(first_sentences(s.get("quick_answer") or s["intro"]), tags), board, 1,
            lambda: guide_pin(photo, "b", "SMALL-KITCHEN BUYING GUIDE", f"How to Choose {article(noun)} {noun}", accent))
        if s.get("measure"):
            verb = "Measure" if "measure" in s.get("measure_heading", "measure").lower() else "Check"
            k = len(s["measure"])
            names = [m[0] for m in s["measure"]]
            add(f"guide-{key}-c", "guide", key, page, None, f"Before You Buy {article(noun)} {noun}: {verb} These {k} Things",
                description(f"{s.get('measure_note', '')} {verb} these first: {', '.join(names).lower()}.", tags), board, 2,
                lambda: guide_pin(photo, "c", f"BEFORE YOU BUY {article(noun).upper()} {noun.upper()}",
                                  f"{verb} These {k} Things First", accent, checks=names))
        if s.get("types"):
            t = len(s["types"])
            names = [x["name"] for x in s["types"]]
            add(f"guide-{key}-d", "guide", key, page, None, f"Which {noun} Is Right for You? {t} Types Compared",
                description(f"Compare {', '.join(names).lower()}, with who should choose or skip each type.", tags), board, 3,
                lambda: guide_pin(photo, "d", "COMPARE THE TYPES", f"Which {noun} Fits Your Kitchen?", accent, number=t))

    # Products: original pin (a), plus dark (b) and colour (c) designs
    for p in sorted(data["products"], key=lambda q: q["added"]):
        asin, g = p["asin"], p["graphic"]
        page = f"{url}/{page_path(p)}"
        accent = ACCENTS.get(p["category"], ORANGE)
        tags = CATEGORY_TAGS.get(p["category"], "")
        pin = p.get("pin") or {}
        board = pin.get("board") or {"organization": "Kitchen Organization Must-Haves", "drinkware": "Drinkware & Tumblers We Love"}.get(p["category"], "Small Kitchen Gadgets We Love")
        if pin:
            add(asin, "product", asin, page, f"{url}/img/{asin}.png", pin["title"], pin["description"], board, 0)
        award = title_case(p.get("award", "Our pick"))
        # New designs go to the product's keyword board (e.g. "Pantry Organization Ideas"); the original pin keeps its board.
        board = data["subcategories"][p["subcategory"]].get("board", board)
        add(f"{asin}-b", "product", asin, page, None, f"{award}: {p['name']}", description(p["blurb"], tags), board, 2,
            lambda g=g, a=accent, aw=award, lb=g["label"]: product_pin(g, a, "b", aw, lb))
        sub = data["subcategories"][p["subcategory"]]
        guide_page = f"{url}/{guide_path(p['subcategory'])}"
        add(f"{asin}-c", "product", asin, guide_page, None, f"{g['headline']}: {g['label']} in Our {sub['title'].replace('Best ', '')} Guide",
            description(f"{p['blurb']} See how it compares in our full guide.", tags), board, 3,
            lambda g=g, a=accent, lb=g["label"]: product_pin(g, a, "c", "Why It Made Our List", lb), fragment=f"#{asin}")

    kind_order = {"gift": 0, "guide": 1, "product": 2}
    pins.sort(key=lambda x: (x["wave"], kind_order[x["kind"]]))
    for i, x in enumerate(pins):
        x["order"] = i + 1
    return pins


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    from build import load, OUT
    data, errors = load()
    print(len(build(data, OUT, data["site"]["url"], force="--force" in sys.argv)), "pins")
