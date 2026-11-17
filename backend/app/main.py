from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.routers import (
    assessments, auth, dashboard, profile, progress,
    recommendations, sections, skills,
)

logging.basicConfig(level=settings.LOG_LEVEL)
log = logging.getLogger("app")

app = FastAPI(
    title="AI-Driven Personalized Coding Practice Recommender",
    version="0.1.0",
    description="Personalized coding-practice recommendation platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, profile.router, sections.router, progress.router,
          assessments.router, skills.router, recommendations.router, dashboard.router):
    app.include_router(r)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.ENV}


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )