from app.db import get_pool
from app.models.schemas import HealthResponse
from fastapi import APIRouter

router = APIRouter(tags=["ops"])


@router.get("/health")
async def health_check() -> HealthResponse:
    try:
        pool = get_pool()
        await pool.fetchval("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(status="ok", db=db_status, version="0.1.0")
