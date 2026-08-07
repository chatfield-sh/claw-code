from __future__ import annotations

from conftest import make_invoice

from invoice_extract.config import Config
from invoice_extract.consensus import attach
from invoice_extract.models import VerificationDocument, VerificationInvoice
from invoice_extract.validate import build

CONFIG = Config()


def agreeing() -> VerificationInvoice:
    return VerificationInvoice(
        vendor_name="Sysco Corporation",
        invoice_number="INV-00123",
        invoice_date="2026-07-15",
        total_amount="1100.00",
    )


def run(check: VerificationInvoice, **overrides):
    result = build("scan.pdf", make_invoice(**overrides), CONFIG)
    attach([result], VerificationDocument(invoices=[check]))
    return result


def codes(result) -> set[str]:
    return {f.code for f in result.findings}


def blockers(result) -> set[str]:
    return {f.code for f in result.findings if f.severity == "blocker"}


def test_agreement_adds_nothing():
    result = run(agreeing())
    assert result.findings == []
    assert result.status == "auto"


def test_formatting_differences_are_not_disagreements():
    check = agreeing()
    check.vendor_name = "SYSCO CORP."
    check.invoice_number = "inv 00123"
    check.invoice_date = "07/15/2026"
    check.total_amount = "$1,100.00"
    result = run(check)
    assert result.findings == []


def test_amount_disagreement_is_a_blocker():
    check = agreeing()
    check.total_amount = "1700.00"
    result = run(check)
    assert "verify-total" in blockers(result)


def test_invoice_number_disagreement_is_a_blocker():
    check = agreeing()
    check.invoice_number = "INV-00723"
    result = run(check)
    assert "verify-invoice-number" in blockers(result)


def test_date_disagreement_is_a_blocker():
    check = agreeing()
    check.invoice_date = "2026-01-15"
    result = run(check)
    assert "verify-invoice-date" in blockers(result)


def test_unrelated_vendor_is_a_blocker():
    check = agreeing()
    check.vendor_name = "US Foods"
    result = run(check)
    assert "verify-vendor" in blockers(result)


def test_partial_vendor_match_is_only_a_warning():
    check = agreeing()
    check.vendor_name = "Sysco Corporation Northeast Division"
    result = run(check)
    assert "verify-vendor-partial" in codes(result)
    assert result.status == "auto"


def test_one_read_finding_nothing_still_disagrees():
    check = agreeing()
    check.total_amount = None
    result = run(check)
    assert "verify-total" in blockers(result)


def test_disagreement_on_invoice_count_blocks_everything():
    results = [build("scan.pdf", make_invoice(), CONFIG) for _ in range(2)]
    attach(results, VerificationDocument(invoices=[agreeing()]))
    assert all("verify-count" in blockers(r) for r in results)
    assert all(r.verification is None for r in results)
