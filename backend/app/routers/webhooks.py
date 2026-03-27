import json

import structlog
from fastapi import APIRouter, Request, Response

from app.db import get_pool
from app.models.schemas import (
    ConversationInitPayload,
    DynamicVariablesResponse,
    PostCallWebhookPayload,
)
from app.services.memory import get_caller_profile, profile_to_dynamic_vars, store_post_call_memory
from app.services.phone import normalize_e164
from app.services.webhook_auth import verify_elevenlabs_signature

logger = structlog.get_logger()
router = APIRouter(prefix="/webhooks/elevenlabs", tags=["webhooks"])


@router.post("/post-call")
async def post_call_webhook(request: Request):
    body = await verify_elevenlabs_signature(request)

    try:
        payload = PostCallWebhookPayload.model_validate_json(body)
    except Exception:
        logger.warning("webhook_malformed_payload")
        return Response(status_code=422, content="Malformed payload")

    data_collection = payload.get_data_collection_results()
    transcript_summary = payload.get_transcript_summary()

    # Extract caller_id from conversation_initiation_client_data.
    # When a call arrives, our conversation-init webhook returns caller_phone
    # as a dynamic variable. ElevenLabs round-trips it back in the post-call payload.
    raw_data = json.loads(body)
    init_data = raw_data.get("conversation_initiation_client_data", {})
    dynamic_vars = init_data.get("dynamic_variables", {})
    raw_caller_id = dynamic_vars.get("caller_phone", "")

    # Fallback: check metadata for phone info (Twilio calls)
    if not raw_caller_id:
        raw_caller_id = raw_data.get("metadata", {}).get("phone", {}).get("caller_id", "")

    if not raw_caller_id:
        logger.warning("post_call_no_caller_id", conversation_id=payload.conversation_id)
        raw_caller_id = f"unknown_{payload.conversation_id}"

    caller_id = normalize_e164(raw_caller_id)

    pool = get_pool()
    inserted = await store_post_call_memory(
        pool=pool,
        conversation_id=payload.conversation_id,
        caller_id=caller_id,
        agent_id=payload.agent_id,
        data_collection=data_collection,
        transcript_summary=transcript_summary,
    )

    logger.info(
        "webhook_received",
        conversation_id=payload.conversation_id,
        caller_id=caller_id,
        new=inserted,
    )
    return {"status": "ok", "new": inserted}


@router.post("/conversation-init")
async def conversation_init(request: Request):
    body = await request.json()

    raw_caller_id = body.get("caller_id", "")
    if not raw_caller_id:
        logger.warning("conversation_init_missing_caller_id")
        return Response(status_code=400, content="Missing caller_id")

    caller_id = normalize_e164(raw_caller_id)
    pool = get_pool()
    profile = await get_caller_profile(pool, caller_id)
    dynamic_vars = profile_to_dynamic_vars(profile, caller_id=caller_id)

    logger.info(
        "conversation_init",
        caller_id=caller_id,
        known=profile is not None,
    )

    return DynamicVariablesResponse(dynamic_variables=dynamic_vars)
