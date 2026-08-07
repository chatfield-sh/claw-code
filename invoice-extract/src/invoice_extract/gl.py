"""GL account and property assignment.

The GL account is the one required field that is not printed on the invoice —
it is the company's coding decision. So it is resolved from the rules file
rather than read off the page, and anything the rules cannot resolve goes to
review instead of being guessed.
"""

from __future__ import annotations

from .config import Config, GLConfig
from .models import InvoiceResult
from .normalize import collapse_whitespace


def assign(result: InvoiceResult, gl: GLConfig, config: Config) -> None:
    _assign_account(result, gl, config)
    _assign_property(result, config)


def _assign_account(result: InvoiceResult, gl: GLConfig, config: Config) -> None:
    haystack = _searchable_text(result)
    rule = gl.vendor_rules.get(result.vendor_key) if result.vendor_key else None

    if rule is not None:
        match = _first_keyword(rule.keyword_accounts, haystack)
        if match is not None:
            keyword, account = match
            result.gl_account = account
            result.gl_rule = f"vendor '{rule.label}' keyword '{keyword}'"
            return
        if rule.default_account:
            result.gl_account = rule.default_account
            result.gl_rule = f"vendor '{rule.label}' default"
            return

    match = _first_keyword(gl.global_keyword_accounts, haystack)
    if match is not None:
        keyword, account = match
        result.gl_account = account
        result.gl_rule = f"keyword '{keyword}'"
        return

    if gl.fallback_account:
        result.gl_account = gl.fallback_account
        result.gl_rule = "fallback"
        return

    if config.require_gl_account:
        if result.vendor_name is None:
            reason = "no vendor was read, so no coding rule could be applied"
        elif rule is None:
            reason = f"vendor {result.vendor_name!r} has no rule in gl_accounts.yaml"
        else:
            reason = (
                f"vendor {result.vendor_name!r} has a rule but no default account, "
                "and no keyword matched this invoice's line items"
            )
        result.add("no-gl-account", f"could not assign a GL account: {reason}")


def _assign_property(result: InvoiceResult, config: Config) -> None:
    if not config.property_hints:
        return
    hint = collapse_whitespace(result.extracted.property_hint.value)
    if hint:
        lowered = hint.lower()
        # Longest hint first, so "riverside inn conference center" beats
        # "riverside inn" when both are configured.
        for needle in sorted(config.property_hints, key=len, reverse=True):
            if needle in lowered:
                result.property_code = config.property_hints[needle]
                return

    if config.require_property:
        result.add(
            "no-property",
            f"could not match a property from {hint!r}"
            if hint
            else "no bill-to or ship-to text was found to match a property",
        )


def _first_keyword(
    keywords: list[tuple[str, str]], haystack: str
) -> tuple[str, str] | None:
    """Return the first configured keyword present in the text.

    Order follows the config file, so the operator controls precedence by
    ordering the rules rather than having to reason about match length.
    """
    for keyword, account in keywords:
        if keyword and keyword in haystack:
            return keyword, account
    return None


def _searchable_text(result: InvoiceResult) -> str:
    """Everything a keyword rule may match against, lowercased."""
    parts: list[str] = []
    if result.vendor_name:
        parts.append(result.vendor_name)
    for item in result.extracted.line_items:
        parts.append(item.description)
    return " \n".join(parts).lower()
