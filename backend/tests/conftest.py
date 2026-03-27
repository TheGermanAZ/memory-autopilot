import asyncio
import hashlib
import hmac
import json
import os
import time
from typing import AsyncGenerator

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from testcontainers.postgres import PostgresContainer

WEBHOOK_SECRET = "test-webhook-secret-1234"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
async def db_pool(postgres_container) -> AsyncGenerator[asyncpg.Pool, None]:
    url = postgres_container.get_connection_url().replace("postgresql+psycopg2://", "postgresql://")
    pool = await asyncpg.create_pool(url, min_size=1, max_size=5)
    schema_path = os.path.join(os.path.dirname(__file__), "..", "schema.sql")
    with open(schema_path) as f:
        await pool.execute(f.read())
    yield pool
    await pool.close()


@pytest.fixture(autouse=True)
async def clean_tables(db_pool):
    yield
    await db_pool.execute("DELETE FROM memory_snapshots")
    await db_pool.execute("DELETE FROM caller_profiles")


@pytest.fixture
async def client(db_pool, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setenv("DATABASE_URL", "unused")
    monkeypatch.setenv("ELEVENLABS_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    # Force settings reload with test env vars
    from app import config as config_module
    config_module.settings = config_module.Settings()

    from app.main import app
    from app import db as db_module
    db_module._pool = db_pool

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def sign_payload(payload: dict, secret: str = WEBHOOK_SECRET) -> dict:
    """Generate ElevenLabs-Signature header for a payload."""
    body = json.dumps(payload).encode()
    timestamp = str(int(time.time()))
    sig_payload = f"{timestamp}.{body.decode()}"
    signature = hmac.new(secret.encode(), sig_payload.encode(), hashlib.sha256).hexdigest()
    return {
        "ElevenLabs-Signature": f"t={timestamp},v1={signature}",
        "Content-Type": "application/json",
    }


def make_post_call_payload(
    conversation_id: str = "conv_001",
    caller_id: str = "+15551234567",
    agent_id: str = "agent_test",
) -> dict:
    return {
        "agent_id": agent_id,
        "conversation_id": conversation_id,
        "status": "done",
        "transcript": [
            {"role": "user", "message": "Hi, my name is Sarah Chen."},
            {"role": "agent", "message": "Hello Sarah, how can I help?"},
        ],
        "analysis": {
            "transcript_summary": "Customer called about a billing issue.",
            "data_collection_results": {
                "customer_name": "Sarah Chen",
                "issue_type": "billing",
                "issue_summary": "Double charged for premium plan",
                "order_id": "ORD-4521",
                "customer_sentiment": "frustrated",
                "open_actions": "Refund pending",
            },
        },
        "metadata": {
            "phone": {"caller_id": caller_id},
        },
    }
