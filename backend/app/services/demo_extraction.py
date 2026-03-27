"""Demo-only extraction. NOT the production path.
Production uses ElevenLabs native Data Collection via post-call webhooks."""

import json
import re

import httpx
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


def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences if present."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


async def extract_memory_from_transcript(transcript: str) -> dict:
    """Demo-only: extract structured memory from a raw transcript via OpenRouter."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "messages": [
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": transcript},
                ],
                "max_tokens": 512,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        return json.loads(_strip_json_fences(text))
