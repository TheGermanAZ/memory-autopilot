import pytest
from tests.conftest import sign_payload, make_post_call_payload, WEBHOOK_SECRET

pytestmark = pytest.mark.asyncio(loop_scope="session")


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


async def test_post_call_webhook_rejects_malformed_payload(client, db_pool):
    payload = {"garbage": True}
    headers = sign_payload(payload)
    resp = await client.post("/webhooks/elevenlabs/post-call", json=payload, headers=headers)
    assert resp.status_code == 422

    count = await db_pool.fetchval("SELECT COUNT(*) FROM caller_profiles")
    assert count == 0


async def test_post_call_webhook_idempotent(client, db_pool):
    payload = make_post_call_payload(conversation_id="conv_idem")
    headers = sign_payload(payload)

    resp1 = await client.post("/webhooks/elevenlabs/post-call", json=payload, headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["new"] is True

    headers2 = sign_payload(payload)  # re-sign with fresh timestamp
    resp2 = await client.post("/webhooks/elevenlabs/post-call", json=payload, headers=headers2)
    assert resp2.status_code == 200
    assert resp2.json()["new"] is False

    snapshot_count = await db_pool.fetchval("SELECT COUNT(*) FROM memory_snapshots")
    assert snapshot_count == 1


async def test_post_call_idempotency_enforced_by_db_constraint(db_pool):
    """Verify the UNIQUE constraint on conversation_id catches duplicates at DB level."""
    from app.services.memory import store_post_call_memory

    data = {"customer_name": "Test", "issue_type": "test"}
    await store_post_call_memory(
        pool=db_pool,
        conversation_id="conv_unique",
        caller_id="+15550000001",
        agent_id="agent_test",
        data_collection=data,
        transcript_summary="Test",
    )
    # Second insert with same conversation_id should return False, not raise
    result = await store_post_call_memory(
        pool=db_pool,
        conversation_id="conv_unique",
        caller_id="+15550000001",
        agent_id="agent_test",
        data_collection=data,
        transcript_summary="Test",
    )
    assert result is False


async def test_conversation_init_returns_dynamic_vars(client, db_pool):
    # Seed a known caller
    payload = make_post_call_payload(conversation_id="conv_init_test", caller_id="+15553334444")
    headers = sign_payload(payload)
    await client.post("/webhooks/elevenlabs/post-call", json=payload, headers=headers)

    resp = await client.post(
        "/webhooks/elevenlabs/conversation-init",
        json={"caller_id": "+15553334444", "agent_id": "agent_test"},
    )
    assert resp.status_code == 200
    dv = resp.json()["dynamic_variables"]
    assert dv["customer_name"] == "Sarah Chen"
    assert dv["issue_type"] == "billing"
    assert "issue_summary" in dv
    assert "order_id" in dv
    assert "customer_sentiment" in dv
    assert "open_actions" in dv


async def test_conversation_init_unknown_caller(client):
    resp = await client.post(
        "/webhooks/elevenlabs/conversation-init",
        json={"caller_id": "+10000000000", "agent_id": "agent_test"},
    )
    assert resp.status_code == 200
    dv = resp.json()["dynamic_variables"]
    assert dv["customer_name"] == ""
    assert dv["issue_summary"] == ""
    assert dv["caller_phone"] == "+10000000000"
    assert len(dv) == 7  # 6 profile fields + caller_phone


async def test_conversation_init_missing_caller_id(client):
    resp = await client.post(
        "/webhooks/elevenlabs/conversation-init",
        json={"agent_id": "agent_test"},
    )
    assert resp.status_code == 422
