"""Risk agent + endpoints (hermetic) and the eval harness."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.agents.risk import RiskAgent
from app.deps import RequestContext
from app.main import app
from evals.harness import run_evals

client = TestClient(app)
CTX = RequestContext(tenant_id="t", user_id="u")


def test_risk_scan_noop_without_db():
    # No DB -> repo reads return None -> nothing to scan, no crash.
    assert RiskAgent().scan(CTX) == []


def test_risks_endpoints_shape():
    body = client.get("/risks").json()
    assert "risks" in body and isinstance(body["risks"], list)
    scanned = client.post("/risks/scan").json()
    assert "created" in scanned and isinstance(scanned["created"], int)


def test_all_evals_pass():
    results = run_evals()
    failed = [r.name for r in results if not r.passed]
    assert not failed, f"failing evals: {failed}"
