from __future__ import annotations

import textwrap

import pytest
from conftest import make_invoice, text

from invoice_extract.config import Config, ConfigError, GLConfig
from invoice_extract.gl import assign
from invoice_extract.validate import build

GL_YAML = """
accounts:
  "6410": Food Cost
  "6420": Beverage Cost
  "6215": Repairs - Equipment
  "6340": Telecom
  "9999": Uncoded

keywords:
  "internet": "6340"

vendors:
  - name: "Sysco Corporation"
    account: "6410"
    keywords:
      "wine": "6420"
  - name: "Grainger"
    keywords:
      "hvac": "6215"
"""


@pytest.fixture
def gl(tmp_path):
    path = tmp_path / "gl.yaml"
    path.write_text(textwrap.dedent(GL_YAML))
    return GLConfig.load(path)


def coded(gl, config=None, **overrides):
    config = config or Config()
    result = build("scan.pdf", make_invoice(**overrides), config)
    assign(result, gl, config)
    return result


def test_vendor_default_account(gl):
    assert coded(gl).gl_account == "6410"


def test_vendor_keyword_beats_vendor_default(gl):
    invoice = make_invoice()
    invoice.line_items[0].description = "Case of red wine"
    config = Config()
    result = build("scan.pdf", invoice, config)
    assign(result, gl, config)
    assert result.gl_account == "6420"
    assert "keyword 'wine'" in result.gl_rule


def test_vendor_without_default_falls_through_to_keyword(gl):
    invoice = make_invoice(vendor_name=text("Grainger"))
    invoice.line_items[0].description = "HVAC blower motor"
    config = Config()
    result = build("scan.pdf", invoice, config)
    assign(result, gl, config)
    assert result.gl_account == "6215"


def test_global_keyword_applies_to_unknown_vendor(gl):
    invoice = make_invoice(vendor_name=text("Some Local ISP"))
    invoice.line_items[0].description = "Monthly internet service"
    config = Config()
    result = build("scan.pdf", invoice, config)
    assign(result, gl, config)
    assert result.gl_account == "6340"
    assert result.gl_rule == "keyword 'internet'"


def test_unmapped_vendor_is_held_not_guessed(gl):
    result = coded(gl, vendor_name=text("Totally New Vendor LLC"))
    assert result.gl_account is None
    assert "no-gl-account" in {f.code for f in result.findings}
    assert result.status == "review"


def test_fallback_account_is_used_when_configured(gl, tmp_path):
    path = tmp_path / "gl2.yaml"
    path.write_text(textwrap.dedent(GL_YAML) + '\nfallback_account: "9999"\n')
    gl2 = GLConfig.load(path)
    result = coded(gl2, vendor_name=text("Totally New Vendor LLC"))
    assert result.gl_account == "9999"
    assert result.gl_rule == "fallback"


def test_require_gl_account_off_lets_it_through(gl):
    config = Config(require_gl_account=False)
    result = coded(gl, config=config, vendor_name=text("Totally New Vendor LLC"))
    assert result.gl_account is None
    assert result.status == "auto"


def test_vendor_name_variations_still_match(gl):
    assert coded(gl, vendor_name=text("SYSCO CORP.")).gl_account == "6410"


def test_property_hint_matches_longest_first():
    config = Config(
        property_hints={
            "riverside inn": "HTL-002",
            "riverside inn conference center": "HTL-009",
        }
    )
    result = build(
        "scan.pdf",
        make_invoice(property_hint=text("Riverside Inn Conference Center, Bldg B")),
        config,
    )
    assign(result, GLConfig(), config)
    assert result.property_code == "HTL-009"


def test_require_property_holds_when_unmatched():
    config = Config(property_hints={"riverside inn": "HTL-002"}, require_property=True)
    result = build("scan.pdf", make_invoice(property_hint=text("Somewhere Else")), config)
    assign(result, GLConfig(), config)
    assert "no-property" in {f.code for f in result.findings}


def test_account_typo_is_rejected_at_load(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        'accounts:\n  "6410": Food\nvendors:\n  - name: Sysco\n    account: "6411"\n'
    )
    with pytest.raises(ConfigError, match="not in `accounts`"):
        GLConfig.load(path)
