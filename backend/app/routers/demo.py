import structlog
from fastapi import APIRouter, HTTPException

from app.db import get_pool
from app.models.schemas import (
    CallerProfile,
    DemoExtractionRequest,
    DemoExtractionResponse,
)
from app.services.demo_extraction import extract_memory_from_transcript
from app.services.memory import get_caller_profile

logger = structlog.get_logger()
router = APIRouter(prefix="/api/demo", tags=["demo"])

DEMO_CALLER_ID = "+15551234567"


@router.get("/memory/{caller_id}")
async def get_demo_memory(caller_id: str) -> CallerProfile:
    if caller_id != DEMO_CALLER_ID:
        raise HTTPException(status_code=404, detail="Caller not found")
    pool = get_pool()
    profile = await get_caller_profile(pool, caller_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Caller not found")
    return CallerProfile(**profile)


@router.post("/extract")
async def demo_extract(req: DemoExtractionRequest) -> DemoExtractionResponse:
    """Demo-only endpoint. Production uses ElevenLabs Data Collection."""
    try:
        result = await extract_memory_from_transcript(req.transcript)
        return DemoExtractionResponse(**result)
    except Exception as e:
        logger.error("demo_extraction_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Extraction failed")
