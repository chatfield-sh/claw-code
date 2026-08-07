"""Excel export.

Three sheets:

* **Invoices**   — the upload sheet, in the exact column order the config
                   declares. By default only invoices that passed every check
                   land here, so nothing unverified reaches the accounting
                   system.
* **Exceptions** — everything held back, with the reason and the scan it came
                   from, so a person can settle it and re-run.
* **Audit**      — every field with the text it was read from and the model's
                   confidence, for spot-checking a sample of the batch.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from .config import Config
from .models import InvoiceResult
from .normalize import parse_money

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(color="FFFFFF", bold=True)
MONEY_FORMAT = "#,##0.00"

MONEY_FIELDS = {
    "subtotal",
    "tax",
    "freight",
    "other_charges",
    "discount",
    "total_amount",
}


def field_value(result: InvoiceResult, name: str) -> Any:
    """Resolve one export column for one invoice."""
    extracted = result.extracted
    if name == "vendor_name":
        return result.vendor_name
    if name == "invoice_number":
        return result.invoice_number
    if name == "invoice_date":
        return result.invoice_date
    if name == "total_amount":
        return result.total_amount
    if name == "gl_account":
        return result.gl_account
    if name == "gl_rule":
        return result.gl_rule
    if name == "property_code":
        return result.property_code
    if name == "source_file":
        return result.source_file
    if name == "status":
        return result.status
    if name == "review_reasons":
        return result.review_reasons or None
    if name == "confidence":
        return _overall_confidence(result)
    if name == "vendor_remit_to":
        return extracted.vendor_remit_to.value
    if name == "due_date":
        return extracted.due_date.value
    if name == "purchase_order":
        return extracted.purchase_order.value
    if name == "account_number":
        return extracted.account_number.value
    if name == "currency":
        return extracted.currency.value
    if name in MONEY_FIELDS:
        return parse_money(getattr(extracted, name).value)
    raise KeyError(f"no export mapping for column field {name!r}")


def _overall_confidence(result: InvoiceResult) -> str:
    """The weakest confidence across the fields that get keyed in."""
    order = {"high": 0, "medium": 1, "low": 2}
    extracted = result.extracted
    levels = [
        extracted.vendor_name.confidence,
        extracted.invoice_number.confidence,
        extracted.invoice_date.confidence,
        extracted.total_amount.confidence,
    ]
    return max(levels, key=lambda level: order[level])


def write(
    path: Path,
    results: list[InvoiceResult],
    config: Config,
    include_review_in_main: bool = False,
) -> None:
    """Write the workbook. Overwrites `path`."""
    workbook = Workbook()
    main = workbook.active
    main.title = "Invoices"

    exported = results if include_review_in_main else [
        r for r in results if r.status == "auto"
    ]
    held = [r for r in results if r.status == "review"]

    _write_main(main, exported, config)
    _write_exceptions(workbook.create_sheet("Exceptions"), held)
    _write_audit(workbook.create_sheet("Audit"), results)

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def _write_main(sheet: Worksheet, results: list[InvoiceResult], config: Config) -> None:
    fields = list(config.columns)
    _header(sheet, [config.columns[f] for f in fields])
    for row, result in enumerate(results, start=2):
        for col, name in enumerate(fields, start=1):
            cell = sheet.cell(row=row, column=col, value=field_value(result, name))
            if name in MONEY_FIELDS:
                cell.number_format = MONEY_FORMAT
    _finish(sheet, len(fields))


EXCEPTION_HEADERS = [
    "Scan File",
    "Vendor",
    "Invoice Number",
    "Invoice Date",
    "Amount",
    "GL Account",
    "Property",
    "Why It Was Held",
]


def _write_exceptions(sheet: Worksheet, results: list[InvoiceResult]) -> None:
    _header(sheet, EXCEPTION_HEADERS)
    for row, result in enumerate(results, start=2):
        values: list[Any] = [
            result.source_file,
            result.vendor_name,
            result.invoice_number,
            result.invoice_date,
            result.total_amount,
            result.gl_account,
            result.property_code,
            result.review_reasons,
        ]
        for col, value in enumerate(values, start=1):
            cell = sheet.cell(row=row, column=col, value=value)
            if isinstance(value, Decimal):
                cell.number_format = MONEY_FORMAT
        sheet.cell(row=row, column=len(values)).alignment = Alignment(wrap_text=True)
    _finish(sheet, len(EXCEPTION_HEADERS), wide_last=True)


AUDIT_HEADERS = [
    "Scan File",
    "Status",
    "Field",
    "Value Used",
    "Text On Invoice",
    "Confidence",
    "Second Read",
]

_AUDIT_FIELDS = ("vendor_name", "invoice_number", "invoice_date", "total_amount")


def _write_audit(sheet: Worksheet, results: list[InvoiceResult]) -> None:
    _header(sheet, AUDIT_HEADERS)
    row = 2
    for result in results:
        for name in _AUDIT_FIELDS:
            field = getattr(result.extracted, name)
            second = (
                getattr(result.verification, name, None)
                if result.verification is not None
                else None
            )
            values = [
                result.source_file,
                result.status,
                name.replace("_", " "),
                field.value,
                field.source_quote,
                field.confidence,
                second if second is not None else "—",
            ]
            for col, value in enumerate(values, start=1):
                sheet.cell(row=row, column=col, value=value)
            row += 1
    _finish(sheet, len(AUDIT_HEADERS))


def _header(sheet: Worksheet, headers: list[str]) -> None:
    for col, text in enumerate(headers, start=1):
        cell = sheet.cell(row=1, column=col, value=text)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    sheet.freeze_panes = "A2"


def _finish(sheet: Worksheet, columns: int, wide_last: bool = False) -> None:
    """Size columns to their contents, within reason."""
    for col in range(1, columns + 1):
        letter = get_column_letter(col)
        longest = max(
            (len(str(cell.value)) for cell in sheet[letter] if cell.value is not None),
            default=0,
        )
        width = min(max(longest + 2, 12), 60)
        if wide_last and col == columns:
            width = 60
        sheet.column_dimensions[letter].width = width
