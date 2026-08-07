"""A record of invoices already submitted, for duplicate detection.

Paying the same invoice twice is the most expensive error in AP, and it is
exactly the error a batch-scanning workflow invites: the same paper goes
through the scanner twice, or a vendor re-sends a copy that gets filed again.
The ledger is a small SQLite file that survives between runs so the second
copy is caught rather than booked.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from decimal import Decimal
from pathlib import Path

from .models import InvoiceResult
from .normalize import invoice_number_key

_SCHEMA = """
CREATE TABLE IF NOT EXISTS submitted_invoices (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_key         TEXT    NOT NULL,
    vendor_name        TEXT,
    invoice_number_key TEXT    NOT NULL,
    invoice_number     TEXT,
    invoice_date       TEXT,
    total_cents        INTEGER,
    source_file        TEXT,
    exported_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_vendor_invoice
    ON submitted_invoices (vendor_key, invoice_number_key);
CREATE INDEX IF NOT EXISTS idx_vendor_amount
    ON submitted_invoices (vendor_key, total_cents, invoice_date);
"""


def _cents(value: Decimal | None) -> int | None:
    if value is None:
        return None
    return int(value.quantize(Decimal("0.01")) * 100)


class Ledger:
    """Duplicate history. Use as a context manager."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self._conn: sqlite3.Connection | None = None
        # Keys seen earlier in this same run, so a file scanned twice in one
        # batch is caught before either copy is written.
        self._pending: dict[tuple[str, str], str] = {}

    def __enter__(self) -> "Ledger":
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.path)
            self._conn.executescript(_SCHEMA)
            self._conn.commit()
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def enabled(self) -> bool:
        return self._conn is not None

    def check(self, result: InvoiceResult) -> None:
        """Flag the result if this invoice has been seen before."""
        vkey = result.vendor_key
        ikey = invoice_number_key(result.invoice_number)
        if vkey is None or ikey is None:
            return  # missing-field already blocks these

        prior = self._pending.get((vkey, ikey))
        if prior is not None:
            result.add(
                "duplicate-in-batch",
                f"the same vendor and invoice number also appears in this batch "
                f"in {prior}",
            )
            return
        self._pending[(vkey, ikey)] = result.source_file

        if self._conn is None:
            return

        with closing(self._conn.cursor()) as cur:
            cur.execute(
                "SELECT source_file, exported_at, total_cents "
                "FROM submitted_invoices "
                "WHERE vendor_key = ? AND invoice_number_key = ?",
                (vkey, ikey),
            )
            row = cur.fetchone()
            if row is not None:
                source, when, cents = row
                amount = "" if cents is None else f" for {Decimal(cents) / 100:,.2f}"
                result.add(
                    "duplicate",
                    f"already submitted on {when} from {source}{amount}",
                )
                return

            # Same vendor, same amount, same date, different number. Often a
            # re-issued invoice with a new number; occasionally a genuine
            # second charge. A human decides.
            cents = _cents(result.total_amount)
            if cents is not None and result.invoice_date:
                cur.execute(
                    "SELECT invoice_number, source_file FROM submitted_invoices "
                    "WHERE vendor_key = ? AND total_cents = ? AND invoice_date = ?",
                    (vkey, cents, result.invoice_date),
                )
                near = cur.fetchone()
                if near is not None:
                    result.add(
                        "possible-duplicate",
                        f"same vendor, amount and date as invoice "
                        f"{near[0]!r} from {near[1]}",
                        severity="warning",
                    )

    def record(self, results: list[InvoiceResult]) -> int:
        """Record exported invoices so the next run sees them. Returns the count."""
        if self._conn is None:
            return 0
        written = 0
        with closing(self._conn.cursor()) as cur:
            for result in results:
                ikey = invoice_number_key(result.invoice_number)
                if result.vendor_key is None or ikey is None:
                    continue
                cur.execute(
                    "INSERT OR IGNORE INTO submitted_invoices "
                    "(vendor_key, vendor_name, invoice_number_key, invoice_number, "
                    " invoice_date, total_cents, source_file) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        result.vendor_key,
                        result.vendor_name,
                        ikey,
                        result.invoice_number,
                        result.invoice_date,
                        _cents(result.total_amount),
                        result.source_file,
                    ),
                )
                written += cur.rowcount
        self._conn.commit()
        return written
