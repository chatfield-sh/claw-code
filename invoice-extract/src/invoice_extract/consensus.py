"""Reconcile the extraction pass against the independent verification pass.

Two independent reads of the same page agreeing on vendor, invoice number,
date and amount is the strongest signal available that a value was read
correctly. Any disagreement on those four sends the invoice to review — the
tool never picks a winner, because whichever it picked would be right only
half the time on exactly the invoices that matter.
"""

from __future__ import annotations

from decimal import Decimal

from .models import InvoiceResult, VerificationDocument, VerificationInvoice
from .normalize import (
    collapse_whitespace,
    invoice_number_key,
    parse_date,
    parse_money,
    vendor_key,
)


def attach(results: list[InvoiceResult], verification: VerificationDocument) -> None:
    """Pair each result with its verification read and record disagreements."""
    verified = verification.invoices
    if len(verified) != len(results):
        for result in results:
            result.add(
                "verify-count",
                f"the two reads disagree on how many invoices this file "
                f"contains ({len(results)} vs {len(verified)})",
            )
        return

    for result, check in zip(results, verified):
        result.verification = check
        _compare(result, check)


def _compare(result: InvoiceResult, check: VerificationInvoice) -> None:
    _compare_vendor(result, check.vendor_name)
    _compare_invoice_number(result, check.invoice_number)
    _compare_date(result, check.invoice_date)
    _compare_total(result, check.total_amount)


def _compare_vendor(result: InvoiceResult, other_raw: str | None) -> None:
    mine = vendor_key(result.vendor_name)
    theirs = vendor_key(other_raw)
    if mine is None and theirs is None:
        return
    if mine == theirs:
        return
    if mine and theirs and (mine in theirs or theirs in mine):
        # One read carried a division or a longer legal name. Same vendor,
        # different amount of it — worth a note, not a hold.
        result.add(
            "verify-vendor-partial",
            f"vendor name read two ways: {result.vendor_name!r} vs {other_raw!r}",
            severity="warning",
        )
        return
    result.add(
        "verify-vendor",
        f"the two reads disagree on the vendor: "
        f"{result.vendor_name!r} vs {other_raw!r}",
    )


def _compare_invoice_number(result: InvoiceResult, other_raw: str | None) -> None:
    mine = invoice_number_key(result.invoice_number)
    theirs = invoice_number_key(other_raw)
    if mine is None and theirs is None:
        return
    if mine == theirs:
        return
    result.add(
        "verify-invoice-number",
        f"the two reads disagree on the invoice number: "
        f"{result.invoice_number!r} vs {other_raw!r}",
    )


def _compare_date(result: InvoiceResult, other_raw: str | None) -> None:
    mine = parse_date(result.invoice_date)
    theirs = parse_date(collapse_whitespace(other_raw))
    if mine is None and theirs is None:
        return
    if mine == theirs:
        return
    result.add(
        "verify-invoice-date",
        f"the two reads disagree on the invoice date: "
        f"{result.invoice_date!r} vs {other_raw!r}",
    )


def _compare_total(result: InvoiceResult, other_raw: str | None) -> None:
    mine = result.total_amount
    theirs = parse_money(other_raw)
    if mine is None and theirs is None:
        return
    if mine is not None and theirs is not None:
        if mine.quantize(Decimal("0.01")) == theirs.quantize(Decimal("0.01")):
            return
    result.add(
        "verify-total",
        f"the two reads disagree on the amount: "
        f"{_show(mine)} vs {_show(theirs)}",
    )


def _show(value: Decimal | None) -> str:
    return "nothing" if value is None else f"{value:,.2f}"
