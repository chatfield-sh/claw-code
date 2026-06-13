"""SHAI Core API entrypoint.

Wires the six screens onto one domain-neutral FastAPI app. Runs without a
database or Claude key (agents degrade to heuristics) so the scaffold is
immediately runnable.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import settings
from .db import db_available
from .modules.registry import available_modules
from .routers import brief, inbox, initiatives, insights, notebook, tasks

app = FastAPI(title="SHAI Core", version=__version__,
              description="The domain-neutral executive operating system.")

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


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "database": db_available(),
        "claude": settings.has_claude,
        "model": settings.shai_model,
        "modules": available_modules(),
    }
