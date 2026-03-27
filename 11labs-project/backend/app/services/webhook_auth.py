import hashlib
import hmac
import time

import structlog
from fastapi import HTTPException, Request

from app.config import settings

logger = structlog.get_logger()

MAX_TIMESTAMP_AGE_SECONDS = 300  # 5 minutes


async def verify_elevenlabs_signature(request: Request) -> bytes:
    """Verify ElevenLabs webhook HMAC signature. Returns raw body on success."""
    if not settings.elevenlabs_webhook_secret:
        logger.warning("webhook_auth_failed", reason="missing_webhook_secret")
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    sig_header = request.headers.get("ElevenLabs-Signature", "")
    if not sig_header:
        logger.warning("webhook_auth_failed", reason="missing_signature_header")
        raise HTTPException(status_code=401, detail="Missing signature")

    body = await request.body()

    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    timestamp = parts.get("t", "")
    signature = parts.get("v1", "")

    if not timestamp or not signature:
        logger.warning("webhook_auth_failed", reason="malformed_signature_header")
        raise HTTPException(status_code=401, detail="Malformed signature")

    # Check timestamp freshness
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > MAX_TIMESTAMP_AGE_SECONDS:
            logger.warning("webhook_auth_failed", reason="stale_timestamp")
            raise HTTPException(status_code=401, detail="Stale timestamp")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp")

    # Verify HMAC
    sig_payload = f"{timestamp}.{body.decode()}"
    expected = hmac.new(
        settings.elevenlabs_webhook_secret.encode(),
        sig_payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        logger.warning("webhook_auth_failed", reason="invalid_signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    logger.info("webhook_auth_success")
    return body
