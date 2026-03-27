"""Demo-only extraction. NOT the production path.
Production uses ElevenLabs native Data Collection via post-call webhooks."""

import json
import anthropic
import structlog
from app.config import settings

logger = structlog.get_logger()

EXTRACTION_PROMPT = """Extract structured memory from this support call transcript.
Return ONLY valid JSON with these exact keys:
- customer_name: string (full name or empty string)
- issue_type: string (billing, technical, general, complaint)
- issue_summary: string (one sentence)
- order_id: string (order/reference number or empty string)
- customer_sentiment: string (frustrated, neutral, satisfied, angry, anxious)
- open_actions: string (promised follow-ups or empty string)

Only include facts explicitly stated in the transcript."""


def get_anthropic_client():
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


async def extract_memory_from_transcript(transcript: str) -> dict:
    """Demo-only: extract structured memory from a raw transcript via Claude."""
    client = get_anthropic_client()
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": transcript}],
        system=EXTRACTION_PROMPT,
    )
    text = response.content[0].text
    return json.loads(text)
