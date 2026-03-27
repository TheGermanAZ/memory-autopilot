import re
import structlog

logger = structlog.get_logger()


def normalize_e164(raw: str) -> str:
    """Normalize a phone number to E.164 format.

    Strips formatting characters. If the result starts with +, returns as-is.
    Otherwise prepends +1 (US default for demo).
    Logs a warning if normalization looks unreliable.
    """
    digits = re.sub(r"[^\d+]", "", raw.strip())
    if not digits:
        logger.warning("phone_normalization_failed", raw=raw)
        return raw.strip()
    if digits.startswith("+"):
        return digits
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    logger.warning("phone_normalization_ambiguous", raw=raw, digits=digits)
    return f"+{digits}"
