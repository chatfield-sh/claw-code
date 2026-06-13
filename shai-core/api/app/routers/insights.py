"""Screen 4: Insights — paste/upload data, the active module returns the read."""

from __future__ import annotations

from fastapi import APIRouter, Depends

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
    return _agent.run(ctx, req.raw_input, module_key=req.module_key, label=req.label)
