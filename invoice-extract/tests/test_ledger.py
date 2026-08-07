from __future__ import annotations

from conftest import make_invoice, money, text

from invoice_extract.config import Config
from invoice_extract.ledger import Ledger
from invoice_extract.validate import build

CONFIG = Config()


def result_for(source="scan.pdf", **overrides):
    return build(source, make_invoice(**overrides), CONFIG)


def codes(result) -> set[str]:
    return {f.code for f in result.findings}


def test_first_submission_is_clean(tmp_path):
    with Ledger(tmp_path / "l.sqlite") as ledger:
        result = result_for()
        ledger.check(result)
        assert result.findings == []
        assert ledger.record([result]) == 1


def test_resubmitting_the_same_invoice_is_caught(tmp_path):
    path = tmp_path / "l.sqlite"
    with Ledger(path) as ledger:
        first = result_for("january-batch.pdf")
        ledger.check(first)
        ledger.record([first])

    with Ledger(path) as ledger:
        again = result_for("february-batch.pdf")
        ledger.check(again)
        assert "duplicate" in codes(again)
        assert again.status == "review"
        assert "january-batch.pdf" in again.review_reasons


def test_duplicate_is_caught_within_a_single_batch(tmp_path):
    with Ledger(tmp_path / "l.sqlite") as ledger:
        first = result_for("a.pdf")
        second = result_for("b.pdf")
        ledger.check(first)
        ledger.check(second)
        assert first.findings == []
        assert "duplicate-in-batch" in codes(second)


def test_reformatted_invoice_number_still_matches(tmp_path):
    path = tmp_path / "l.sqlite"
    with Ledger(path) as ledger:
        ledger.record([result_for()])
    with Ledger(path) as ledger:
        again = result_for(invoice_number=text("inv 00123"))
        ledger.check(again)
        assert "duplicate" in codes(again)


def test_different_invoice_from_same_vendor_is_fine(tmp_path):
    path = tmp_path / "l.sqlite"
    with Ledger(path) as ledger:
        ledger.record([result_for()])
    with Ledger(path) as ledger:
        other = result_for(
            invoice_number=text("INV-00124"),
            subtotal=money("500.00"),
            tax=money("40.00"),
            freight=money("10.00"),
            total_amount=money("550.00"),
            line_items=[],
        )
        ledger.check(other)
        assert other.findings == []


def test_same_vendor_amount_and_date_is_a_warning(tmp_path):
    path = tmp_path / "l.sqlite"
    with Ledger(path) as ledger:
        ledger.record([result_for()])
    with Ledger(path) as ledger:
        reissued = result_for(invoice_number=text("INV-00999"))
        ledger.check(reissued)
        assert "possible-duplicate" in codes(reissued)
        assert reissued.status == "auto"  # warning only — a person decides


def test_disabled_ledger_still_catches_within_batch():
    with Ledger(None) as ledger:
        assert not ledger.enabled
        first, second = result_for("a.pdf"), result_for("b.pdf")
        ledger.check(first)
        ledger.check(second)
        assert "duplicate-in-batch" in codes(second)
        assert ledger.record([first, second]) == 0
