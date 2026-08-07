from __future__ import annotations

import datetime as dt
from decimal import Decimal

from conftest import make_invoice, money, text

from invoice_extract.config import Config
from invoice_extract.validate import build

CONFIG = Config()


def codes(result) -> set[str]:
    return {f.code for f in result.findings}


def blockers(result) -> set[str]:
    return {f.code for f in result.findings if f.severity == "blocker"}


def test_clean_invoice_passes(invoice):
    result = build("scan.pdf", invoice, CONFIG)
    assert result.findings == []
    assert result.status == "auto"
    assert result.vendor_name == "Sysco Corporation"
    assert result.invoice_number == "INV-00123"
    assert result.invoice_date == "2026-07-15"
    assert result.total_amount == Decimal("1100.00")


def test_missing_fields_are_blockers():
    result = build(
        "scan.pdf",
        make_invoice(invoice_number=text(None), total_amount=money(None)),
        CONFIG,
    )
    assert "missing-field" in blockers(result)
    assert result.status == "review"


def test_low_confidence_holds_the_invoice():
    result = build(
        "scan.pdf",
        make_invoice(total_amount=money("1100.00", confidence="low")),
        CONFIG,
    )
    assert "low-confidence" in blockers(result)


def test_arithmetic_mismatch_is_caught():
    # Components sum to 1100 but the stated total reads 1010 — a transposition.
    result = build("scan.pdf", make_invoice(total_amount=money("1010.00")), CONFIG)
    assert "arithmetic" in blockers(result)


def test_arithmetic_tolerates_vendor_rounding():
    result = build("scan.pdf", make_invoice(total_amount=money("1100.01")), CONFIG)
    assert "arithmetic" not in codes(result)


def test_discount_is_subtracted_regardless_of_sign():
    for printed in ("50.00", "-50.00"):
        result = build(
            "scan.pdf",
            make_invoice(discount=money(printed), total_amount=money("1050.00")),
            CONFIG,
        )
        assert "arithmetic" not in codes(result), printed


def test_amount_must_match_the_text_it_came_from():
    # Normalized value disagrees with the characters quoted from the page.
    result = build(
        "scan.pdf",
        make_invoice(total_amount=money("1100.00", quote="$1,700.00")),
        CONFIG,
    )
    assert "amount-not-grounded" in blockers(result)


def test_invoice_number_grounding_is_a_warning_only():
    result = build(
        "scan.pdf",
        make_invoice(invoice_number=text("INV-00123", quote="INV-00987")),
        CONFIG,
    )
    assert "invoice-number-not-grounded" in codes(result)
    assert "invoice-number-not-grounded" not in blockers(result)


def test_negative_total_without_credit_memo_flag():
    result = build(
        "scan.pdf",
        make_invoice(
            subtotal=money("-1000.00"),
            tax=money("-80.00"),
            freight=money("-20.00"),
            total_amount=money("-1100.00"),
        ),
        CONFIG,
    )
    assert "negative-amount" in blockers(result)


def test_credit_memo_with_negative_total_is_accepted():
    result = build(
        "scan.pdf",
        make_invoice(
            is_credit_memo=True,
            subtotal=money("-1000.00"),
            tax=money("-80.00"),
            freight=money("-20.00"),
            total_amount=money("-1100.00"),
            line_items=[],
        ),
        CONFIG,
    )
    assert blockers(result) == set()


def test_zero_total_is_held():
    result = build(
        "scan.pdf",
        make_invoice(
            subtotal=money("0.00"),
            tax=money(None),
            freight=money(None),
            total_amount=money("0.00"),
            line_items=[],
        ),
        CONFIG,
    )
    assert "zero-amount" in blockers(result)


def test_future_date_is_held():
    future = (dt.date.today() + dt.timedelta(days=30)).isoformat()
    result = build("scan.pdf", make_invoice(invoice_date=text(future)), CONFIG)
    assert "future-date" in blockers(result)


def test_stale_date_is_held():
    old = (dt.date.today() - dt.timedelta(days=1000)).isoformat()
    result = build("scan.pdf", make_invoice(invoice_date=text(old)), CONFIG)
    assert "stale-date" in blockers(result)


def test_unparseable_date_is_reported_separately_from_missing():
    result = build(
        "scan.pdf", make_invoice(invoice_date=text("sometime in July")), CONFIG
    )
    assert {"missing-field", "unparseable-date"} <= blockers(result)


def test_statement_is_not_booked_as_an_invoice():
    result = build(
        "scan.pdf", make_invoice(document_type_note="monthly statement"), CONFIG
    )
    assert "not-an-invoice" in blockers(result)


def test_line_item_mismatch_is_a_warning():
    invoice = make_invoice()
    invoice.line_items[0].amount = "500.00"  # now sums to 900, not 1000
    result = build("scan.pdf", invoice, CONFIG)
    assert "line-items" in codes(result)
    assert result.status == "auto"


def test_legibility_note_is_a_warning():
    result = build(
        "scan.pdf", make_invoice(legibility_note="bottom edge cut off"), CONFIG
    )
    assert "legibility" in codes(result)
    assert result.status == "auto"
