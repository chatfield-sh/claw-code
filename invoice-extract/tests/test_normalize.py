from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from invoice_extract.normalize import (
    invoice_number_key,
    money_str,
    parse_date,
    parse_money,
    vendor_key,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1234.56", Decimal("1234.56")),
        ("$1,234.56", Decimal("1234.56")),
        ("  1,234.56 USD ", Decimal("1234.56")),
        ("(1,234.56)", Decimal("-1234.56")),
        ("-1234.56", Decimal("-1234.56")),
        ("1234.56-", Decimal("-1234.56")),
        ("€1.234,56".replace(".", "").replace(",", "."), Decimal("1234.56")),
        ("0.00", Decimal("0.00")),
        ("1O0.5O", Decimal("100.50")),  # OCR letter-for-digit substitution
        ("$0", Decimal("0")),
    ],
)
def test_parse_money(raw, expected):
    assert parse_money(raw) == expected


@pytest.mark.parametrize(
    "raw", [None, "", "   ", "N/A", "see attached", "$", ".", "12.34.56", "--"]
)
def test_parse_money_rejects_non_amounts(raw):
    assert parse_money(raw) is None


def test_parenthesized_negative_stays_negative_once():
    assert parse_money("($5.00)") == Decimal("-5.00")


def test_money_str_pads_to_cents():
    assert money_str(Decimal("5")) == "5.00"
    assert money_str(None) is None


@pytest.mark.parametrize(
    "a,b",
    [
        ("ACME Supply Co., Inc.", "Acme Supply Company"),
        ("The Grainger Corporation", "Grainger"),
        ("Ecolab Inc.", "ECOLAB  INC"),
        ("Sysco Corporation", "sysco corp"),
    ],
)
def test_vendor_key_collapses_equivalent_names(a, b):
    assert vendor_key(a) == vendor_key(b)


def test_vendor_key_keeps_different_vendors_apart():
    assert vendor_key("Acme Supply") != vendor_key("Acme Services")
    assert vendor_key("") is None
    assert vendor_key(None) is None


@pytest.mark.parametrize(
    "a,b", [("INV-00123", "inv 00123"), ("A/123", "a123"), ("12-34", "1234")]
)
def test_invoice_number_key_ignores_separators_and_case(a, b):
    assert invoice_number_key(a) == invoice_number_key(b)


def test_invoice_number_key_preserves_leading_zeros():
    assert invoice_number_key("INV-0042") != invoice_number_key("INV-42")
    assert invoice_number_key("0042") != invoice_number_key("42")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2026-07-15", dt.date(2026, 7, 15)),
        ("07/15/2026", dt.date(2026, 7, 15)),
        ("Jul 15, 2026", dt.date(2026, 7, 15)),
        ("15 July 2026", dt.date(2026, 7, 15)),
        ("2026/07/15", dt.date(2026, 7, 15)),
    ],
)
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "not a date", "13/45/2026"])
def test_parse_date_rejects_junk(raw):
    assert parse_date(raw) is None
