"""Configuration loading.

Two files drive the tool:

* `config.yaml`      — model settings, thresholds, and the column layout of the
                       spreadsheet the accounting team uploads.
* `gl_accounts.yaml` — the chart of accounts plus the rules that map a vendor
                       and its line items to a GL account.

Both ship as `.example.yaml` and are meant to be copied and edited per client.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

DEFAULT_MODEL = "claude-opus-5"

# Field name -> header text. The keys are what the exporter knows how to
# produce; the values are whatever the upload template calls them.
DEFAULT_COLUMNS: dict[str, str] = {
    "vendor_name": "Vendor",
    "invoice_number": "Invoice Number",
    "invoice_date": "Invoice Date",
    "gl_account": "GL Account",
    "total_amount": "Amount",
    "property_code": "Property",
    "source_file": "Scan File",
}

KNOWN_COLUMNS = {
    "vendor_name",
    "vendor_remit_to",
    "invoice_number",
    "invoice_date",
    "due_date",
    "purchase_order",
    "account_number",
    "gl_account",
    "gl_rule",
    "subtotal",
    "tax",
    "freight",
    "other_charges",
    "discount",
    "total_amount",
    "currency",
    "property_code",
    "source_file",
    "status",
    "review_reasons",
    "confidence",
}


class ConfigError(ValueError):
    """Raised when a config file is structurally wrong."""


@dataclass
class Config:
    model: str = DEFAULT_MODEL
    effort: str = "high"
    max_tokens: int = 16000
    # Run the independent second read. Disabling it roughly halves cost and
    # removes the strongest guard against a silent misread.
    verify: bool = True
    # Largest absolute difference tolerated when checking that the invoice's
    # own components sum to its stated total.
    arithmetic_tolerance: Decimal = Decimal("0.02")
    # Reject any invoice whose date is more than this many days in the future.
    max_future_days: int = 3
    # Reject any invoice older than this, as a stale-scan guard.
    max_age_days: int = 730
    # Treat these as blockers rather than warnings.
    require_gl_account: bool = True
    require_property: bool = False
    columns: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_COLUMNS))
    # Map a substring found in the bill-to/ship-to text to a property code.
    property_hints: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None) -> "Config":
        if path is None:
            return cls()
        raw = _read_yaml(path)
        cfg = cls()
        cfg.model = raw.get("model", cfg.model)
        cfg.effort = raw.get("effort", cfg.effort)
        cfg.max_tokens = int(raw.get("max_tokens", cfg.max_tokens))
        cfg.verify = bool(raw.get("verify", cfg.verify))
        if "arithmetic_tolerance" in raw:
            cfg.arithmetic_tolerance = Decimal(str(raw["arithmetic_tolerance"]))
        cfg.max_future_days = int(raw.get("max_future_days", cfg.max_future_days))
        cfg.max_age_days = int(raw.get("max_age_days", cfg.max_age_days))
        cfg.require_gl_account = bool(
            raw.get("require_gl_account", cfg.require_gl_account)
        )
        cfg.require_property = bool(raw.get("require_property", cfg.require_property))

        columns = raw.get("columns")
        if columns is not None:
            if not isinstance(columns, dict) or not columns:
                raise ConfigError("`columns` must be a non-empty mapping")
            unknown = set(columns) - KNOWN_COLUMNS
            if unknown:
                raise ConfigError(
                    f"unknown column field(s): {', '.join(sorted(unknown))}. "
                    f"Known fields: {', '.join(sorted(KNOWN_COLUMNS))}"
                )
            cfg.columns = {k: str(v) for k, v in columns.items()}

        hints = raw.get("property_hints") or {}
        if not isinstance(hints, dict):
            raise ConfigError("`property_hints` must be a mapping")
        cfg.property_hints = {str(k).lower(): str(v) for k, v in hints.items()}
        return cfg


@dataclass
class GLRule:
    """One vendor's GL coding, with optional keyword overrides."""

    vendor_key: str
    default_account: str | None
    # (keyword, account) — first keyword found in the invoice text wins.
    keyword_accounts: list[tuple[str, str]] = field(default_factory=list)
    label: str = ""


@dataclass
class GLConfig:
    accounts: dict[str, str] = field(default_factory=dict)  # account -> description
    vendor_rules: dict[str, GLRule] = field(default_factory=dict)  # vendor_key -> rule
    # Applied when no vendor rule matches; first keyword found wins.
    global_keyword_accounts: list[tuple[str, str]] = field(default_factory=list)
    fallback_account: str | None = None

    @classmethod
    def load(cls, path: Path | None) -> "GLConfig":
        if path is None:
            return cls()
        from .normalize import vendor_key as _vendor_key

        raw = _read_yaml(path)
        cfg = cls()

        accounts = raw.get("accounts") or {}
        if not isinstance(accounts, dict):
            raise ConfigError("`accounts` must be a mapping of account -> description")
        cfg.accounts = {str(k): str(v) for k, v in accounts.items()}

        cfg.fallback_account = raw.get("fallback_account")
        if cfg.fallback_account is not None:
            cfg.fallback_account = str(cfg.fallback_account)

        cfg.global_keyword_accounts = _parse_keywords(
            raw.get("keywords") or {}, "keywords"
        )

        vendors = raw.get("vendors") or []
        if not isinstance(vendors, list):
            raise ConfigError("`vendors` must be a list")
        for entry in vendors:
            if not isinstance(entry, dict) or "name" not in entry:
                raise ConfigError("each vendor entry needs at least a `name`")
            name = str(entry["name"])
            key = _vendor_key(name)
            if key is None:
                raise ConfigError(f"vendor name {name!r} normalizes to nothing")
            account = entry.get("account")
            rule = GLRule(
                vendor_key=key,
                default_account=None if account is None else str(account),
                keyword_accounts=_parse_keywords(
                    entry.get("keywords") or {}, f"vendors[{name}].keywords"
                ),
                label=name,
            )
            cfg.vendor_rules[key] = rule

        cfg.validate_accounts()
        return cfg

    def validate_accounts(self) -> None:
        """Every account referenced by a rule must exist in the chart.

        A typo'd account code is worse than an unmapped vendor: unmapped goes
        to review, a typo goes to m3 and bounces later.
        """
        if not self.accounts:
            return
        referenced: list[tuple[str, str]] = []
        if self.fallback_account:
            referenced.append(("fallback_account", self.fallback_account))
        for kw, acct in self.global_keyword_accounts:
            referenced.append((f"keywords[{kw}]", acct))
        for rule in self.vendor_rules.values():
            if rule.default_account:
                referenced.append((f"vendors[{rule.label}]", rule.default_account))
            for kw, acct in rule.keyword_accounts:
                referenced.append((f"vendors[{rule.label}].keywords[{kw}]", acct))
        bad = [(where, acct) for where, acct in referenced if acct not in self.accounts]
        if bad:
            details = ", ".join(f"{where} -> {acct!r}" for where, acct in bad)
            raise ConfigError(f"GL account(s) not in `accounts`: {details}")


def _parse_keywords(raw: Any, where: str) -> list[tuple[str, str]]:
    if not isinstance(raw, dict):
        raise ConfigError(f"`{where}` must be a mapping of keyword -> account")
    return [(str(k).lower(), str(v)) for k, v in raw.items()]


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}") from None
    except yaml.YAMLError as exc:
        raise ConfigError(f"could not parse {path}: {exc}") from None
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a YAML mapping at the top level")
    return data
