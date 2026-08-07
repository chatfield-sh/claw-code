"""Schemas for invoice extraction.

The `Extraction*` models are the structured-output contract sent to Claude.
The `Invoice*` models are the post-processing result carried through
validation, GL assignment and export.

Constraints: these classes are compiled to a JSON Schema for the API's
structured-output mode, which does not support numeric/length constraints,
recursion, or `additionalProperties` other than `false`. Keep the shapes flat
and use plain types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]


class MoneyField(BaseModel):
    """A monetary amount together with the evidence it was read from."""

    value: str | None = Field(
        description=(
            "The amount as it should be recorded, using a plain decimal string "
            "with no currency symbol, thousands separator or trailing text "
            "(e.g. '1234.56'). Negative amounts use a leading '-'. "
            "Null if the field is genuinely absent from the document."
        )
    )
    source_quote: str | None = Field(
        description=(
            "The exact characters as printed on the invoice, copied verbatim "
            "including any currency symbol or separators (e.g. '$1,234.56'). "
            "Null if the field is absent."
        )
    )
    confidence: Confidence = Field(
        description=(
            "high = printed clearly and unambiguously; "
            "medium = legible but degraded, or inferred from context; "
            "low = poorly legible, ambiguous, or a guess."
        )
    )


class TextField(BaseModel):
    """A text value together with the evidence it was read from."""

    value: str | None = Field(
        description="The normalized value, or null if genuinely absent."
    )
    source_quote: str | None = Field(
        description="The exact characters as printed on the invoice, verbatim."
    )
    confidence: Confidence = Field(
        description=(
            "high = printed clearly and unambiguously; "
            "medium = legible but degraded, or inferred from context; "
            "low = poorly legible, ambiguous, or a guess."
        )
    )


class ExtractedLineItem(BaseModel):
    description: str = Field(description="The line item description as printed.")
    quantity: str | None = Field(description="Quantity as a decimal string, or null.")
    unit_price: str | None = Field(
        description="Unit price as a plain decimal string, or null."
    )
    amount: str | None = Field(
        description="Extended line amount as a plain decimal string, or null."
    )


class ExtractedInvoice(BaseModel):
    """One invoice as read off the page."""

    vendor_name: TextField = Field(
        description=(
            "The legal or trading name of the party being paid — the entity "
            "that issued the invoice. This is NOT the bill-to party and NOT "
            "the remit-to bank. If a 'Remit To' name differs from the "
            "letterhead, prefer the letterhead/issuer name and note the other "
            "in vendor_remit_to."
        )
    )
    vendor_remit_to: TextField = Field(
        description="The 'Remit To' or payee name, if it differs from the issuer."
    )
    invoice_number: TextField = Field(
        description=(
            "The vendor's own invoice/document number. Copy it exactly, "
            "preserving letters, leading zeros, dashes and slashes. Do NOT use "
            "an account number, PO number, customer number, statement number "
            "or tracking number."
        )
    )
    invoice_date: TextField = Field(
        description=(
            "The invoice date normalized to YYYY-MM-DD. If only a service "
            "period is shown, use the invoice/issue date, not the period."
        )
    )
    due_date: TextField = Field(
        description="The payment due date normalized to YYYY-MM-DD, or null."
    )
    purchase_order: TextField = Field(
        description="The customer PO number if one is printed, else null."
    )
    account_number: TextField = Field(
        description="The vendor's account number for this customer, else null."
    )
    property_hint: TextField = Field(
        description=(
            "Any text identifying which property/site/location this invoice is "
            "for — the bill-to or ship-to name, street address, or site code. "
            "Copy the most specific identifier available."
        )
    )
    currency: TextField = Field(
        description="ISO currency code (e.g. 'USD') if determinable, else null."
    )

    subtotal: MoneyField = Field(description="Subtotal before tax and freight.")
    tax: MoneyField = Field(description="Total tax charged.")
    freight: MoneyField = Field(description="Freight/shipping/delivery charges.")
    other_charges: MoneyField = Field(
        description="Any other additive charges (fuel surcharge, fees, etc.)."
    )
    discount: MoneyField = Field(
        description=(
            "Any discount or credit applied, as a POSITIVE number representing "
            "the amount subtracted. Null if none."
        )
    )
    total_amount: MoneyField = Field(
        description=(
            "The amount payable — the grand total, 'Amount Due', 'Balance Due' "
            "or 'Total'. If a prompt-payment discount gives two totals, use the "
            "full undiscounted amount due and note the discount separately."
        )
    )

    line_items: list[ExtractedLineItem] = Field(
        description=(
            "Every billed line on the invoice, in printed order. Return an "
            "empty list if the invoice has no itemized lines."
        )
    )

    is_credit_memo: bool = Field(
        description="True if this document is a credit memo / negative invoice."
    )
    document_type_note: str | None = Field(
        description=(
            "Set only if the document is NOT a standard invoice — e.g. "
            "'statement', 'quote', 'packing slip', 'receipt'. Null otherwise."
        )
    )
    legibility_note: str | None = Field(
        description=(
            "Set if the scan quality impaired reading: describe what was hard "
            "to read and where. Null if the scan was clean."
        )
    )
    page_range: str | None = Field(
        description="Pages of the source file this invoice occupies, e.g. '1-2'."
    )


class ExtractedDocument(BaseModel):
    """The full result of reading one scanned file."""

    invoices: list[ExtractedInvoice] = Field(
        description=(
            "One entry per distinct invoice in the file. Most files contain "
            "exactly one. Return an empty list only if the file contains no "
            "invoice at all."
        )
    )


class VerificationInvoice(BaseModel):
    """Second-pass read of the fields that reach the accounting system."""

    vendor_name: str | None
    invoice_number: str | None
    invoice_date: str | None = Field(description="Normalized to YYYY-MM-DD.")
    total_amount: str | None = Field(description="Plain decimal string.")


class VerificationDocument(BaseModel):
    invoices: list[VerificationInvoice] = Field(
        description="One entry per invoice in the file, in the same page order."
    )


# --------------------------------------------------------------------------
# Post-processing result types (not sent to the API)
# --------------------------------------------------------------------------

Status = Literal["auto", "review"]


@dataclass
class Finding:
    """A reason an invoice needs a human before it is booked."""

    code: str
    message: str
    severity: Literal["blocker", "warning"] = "blocker"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"[{self.code}] {self.message}"


@dataclass
class InvoiceResult:
    """One extracted invoice after verification, validation and GL coding."""

    source_file: str
    extracted: ExtractedInvoice
    verification: VerificationInvoice | None = None

    vendor_name: str | None = None
    vendor_key: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    total_amount: Decimal | None = None
    gl_account: str | None = None
    gl_rule: str | None = None
    property_code: str | None = None
    findings: list[Finding] = field(default_factory=list)

    def add(self, code: str, message: str, severity: str = "blocker") -> None:
        self.findings.append(Finding(code, message, severity))  # type: ignore[arg-type]

    @property
    def status(self) -> Status:
        return "review" if any(f.severity == "blocker" for f in self.findings) else "auto"

    @property
    def review_reasons(self) -> str:
        return "; ".join(str(f) for f in self.findings)
