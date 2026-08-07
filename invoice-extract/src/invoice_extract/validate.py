"""Turn a raw extraction into a checked result.

The checks here are the ones a page can answer about itself: is the required
data present, does the model say it could read it, do the numbers on the
invoice add up to the invoice's own total, is the date plausible, and does each
normalized value still match the characters it was copied from.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal

from .config import Config
from .models import ExtractedInvoice, InvoiceResult
from .normalize import (
    collapse_whitespace,
    invoice_number_key,
    parse_date,
    parse_money,
    vendor_key,
)

# Fields whose value is keyed into the accounting system.
CRITICAL_FIELDS = ("vendor_name", "invoice_number", "invoice_date", "total_amount")


def build(
    source_file: str, extracted: ExtractedInvoice, config: Config
) -> InvoiceResult:
    """Build a result from one extracted invoice and run every page-local check."""
    result = InvoiceResult(source_file=source_file, extracted=extracted)

    result.vendor_name = collapse_whitespace(extracted.vendor_name.value)
    result.vendor_key = vendor_key(result.vendor_name)
    result.invoice_number = collapse_whitespace(extracted.invoice_number.value)
    result.total_amount = parse_money(extracted.total_amount.value)

    parsed_date = parse_date(extracted.invoice_date.value)
    result.invoice_date = parsed_date.isoformat() if parsed_date else None

    _check_document_type(result, extracted)
    _check_required(result, extracted)
    _check_confidence(result, extracted)
    _check_grounding(result, extracted)
    _check_sign(result, extracted)
    _check_arithmetic(result, extracted, config)
    _check_line_items(result, extracted, config)
    _check_date(result, parsed_date, config)
    _check_legibility(result, extracted)

    return result


def _check_document_type(result: InvoiceResult, extracted: ExtractedInvoice) -> None:
    note = collapse_whitespace(extracted.document_type_note)
    if note:
        result.add(
            "not-an-invoice",
            f"the document does not look like a standard invoice ({note})",
        )


def _check_required(result: InvoiceResult, extracted: ExtractedInvoice) -> None:
    missing = []
    if not result.vendor_name:
        missing.append("vendor")
    if not result.invoice_number:
        missing.append("invoice number")
    if not result.invoice_date:
        missing.append("invoice date")
    if result.total_amount is None:
        missing.append("amount")
    if missing:
        result.add("missing-field", f"could not read: {', '.join(missing)}")

    # A date that was read but not parsed is a different problem from one that
    # was never found, and needs a different fix.
    if extracted.invoice_date.value and result.invoice_date is None:
        result.add(
            "unparseable-date",
            f"invoice date {extracted.invoice_date.value!r} is not a date this "
            "tool recognizes",
        )
    if extracted.total_amount.value and result.total_amount is None:
        result.add(
            "unparseable-amount",
            f"amount {extracted.total_amount.value!r} is not a number this tool "
            "recognizes",
        )


def _check_confidence(result: InvoiceResult, extracted: ExtractedInvoice) -> None:
    for name in CRITICAL_FIELDS:
        field = getattr(extracted, name)
        if field.confidence == "low":
            result.add(
                "low-confidence",
                f"{name.replace('_', ' ')} was read with low confidence "
                f"(source shows {field.source_quote!r})",
            )


def _check_grounding(result: InvoiceResult, extracted: ExtractedInvoice) -> None:
    """The normalized value must still match the characters it came from.

    This catches the failure that confidence scores miss: a value that was read
    correctly off the page and then altered on the way into the structured
    field.
    """
    quoted_total = parse_money(extracted.total_amount.source_quote)
    if quoted_total is not None and result.total_amount is not None:
        if quoted_total.quantize(Decimal("0.01")) != result.total_amount.quantize(
            Decimal("0.01")
        ):
            result.add(
                "amount-not-grounded",
                f"the reported amount {result.total_amount:,.2f} does not match "
                f"the text it was read from ({extracted.total_amount.source_quote!r})",
            )

    quote = extracted.invoice_number.source_quote
    if quote and result.invoice_number:
        if invoice_number_key(quote) != invoice_number_key(result.invoice_number):
            result.add(
                "invoice-number-not-grounded",
                f"the reported invoice number {result.invoice_number!r} does not "
                f"match the text it was read from ({quote!r})",
                severity="warning",
            )


def _check_sign(result: InvoiceResult, extracted: ExtractedInvoice) -> None:
    total = result.total_amount
    if total is None:
        return
    if total == 0:
        result.add("zero-amount", "the invoice total is zero")
        return
    if total < 0 and not extracted.is_credit_memo:
        result.add(
            "negative-amount",
            f"the amount is negative ({total:,.2f}) but the document was not "
            "identified as a credit memo",
        )
    if total > 0 and extracted.is_credit_memo:
        result.add(
            "credit-memo-sign",
            f"the document was identified as a credit memo but the amount is "
            f"positive ({total:,.2f})",
        )


def _check_arithmetic(
    result: InvoiceResult, extracted: ExtractedInvoice, config: Config
) -> None:
    """Do the invoice's own components sum to its own total?

    Only runs when a subtotal and total are both present. A vendor that prints
    only a total has nothing to check against, which is a coverage gap, not a
    failure — the verification pass is the guard there.
    """
    subtotal = parse_money(extracted.subtotal.value)
    total = result.total_amount
    if subtotal is None or total is None:
        return

    tax = parse_money(extracted.tax.value) or Decimal(0)
    freight = parse_money(extracted.freight.value) or Decimal(0)
    other = parse_money(extracted.other_charges.value) or Decimal(0)
    discount = parse_money(extracted.discount.value) or Decimal(0)

    computed = subtotal + tax + freight + other - abs(discount)
    difference = (computed - total).copy_abs()
    if difference > config.arithmetic_tolerance:
        result.add(
            "arithmetic",
            f"components do not sum to the total: subtotal {subtotal:,.2f} "
            f"+ tax {tax:,.2f} + freight {freight:,.2f} + other {other:,.2f} "
            f"- discount {abs(discount):,.2f} = {computed:,.2f}, "
            f"but the invoice total reads {total:,.2f} "
            f"(off by {difference:,.2f})",
        )


def _check_line_items(
    result: InvoiceResult, extracted: ExtractedInvoice, config: Config
) -> None:
    """Do the line items sum to the subtotal?

    A warning rather than a blocker: partial line-item capture on a dense or
    multi-page invoice is common and does not by itself mean the total is
    wrong.
    """
    if not extracted.line_items:
        return
    amounts = [parse_money(item.amount) for item in extracted.line_items]
    if any(amount is None for amount in amounts):
        return
    subtotal = parse_money(extracted.subtotal.value)
    if subtotal is None:
        return
    line_sum = sum(amounts, Decimal(0))  # type: ignore[arg-type]
    difference = (line_sum - subtotal).copy_abs()
    if difference > config.arithmetic_tolerance:
        result.add(
            "line-items",
            f"line items total {line_sum:,.2f} but the subtotal reads "
            f"{subtotal:,.2f} (off by {difference:,.2f})",
            severity="warning",
        )


def _check_date(
    result: InvoiceResult, parsed: _dt.date | None, config: Config
) -> None:
    if parsed is None:
        return
    today = _dt.date.today()
    if parsed > today + _dt.timedelta(days=config.max_future_days):
        result.add(
            "future-date",
            f"the invoice date {parsed.isoformat()} is in the future, which "
            "usually means a misread year or a transposed day and month",
        )
    elif parsed < today - _dt.timedelta(days=config.max_age_days):
        result.add(
            "stale-date",
            f"the invoice date {parsed.isoformat()} is more than "
            f"{config.max_age_days} days old",
        )


def _check_legibility(result: InvoiceResult, extracted: ExtractedInvoice) -> None:
    note = collapse_whitespace(extracted.legibility_note)
    if note:
        result.add("legibility", f"scan quality note: {note}", severity="warning")
