from __future__ import annotations

import pytest

from invoice_extract.models import (
    ExtractedInvoice,
    ExtractedLineItem,
    MoneyField,
    TextField,
)


def text(value: str | None, quote: str | None = None, confidence: str = "high"):
    return TextField(
        value=value,
        source_quote=quote if quote is not None else value,
        confidence=confidence,  # type: ignore[arg-type]
    )


def money(value: str | None, quote: str | None = None, confidence: str = "high"):
    return MoneyField(
        value=value,
        source_quote=quote if quote is not None else value,
        confidence=confidence,  # type: ignore[arg-type]
    )


def make_invoice(**overrides) -> ExtractedInvoice:
    """A clean, internally consistent invoice. Override fields per test."""
    fields = {
        "vendor_name": text("Sysco Corporation"),
        "vendor_remit_to": text(None),
        "invoice_number": text("INV-00123"),
        "invoice_date": text("2026-07-15"),
        "due_date": text("2026-08-14"),
        "purchase_order": text(None),
        "account_number": text(None),
        "property_hint": text("Riverside Inn, 1234 Harbor Blvd"),
        "currency": text("USD"),
        "subtotal": money("1000.00"),
        "tax": money("80.00"),
        "freight": money("20.00"),
        "other_charges": money(None),
        "discount": money(None),
        "total_amount": money("1100.00"),
        "line_items": [
            ExtractedLineItem(
                description="Produce - mixed case",
                quantity="10",
                unit_price="60.00",
                amount="600.00",
            ),
            ExtractedLineItem(
                description="Dry goods",
                quantity="8",
                unit_price="50.00",
                amount="400.00",
            ),
        ],
        "is_credit_memo": False,
        "document_type_note": None,
        "legibility_note": None,
        "page_range": "1",
    }
    fields.update(overrides)
    return ExtractedInvoice(**fields)  # type: ignore[arg-type]


@pytest.fixture
def invoice() -> ExtractedInvoice:
    return make_invoice()
