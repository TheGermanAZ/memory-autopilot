from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db import get_pool
from app.models.schemas import HealthResponse

router = APIRouter(tags=["ops"])


@router.get("/health")
async def health_check():
    try:
        pool = get_pool()
        await pool.fetchval("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    if db_status == "disconnected":
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "disconnected", "version": "0.1.0"},
        )

    return HealthResponse(status="ok", db=db_status, version="0.1.0")
