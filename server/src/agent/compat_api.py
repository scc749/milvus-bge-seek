"""Python 3.10 compatible FastAPI app that exposes graph-backed compat routes."""

from __future__ import annotations

from fastapi import FastAPI

from agent.api.compat_router import router as compat_router

app = FastAPI(title="RAG Compat API", version="0.1.0")
app.include_router(compat_router)
