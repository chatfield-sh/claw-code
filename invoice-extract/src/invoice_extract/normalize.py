"""Normalization helpers.

Everything that turns model output into canonical values lives here, so the
comparison logic in `consensus.py`, the arithmetic in `validate.py` and the
lookups in `gl.py` and `ledger.py` all agree on what "the same" means.
"""

from __future__ import annotations

import datetime as _dt
import re
import unicodedata
from decimal import Decimal, InvalidOperation

__all__ = [
    "parse_money",
    "money_str",
    "vendor_key",
    "invoice_number_key",
    "parse_date",
    "collapse_whitespace",
]

# Characters OCR commonly substitutes inside otherwise-numeric strings.
_OCR_DIGIT_FIXES = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1"})

_CURRENCY_CHARS = "$€£¥₹"
_TRAILING_NOISE = re.compile(r"\b(usd|cad|eur|gbp|each|ea|per|only)\b\.?$", re.I)
_PAREN_NEGATIVE = re.compile(r"^\((.*)\)$")

# Suffixes that differ between how a vendor prints its name on two invoices but
# never distinguish two real vendors from each other.
_VENDOR_SUFFIXES = {
    "inc", "incorporated", "llc", "l l c", "llp", "ltd", "limited", "co",
    "company", "corp", "corporation", "plc", "pllc", "lp", "pa", "pc", "sa",
    "gmbh", "the", "and", "of",
}


def collapse_whitespace(text: str | None) -> str | None:
    """Trim and collapse internal runs of whitespace."""
    if text is None:
        return None
    cleaned = " ".join(text.split())
    return cleaned or None


def parse_money(raw: str | None) -> Decimal | None:
    """Parse a monetary string into a Decimal, or return None.

    Handles currency symbols, thousands separators, parenthesized negatives,
    trailing currency codes, and the digit-shaped letters OCR tends to emit.
    Returns None rather than raising, so a malformed amount becomes a
    validation finding instead of a crash.
    """
    if raw is None:
        return None
    text = collapse_whitespace(str(raw))
    if not text:
        return None

    text = unicodedata.normalize("NFKC", text)
    text = _TRAILING_NOISE.sub("", text).strip()

    negative = False
    paren = _PAREN_NEGATIVE.match(text)
    if paren:
        negative = True
        text = paren.group(1).strip()

    for symbol in _CURRENCY_CHARS:
        text = text.replace(symbol, "")
    text = text.replace(",", "").replace(" ", "").replace(" ", "")
    text = text.translate(_OCR_DIGIT_FIXES)

    if text.startswith("-"):
        negative = not negative
        text = text[1:]
    elif text.endswith("-"):  # trailing-minus convention on some ledgers
        negative = not negative
        text = text[:-1]

    if not text or not re.fullmatch(r"\d*\.?\d*", text) or text in {".", ""}:
        return None

    try:
        value = Decimal(text)
    except InvalidOperation:
        return None

    return -value if negative else value


def money_str(value: Decimal | None) -> str | None:
    """Render a Decimal as a fixed two-place string for export."""
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01')):f}"


def vendor_key(name: str | None) -> str | None:
    """Reduce a vendor name to a comparison key.

    Case, punctuation and corporate suffixes are dropped so that
    "ACME Supply Co., Inc." and "Acme Supply Company" collapse together, while
    genuinely different vendors stay distinct.
    """
    cleaned = collapse_whitespace(name)
    if not cleaned:
        return None
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = "".join(c for c in cleaned if not unicodedata.combining(c))
    cleaned = re.sub(r"[^\w\s]", " ", cleaned.lower())
    tokens = [t for t in cleaned.split() if t and t not in _VENDOR_SUFFIXES]
    return " ".join(tokens) or None


def invoice_number_key(number: str | None) -> str | None:
    """Reduce an invoice number to a comparison key.

    Separators and case vary between how a vendor prints a number and how it
    is keyed, but the alphanumeric run does not. Leading zeros are preserved:
    'INV-0042' and '42' are different invoices.
    """
    cleaned = collapse_whitespace(number)
    if not cleaned:
        return None
    key = re.sub(r"[^A-Za-z0-9]", "", cleaned).upper()
    return key or None


_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%d/%m/%Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d %b %Y",
    "%d %B %Y",
    "%Y/%m/%d",
    "%m-%d-%Y",
)


def parse_date(raw: str | None) -> _dt.date | None:
    """Parse a date string into a date, or return None.

    The extraction prompt asks for YYYY-MM-DD; the other formats are a safety
    net for when the model echoes the printed form instead. Ambiguous
    day/month orderings are resolved US-first, matching the invoices this tool
    is built for — `validate.py` flags dates that land in the future or far
    past, which is where a misread ordering shows up.
    """
    text = collapse_whitespace(raw)
    if not text:
        return None
    text = text.replace(".", "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return _dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
