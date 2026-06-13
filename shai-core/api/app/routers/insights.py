"""Screen 4: Insights — paste/upload data, the active module returns the read.

The parsed record and its insight are persisted (tenant-scoped) when the DB is
available; analysis still runs and returns when it is not.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import repo
from ..agents.module_agent import ModuleAgent
from ..deps import RequestContext, get_current_user
from ..modules.registry import available_modules
from ..schemas import AnalyzeRequest, AnalyzeResponse

router = APIRouter(prefix="/insights", tags=["insights"])
_agent = ModuleAgent()


@router.get("/modules")
def list_modules() -> dict:
    return {"modules": available_modules()}


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, ctx: RequestContext = Depends(get_current_user)) -> AnalyzeResponse:
    result = _agent.run(ctx, req.raw_input, module_key=req.module_key, label=req.label)

    # Persist record + insight (best-effort; analysis already returned).
    record_row = repo.create_module_record(
        ctx, result.record.module_key, result.record.label, result.record.data,
    )
    if record_row:
        repo.create_module_insight(
            ctx, str(record_row["id"]), result.insight.module_key,
            result.insight.model_dump(),
        )
    return result
