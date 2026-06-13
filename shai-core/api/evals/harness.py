"""Eval cases for SHAI Core agents.

Each case asserts a *property* of an agent's output rather than an exact string,
so it works on both the deterministic offline heuristics and (more loosely) real
Claude output. Structural cases run anywhere; the LLM-judge case demonstrates
the grading pattern and is skipped (counted as pass) when no Claude key is set.

Run:  python -m evals
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.email import EmailAgent
from app.agents.orchestrator import Intent, Orchestrator
from app.agents.task import TaskAgent
from app.claude import complete
from app.config import settings
from app.deps import RequestContext
from app.modules.registry import get_module

CTX = RequestContext(tenant_id="eval", user_id="eval", role="founder")


@dataclass
class EvalResult:
    name: str
    passed: bool
    detail: str


def _r(name: str, passed: bool, detail: str) -> EvalResult:
    return EvalResult(name, passed, detail)


# ---- Structural cases (deterministic offline) -----------------------------
def case_generic_module_surfaces_number() -> EvalResult:
    mod = get_module("generic")
    insight = mod.analyze(CTX, mod.parse(CTX, "revenue,1200\ncost,800", label="Q2"))
    ok = insight.impact == 1200 and insight.severity in {"green", "amber", "red"}
    return _r("generic_module_surfaces_number", ok, f"impact={insight.impact} sev={insight.severity}")


def case_generic_module_no_numbers_is_green() -> EvalResult:
    mod = get_module("generic")
    insight = mod.analyze(CTX, mod.parse(CTX, "note: kickoff went well"))
    ok = insight.severity == "green" and insight.impact is None
    return _r("generic_module_no_numbers_is_green", ok, f"sev={insight.severity}")


def case_task_extraction_finds_action_items() -> EvalResult:
    tasks = TaskAgent().extract(CTX, "- TODO: ship the build\nrandom line\nAction: review the PR")
    ok = len(tasks) >= 2
    return _r("task_extraction_finds_action_items", ok, f"{len(tasks)} tasks")


def case_email_triage_ranks_questions_higher() -> EvalResult:
    agent = EmailAgent()
    q = agent.triage(CTX, "a@b.com", "Need input", "Can you approve this today?")
    s = agent.triage(CTX, "a@b.com", "FYI", "Sharing the deck for reference.")
    ok = q > s
    return _r("email_triage_ranks_questions_higher", ok, f"question={q} statement={s}")


def case_orchestrator_routes_email() -> EvalResult:
    intent = Orchestrator().classify("draft a reply to this email")
    ok = intent == Intent.EMAIL
    return _r("orchestrator_routes_email", ok, f"intent={intent.value}")


# ---- LLM-judge case (skipped without Claude) ------------------------------
def case_llm_judge_insight_is_actionable() -> EvalResult:
    if not settings.has_claude:
        return _r("llm_judge_insight_is_actionable", True, "skipped (no Claude key)")
    mod = get_module("generic")
    insight = mod.analyze(CTX, mod.parse(CTX, "revenue,1200\ncost,1800", label="Q2"))
    verdict = complete(
        CTX,
        system="You grade an executive insight. Reply with only PASS or FAIL. "
               "PASS if it names a concrete action; FAIL otherwise.",
        user=f"Headline: {insight.headline}\nAction: {insight.action}",
        max_tokens=4,
    )
    ok = bool(verdict) and "PASS" in verdict.upper()
    return _r("llm_judge_insight_is_actionable", ok, f"verdict={verdict!r}")


CASES = [
    case_generic_module_surfaces_number,
    case_generic_module_no_numbers_is_green,
    case_task_extraction_finds_action_items,
    case_email_triage_ranks_questions_higher,
    case_orchestrator_routes_email,
    case_llm_judge_insight_is_actionable,
]


def run_evals() -> list[EvalResult]:
    return [case() for case in CASES]
