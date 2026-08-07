#!/usr/bin/env python3
"""Run the pipeline over the sample scans without calling the API.

The model responses here are CANNED — hand-written to match what the sample
scans say, including one deliberate misread on the degraded Ecolab scan. This
is not an accuracy test and proves nothing about how well the model reads; it
exercises everything around the model (consensus, validation, GL coding,
duplicate detection, export, exit codes) and shows what the output looks like
before you spend anything on an API key.

    python samples/make_samples.py     # once, to create the scans
    python samples/demo_run.py

For a real run, set ANTHROPIC_API_KEY and use the CLI:

    invoice-extract samples/scans/ -g config/gl_accounts.example.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from invoice_extract import cli  # noqa: E402
from invoice_extract.extract import Usage  # noqa: E402
from invoice_extract.models import (  # noqa: E402
    ExtractedDocument,
    ExtractedInvoice,
    ExtractedLineItem,
    MoneyField,
    TextField,
    VerificationDocument,
    VerificationInvoice,
)

SCANS = ROOT / "samples" / "scans"
OUT = ROOT / "samples" / "out"


def t(value, quote=None, confidence="high"):
    return TextField(value=value, source_quote=quote or value, confidence=confidence)


def m(value, quote=None, confidence="high"):
    return MoneyField(value=value, source_quote=quote or value, confidence=confidence)


def inv(**kw) -> ExtractedInvoice:
    base = dict(
        vendor_remit_to=t(None), due_date=t(None), purchase_order=t(None),
        account_number=t(None), currency=t("USD"), other_charges=m(None),
        discount=m(None), freight=m(None), tax=m(None), subtotal=m(None),
        line_items=[], is_credit_memo=False, document_type_note=None,
        legibility_note=None, page_range="1",
    )
    base.update(kw)
    return ExtractedInvoice(**base)


def line(desc, qty, unit, amount):
    return ExtractedLineItem(description=desc, quantity=qty, unit_price=unit, amount=amount)


def v(vendor, number, date, total) -> VerificationInvoice:
    return VerificationInvoice(
        vendor_name=vendor, invoice_number=number, invoice_date=date, total_amount=total
    )


# What the model would return for each scan, pass 1 and pass 2.
READS: dict[str, ExtractedInvoice] = {
    "sysco-4471-9928.png": inv(
        vendor_name=t("Sysco Corporation", "SYSCO CORPORATION"),
        invoice_number=t("4471-9928"), invoice_date=t("2026-07-15", "07/15/2026"),
        purchase_order=t("PO-55831"), account_number=t("884120"),
        property_hint=t("Riverside Inn, 1234 Harbor Blvd, Portland, OR 97201"),
        subtotal=m("1000.00", "1,000.00"), tax=m("80.00"), freight=m("20.00"),
        total_amount=m("1100.00", "$1,100.00"),
        line_items=[line("Produce - mixed case", "10", "60.00", "600.00"),
                    line("Dry goods - assorted", "8", "50.00", "400.00")],
    ),
    "grainger-9481773265.png": inv(
        vendor_name=t("Grainger", "GRAINGER"),
        invoice_number=t("9481773265"), invoice_date=t("2026-07-22", "07/22/2026"),
        account_number=t("8829104"),
        property_hint=t("Downtown Suites, 88 Fifth Street, Portland, OR 97204"),
        subtotal=m("495.00"), tax=m("39.60"), total_amount=m("534.60", "$534.60"),
        line_items=[line("HVAC blower motor, 1/3 HP", "2", "184.50", "369.00"),
                    line("Pleated air filter 20x25x1, case", "3", "42.00", "126.00")],
    ),
    "citywater-88-201466.png": inv(
        vendor_name=t("City Water & Power", "CITY WATER & POWER"),
        invoice_number=t("88-201466"), invoice_date=t("2026-07-28", "07/28/2026"),
        account_number=t("4471-000-99"),
        property_hint=t("Riverside Inn, 1234 Harbor Blvd, Portland, OR 97201"),
        subtotal=m("2094.60", "2,094.60"), tax=m("109.56"),
        total_amount=m("2204.16", "$2,204.16"),
        line_items=[line("Electric usage - 18,420 kWh", "1", "1884.60", "1884.60"),
                    line("Demand charge", "1", "210.00", "210.00")],
    ),
    "cascade-CCS-2026-0788.png": inv(
        vendor_name=t("Cascade Commercial Services LLC", "CASCADE COMMERCIAL SERVICES LLC"),
        invoice_number=t("CCS-2026-0788"), invoice_date=t("2026-08-01", "08/01/2026"),
        property_hint=t("Downtown Suites, 88 Fifth Street, Portland, OR 97204"),
        subtotal=m("1725.00", "1,725.00"), tax=m("0.00"),
        total_amount=m("1725.00", "$1,725.00"),
        line_items=[line("Quarterly window washing - exterior", "1", "1450.00", "1450.00"),
                    line("Awning cleaning", "1", "275.00", "275.00")],
    ),
    "standard-textile-statement.png": inv(
        vendor_name=t("Standard Textile Co., Inc.", "STANDARD TEXTILE CO., INC."),
        invoice_number=t(None), invoice_date=t("2026-07-31", "07/31/2026"),
        account_number=t("HT-88412"),
        property_hint=t("Riverside Inn, 1234 Harbor Blvd, Portland, OR 97201"),
        total_amount=m("4980.50", "$4,980.50"),
        document_type_note="monthly statement listing three invoices, marked "
                           "'do not pay from this document'",
    ),
    # The degraded scan: pass 1 reads the cents as .09, pass 2 as .99.
    "ecolab-6610294883.png": inv(
        vendor_name=t("Ecolab Inc.", "ECOLAB INC."),
        invoice_number=t("6610294883"), invoice_date=t("2026-07-19", "07/19/2026"),
        account_number=t("1180-4471"),
        property_hint=t("Riverside Inn, 1234 Harbor Blvd, Portland, OR 97201"),
        subtotal=m("1316.00", "1,316.00"), tax=m("96.09", "96.09", "medium"),
        total_amount=m("1412.09", "$1,412.09", "medium"),
        line_items=[line("Warewash detergent, 5 gal", "4", "188.00", "752.00"),
                    line("Sanitizer concentrate, case", "6", "94.00", "564.00")],
        legibility_note="heavy speckle across the totals block; the cents on the "
                        "amount due are not crisp",
    ),
}
READS["sysco-4471-9928-rescan.png"] = READS["sysco-4471-9928.png"]

CHECKS: dict[str, VerificationInvoice] = {
    "sysco-4471-9928.png": v("Sysco Corporation", "4471-9928", "2026-07-15", "1100.00"),
    "grainger-9481773265.png": v("Grainger", "9481773265", "2026-07-22", "534.60"),
    "citywater-88-201466.png": v("City Water and Power", "88-201466", "2026-07-28", "2204.16"),
    "cascade-CCS-2026-0788.png": v(
        "Cascade Commercial Services LLC", "CCS-2026-0788", "2026-08-01", "1725.00"),
    "standard-textile-statement.png": v(
        "Standard Textile Co., Inc.", None, "2026-07-31", "4980.50"),
    "ecolab-6610294883.png": v("Ecolab Inc.", "6610294883", "2026-07-19", "1412.99"),
}
CHECKS["sysco-4471-9928-rescan.png"] = CHECKS["sysco-4471-9928.png"]


class CannedExtractor:
    def __init__(self, **_kwargs):
        self.usage = Usage()

    def read(self, path):
        return ExtractedDocument(invoices=[READS[path.name]])

    def verify(self, path):
        return VerificationDocument(invoices=[CHECKS[path.name]])


def banner(text: str) -> None:
    print(f"\n\033[1m{'=' * 72}\n{text}\n{'=' * 72}\033[0m", flush=True)


def main() -> int:
    if not SCANS.exists():
        print("Run `python samples/make_samples.py` first.", file=sys.stderr)
        return 2

    cli.Extractor = CannedExtractor  # type: ignore[assignment]
    OUT.mkdir(parents=True, exist_ok=True)
    ledger = OUT / "submitted.sqlite"
    ledger.unlink(missing_ok=True)

    gl = str(ROOT / "config" / "gl_accounts.example.yaml")
    config = str(ROOT / "config" / "config.example.yaml")
    originals = sorted(p for p in SCANS.glob("*.png") if "rescan" not in p.name)

    banner("RUN 1 — this month's batch of six scans")
    first = cli.main([*map(str, originals), "-c", config, "-g", gl,
                      "-o", str(OUT / "august.xlsx"), "--ledger", str(ledger)])
    print(f"\nexit code: {first}")

    banner("RUN 2 — someone re-scans the Sysco invoice into next month's batch")
    second = cli.main([str(SCANS / "sysco-4471-9928-rescan.png"), "-c", config, "-g", gl,
                       "-o", str(OUT / "september.xlsx"), "--ledger", str(ledger)])
    print(f"\nexit code: {second}")

    print(f"\nWorkbooks written to {OUT.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
