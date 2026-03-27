import json

import asyncpg
import structlog

logger = structlog.get_logger()

PROFILE_FIELDS = [
    "customer_name",
    "issue_summary",
    "issue_type",
    "order_id",
    "customer_sentiment",
    "open_actions",
]

DEFAULT_PROFILE = {field: "" for field in PROFILE_FIELDS}


async def store_post_call_memory(
    pool: asyncpg.Pool,
    conversation_id: str,
    caller_id: str,
    agent_id: str | None,
    data_collection: dict,
    transcript_summary: str | None,
) -> bool:
    """Store memory from a post-call webhook. Returns True if new, False if duplicate."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Ensure caller profile exists (FK requirement)
            await conn.execute(
                """
                INSERT INTO caller_profiles (caller_id)
                VALUES ($1)
                ON CONFLICT (caller_id) DO NOTHING
                """,
                caller_id,
            )

            # 2. Insert snapshot (idempotent by conversation_id)
            result = await conn.execute(
                """
                INSERT INTO memory_snapshots
                    (conversation_id, caller_id, agent_id, source, data_collection, transcript_summary)
                VALUES ($1, $2, $3, 'webhook', $4, $5)
                ON CONFLICT (conversation_id) DO NOTHING
                """,
                conversation_id,
                caller_id,
                agent_id,
                json.dumps(data_collection),
                transcript_summary,
            )

            # 3. Only update profile if snapshot was actually inserted
            row_count = int(result.split()[-1])
            if row_count == 0:
                logger.info("duplicate_webhook_ignored", conversation_id=conversation_id)
                return False

            # Update profile with latest data collection fields
            await conn.execute(
                """
                UPDATE caller_profiles SET
                    customer_name = COALESCE(NULLIF($2, ''), customer_name),
                    issue_summary = COALESCE(NULLIF($3, ''), issue_summary),
                    issue_type = COALESCE(NULLIF($4, ''), issue_type),
                    order_id = COALESCE(NULLIF($5, ''), order_id),
                    customer_sentiment = COALESCE(NULLIF($6, ''), customer_sentiment),
                    open_actions = COALESCE(NULLIF($7, ''), open_actions),
                    updated_at = now()
                WHERE caller_id = $1
                """,
                caller_id,
                data_collection.get("customer_name", ""),
                data_collection.get("issue_summary", ""),
                data_collection.get("issue_type", ""),
                data_collection.get("order_id", ""),
                data_collection.get("customer_sentiment", ""),
                data_collection.get("open_actions", ""),
            )

            logger.info(
                "memory_stored",
                conversation_id=conversation_id,
                caller_id=caller_id,
            )
            return True


async def get_caller_profile(pool: asyncpg.Pool, caller_id: str) -> dict | None:
    """Get caller profile. Returns dict or None if unknown caller."""
    row = await pool.fetchrow(
        "SELECT * FROM caller_profiles WHERE caller_id = $1",
        caller_id,
    )
    if row is None:
        return None
    return dict(row)


def profile_to_dynamic_vars(profile: dict | None, caller_id: str = "") -> dict[str, str]:
    """Convert a caller profile to ElevenLabs dynamic variables.
    Always returns ALL keys — empty strings for unknown callers.
    Includes caller_phone so it round-trips back in the post-call webhook."""
    if profile is None:
        result = dict(DEFAULT_PROFILE)
    else:
        result = {field: str(profile.get(field, "")) for field in PROFILE_FIELDS}
    result["caller_phone"] = caller_id
    return result
