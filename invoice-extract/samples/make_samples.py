#!/usr/bin/env python3
"""Generate sample invoice scans for exercising the tool.

These are synthetic but built to look like what actually comes off a scanner:
slightly rotated, speckled, JPEG-softened, with the layout quirks that make
real invoices hard — a PO number sitting next to the invoice number, a prior
balance above the amount due, a statement that isn't an invoice at all.

    python samples/make_samples.py

Writes PNGs into samples/scans/. Requires Pillow (`pip install pillow`).
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent / "scans"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
W, H = 1275, 1650  # 8.5x11 at 150 dpi


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_DIR / name
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size)


BODY = lambda s=22: font("DejaVuSans.ttf", s)  # noqa: E731
BOLD = lambda s=22: font("DejaVuSans-Bold.ttf", s)  # noqa: E731
MONO = lambda s=22: font("DejaVuSansMono.ttf", s)  # noqa: E731


class Page:
    def __init__(self) -> None:
        self.img = Image.new("L", (W, H), 255)
        self.d = ImageDraw.Draw(self.img)
        self.y = 90

    def text(self, x, s, f=None, dy=34, fill=30):
        self.d.text((x, self.y), s, font=f or BODY(), fill=fill)
        self.y += dy
        return self

    def at(self, x, y, s, f=None, fill=30):
        self.d.text((x, y), s, font=f or BODY(), fill=fill)
        return self

    def rule(self, x0=90, x1=W - 90, pad=10, width=2):
        self.y += pad
        self.d.line([(x0, self.y), (x1, self.y)], fill=90, width=width)
        self.y += pad + 8
        return self

    def gap(self, n=20):
        self.y += n
        return self

    def scan(self, seed: int, quality: int = 55, blur: float = 0.6) -> Image.Image:
        """Degrade the clean render into something scanner-shaped."""
        rng = random.Random(seed)
        img = self.img

        # Page skew — a sheet is never square on the glass.
        img = img.rotate(
            rng.uniform(-0.7, 0.7), resample=Image.BICUBIC, fillcolor=255, expand=False
        )
        img = img.filter(ImageFilter.GaussianBlur(blur))

        # Sensor speckle and a touch of uneven illumination.
        px = img.load()
        for _ in range(int(W * H * 0.0025)):
            x, y = rng.randrange(W), rng.randrange(H)
            px[x, y] = max(0, min(255, px[x, y] + rng.randint(-70, 45)))
        vign = Image.linear_gradient("L").resize((W, H)).point(lambda v: 246 + v // 28)
        img = Image.blend(img, Image.composite(img, vign, img.point(lambda v: v < 200)), 0.35)

        out = OUT / "tmp.jpg"
        img.convert("L").save(out, quality=quality)
        img = Image.open(out).convert("L")
        out.unlink()
        return img

    def save(self, name: str, seed: int, **kw) -> Path:
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / name
        self.scan(seed, **kw).save(path)
        print(f"  {path.relative_to(OUT.parent.parent)}")
        return path


def letterhead(p: Page, name: str, addr: list[str], title: str = "INVOICE") -> Page:
    p.text(90, name, BOLD(38), dy=44)
    for line in addr:
        p.text(90, line, BODY(20), dy=26)
    # Right-align the title and shrink it until it fits the margin, so a long
    # one like "STATEMENT OF ACCOUNT" doesn't run off the page.
    size = 46
    while size > 20:
        f = BOLD(size)
        width = p.d.textlength(title, font=f)
        if width <= 620:
            break
        size -= 2
    p.at(W - 90 - width, 92, title, f)
    return p


def bill_to(p: Page, lines: list[str]) -> Page:
    p.gap(14)
    p.text(90, "BILL TO", BOLD(20), dy=30)
    for line in lines:
        p.text(90, line, BODY(21), dy=27)
    return p


def meta(p: Page, y: int, rows: list[tuple[str, str]]) -> None:
    """The header block on the right — where the wrong number gets grabbed."""
    for label, value in rows:
        p.at(W - 470, y, label, BODY(20), fill=70)
        p.at(W - 250, y, value, MONO(21))
        y += 30


def table(p: Page, rows: list[tuple[str, str, str, str]]) -> None:
    p.gap(26)
    p.at(90, p.y, "DESCRIPTION", BOLD(19), fill=70)
    p.at(720, p.y, "QTY", BOLD(19), fill=70)
    p.at(850, p.y, "UNIT", BOLD(19), fill=70)
    p.at(1050, p.y, "AMOUNT", BOLD(19), fill=70)
    p.y += 26
    p.rule(pad=4)
    for desc, qty, unit, amt in rows:
        p.at(90, p.y, desc, BODY(21))
        p.at(720, p.y, qty, MONO(21))
        p.at(850, p.y, unit, MONO(21))
        p.at(1050, p.y, amt, MONO(21))
        p.y += 32
    p.rule(pad=6)


def totals(p: Page, rows: list[tuple[str, str]], final: tuple[str, str]) -> None:
    # Labels start well left of the amount column: real invoices carry long
    # ones ("Payment received 07/06 - thank you") that must not collide.
    for label, value in rows:
        p.at(560, p.y, label, BODY(21), fill=60)
        p.at(1050, p.y, value, MONO(21))
        p.y += 30
    p.y += 6
    p.d.line([(550, p.y), (W - 90, p.y)], fill=60, width=2)
    p.y += 12
    p.at(560, p.y, final[0], BOLD(24))
    p.at(1010, p.y, final[1], BOLD(24))


# --------------------------------------------------------------------------
# The samples
# --------------------------------------------------------------------------


def sysco(name: str, invoice_no: str, seed: int, **kw):
    """Clean food-service invoice. Should code to Food Cost and pass."""
    p = Page()
    letterhead(p, "SYSCO CORPORATION", ["1390 Enclave Parkway", "Houston, TX 77077"])
    meta(p, 150, [
        ("Invoice No.", invoice_no),
        ("Invoice Date", "07/15/2026"),
        ("Customer No.", "884120"),
        ("P.O. Number", "PO-55831"),
        ("Terms", "Net 30"),
    ])
    bill_to(p, ["Riverside Inn", "1234 Harbor Blvd", "Portland, OR 97201"])
    table(p, [
        ("Produce - mixed case", "10", "60.00", "600.00"),
        ("Dry goods - assorted", "8", "50.00", "400.00"),
    ])
    totals(p, [("Subtotal", "1,000.00"), ("Tax", "80.00"), ("Freight", "20.00")],
           ("AMOUNT DUE", "$1,100.00"))
    return p.save(name, seed, **kw)


def grainger():
    """Vendor has no default account — coding depends on the line items."""
    p = Page()
    letterhead(p, "GRAINGER", ["100 Grainger Parkway", "Lake Forest, IL 60045"])
    meta(p, 150, [
        ("Invoice", "9481773265"),
        ("Date", "07/22/2026"),
        ("Account", "8829104"),
        ("Order No.", "1447-99820"),
    ])
    bill_to(p, ["Downtown Suites", "88 Fifth Street", "Portland, OR 97204"])
    table(p, [
        ("HVAC blower motor, 1/3 HP", "2", "184.50", "369.00"),
        ("Pleated air filter 20x25x1, case", "3", "42.00", "126.00"),
    ])
    totals(p, [("Subtotal", "495.00"), ("Tax", "39.60")], ("TOTAL DUE", "$534.60"))
    return p.save("grainger-9481773265.png", 7)


def city_water():
    """Utility bill with a prior balance above the amount due."""
    p = Page()
    letterhead(p, "CITY WATER & POWER", ["Municipal Services Division", "Portland, OR"],
               title="STATEMENT OF ACCOUNT")
    meta(p, 150, [
        ("Invoice Number", "88-201466"),
        ("Billing Date", "07/28/2026"),
        ("Service Period", "06/25 - 07/25"),
        ("Account Number", "4471-000-99"),
    ])
    bill_to(p, ["Riverside Inn", "1234 Harbor Blvd", "Portland, OR 97201"])
    table(p, [
        ("Electric usage - 18,420 kWh", "1", "1,884.60", "1,884.60"),
        ("Demand charge", "1", "210.00", "210.00"),
    ])
    totals(p, [
        ("Previous balance", "1,902.44"),
        ("Payment received 07/06 - thank you", "-1,902.44"),
        ("Subtotal", "2,094.60"),
        ("Utility tax", "109.56"),
    ], ("AMOUNT DUE", "$2,204.16"))
    return p.save("citywater-88-201466.png", 11)


def unknown_vendor():
    """Vendor not in the rules file — should be held, not guessed."""
    p = Page()
    letterhead(p, "CASCADE COMMERCIAL SERVICES LLC",
               ["4410 SE Powell Blvd", "Portland, OR 97206"])
    meta(p, 150, [
        ("Invoice #", "CCS-2026-0788"),
        ("Date", "08/01/2026"),
        ("PO", "—"),
    ])
    bill_to(p, ["Downtown Suites", "88 Fifth Street", "Portland, OR 97204"])
    table(p, [
        ("Quarterly window washing - exterior", "1", "1,450.00", "1,450.00"),
        ("Awning cleaning", "1", "275.00", "275.00"),
    ])
    totals(p, [("Subtotal", "1,725.00"), ("Tax", "0.00")], ("TOTAL", "$1,725.00"))
    return p.save("cascade-CCS-2026-0788.png", 13)


def statement():
    """A statement listing several invoices — not a payable document."""
    p = Page()
    letterhead(p, "STANDARD TEXTILE CO., INC.",
               ["One Knollcrest Drive", "Cincinnati, OH 45237"],
               title="MONTHLY STATEMENT")
    meta(p, 150, [
        ("Statement No.", "ST-0726-4471"),
        ("Statement Date", "07/31/2026"),
        ("Account", "HT-88412"),
    ])
    bill_to(p, ["Riverside Inn", "1234 Harbor Blvd", "Portland, OR 97201"])
    table(p, [
        ("Invoice 771204  06/28/2026", "", "", "2,140.00"),
        ("Invoice 773991  07/09/2026", "", "", "1,880.50"),
        ("Invoice 776310  07/24/2026", "", "", "960.00"),
    ])
    totals(p, [("Current", "960.00"), ("31-60 days", "4,020.50")],
           ("BALANCE DUE", "$4,980.50"))
    p.gap(24)
    p.text(90, "This is a statement of account. Please do not pay from this document.",
           BODY(19))
    return p.save("standard-textile-statement.png", 17)


def smudged():
    """Heavily degraded scan — the case where a single digit is at risk."""
    p = Page()
    letterhead(p, "ECOLAB INC.", ["1 Ecolab Place", "St. Paul, MN 55102"])
    meta(p, 150, [
        ("Invoice Number", "6610294883"),
        ("Invoice Date", "07/19/2026"),
        ("Customer", "1180-4471"),
    ])
    bill_to(p, ["Riverside Inn", "1234 Harbor Blvd", "Portland, OR 97201"])
    table(p, [
        ("Warewash detergent, 5 gal", "4", "188.00", "752.00"),
        ("Sanitizer concentrate, case", "6", "94.00", "564.00"),
    ])
    totals(p, [("Subtotal", "1,316.00"), ("Tax", "96.09")], ("AMOUNT DUE", "$1,412.09"))
    return p.save("ecolab-6610294883.png", 23, quality=28, blur=1.5)


def main() -> None:
    print("Writing sample scans:")
    sysco("sysco-4471-9928.png", "4471-9928", 3)
    grainger()
    city_water()
    unknown_vendor()
    statement()
    smudged()
    # The same Sysco invoice, scanned a second time in a later batch.
    sysco("sysco-4471-9928-rescan.png", "4471-9928", 31, quality=45)
    print("\nDone. Try:  invoice-extract samples/scans/ -g config/gl_accounts.example.yaml")


if __name__ == "__main__":
    main()
