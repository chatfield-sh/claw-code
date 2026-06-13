"""SHAI Core API entrypoint.

Wires the six screens onto one domain-neutral FastAPI app. Runs without a
database or Claude key (agents degrade to heuristics) so the scaffold is
immediately runnable.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__, google
from .config import settings
from .db import db_available
from .modules.registry import available_modules
from .observability import RequestLogMiddleware, configure_logging
from .routers import (
    ask, audit, brief, inbox, initiatives, insights, notebook, profile, risks, tasks,
)
from .routers import google as google_router

log = logging.getLogger("shai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    issues = settings.problems()
    if issues:
        message = "Insecure configuration: " + "; ".join(issues)
        if settings.is_prod:
            # Fail closed: refuse to start a misconfigured production server.
            raise RuntimeError(message)
        log.warning("%s (allowed in dev)", message)
    yield


app = FastAPI(title="SHAI Core", version=__version__, lifespan=lifespan,
              description="The domain-neutral executive operating system.")

app.add_middleware(RequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(brief.router)
app.include_router(inbox.router)
app.include_router(tasks.router)
app.include_router(insights.router)
app.include_router(initiatives.router)
app.include_router(notebook.router)
app.include_router(ask.router)
app.include_router(profile.router)
app.include_router(audit.router)
app.include_router(risks.router)
app.include_router(google_router.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "database": db_available(),
        "claude": settings.has_claude,
        "model": settings.shai_model,
        "google": google.is_configured(),
        "clerk": bool(settings.clerk_secret_key),
        "modules": available_modules(),
    }
