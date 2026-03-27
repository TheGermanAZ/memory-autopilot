"""Seed the database with demo caller data."""
import asyncio
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

ROOT_DIR = Path(__file__).resolve().parent.parent

import asyncpg


async def seed(database_url: str):
    conn = await asyncpg.connect(database_url)

    with open(ROOT_DIR / "data" / "memory" / "sarah_chen.json") as f:
        memory = json.load(f)

    await conn.execute(
        """
        INSERT INTO caller_profiles (caller_id, customer_name, issue_summary, issue_type, order_id, customer_sentiment, open_actions)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (caller_id) DO UPDATE SET
            customer_name = $2, issue_summary = $3, issue_type = $4,
            order_id = $5, customer_sentiment = $6, open_actions = $7,
            updated_at = now()
        """,
        "+15551234567",
        memory["customer_name"],
        memory["issue_summary"],
        memory["issue_type"],
        memory["order_id"],
        memory["customer_sentiment"],
        memory["open_actions"],
    )

    await conn.execute(
        """
        INSERT INTO memory_snapshots (conversation_id, caller_id, agent_id, source, data_collection, transcript_summary)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (conversation_id) DO NOTHING
        """,
        "demo_call_001",
        "+15551234567",
        "demo_agent",
        "demo",
        json.dumps(memory),
        "Customer called about a duplicate charge on premium plan order ORD-4521.",
    )

    await conn.close()
    print("Seeded demo data for Sarah Chen (+15551234567)")


if __name__ == "__main__":
    url = os.environ.get("DATABASE_URL", "postgresql://localhost:5432/memory_autopilot")
    asyncio.run(seed(url))
