from __future__ import annotations

from common.errors import register_exception_handlers
from common.logging import configure_logging
from fastapi import FastAPI

from app.config import settings
from app.domains.admin.router import router as admin_router

configure_logging(settings.log_level)

app = FastAPI(title="admin")
register_exception_handlers(app)
app.include_router(admin_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
