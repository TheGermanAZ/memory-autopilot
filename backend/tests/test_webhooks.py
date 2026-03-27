import pytest
from tests.conftest import sign_payload, make_post_call_payload, WEBHOOK_SECRET

pytestmark = pytest.mark.asyncio


async def test_post_call_webhook_stores_memory(client, db_pool):
    payload = make_post_call_payload()
    headers = sign_payload(payload)
    resp = await client.post("/webhooks/elevenlabs/post-call", json=payload, headers=headers)
    assert resp.status_code == 200

    profile = await db_pool.fetchrow(
        "SELECT * FROM caller_profiles WHERE caller_id = $1", "+15551234567"
    )
    assert profile is not None
    assert profile["customer_name"] == "Sarah Chen"
    assert profile["issue_type"] == "billing"

    snapshot = await db_pool.fetchrow(
        "SELECT * FROM memory_snapshots WHERE conversation_id = $1", "conv_001"
    )
    assert snapshot is not None
    assert snapshot["source"] == "webhook"


async def test_post_call_webhook_rejects_invalid_signature(client, db_pool):
    payload = make_post_call_payload()
    headers = sign_payload(payload, secret="wrong-secret")
    resp = await client.post("/webhooks/elevenlabs/post-call", json=payload, headers=headers)
    assert resp.status_code == 401

    count = await db_pool.fetchval("SELECT COUNT(*) FROM caller_profiles")
    assert count == 0
