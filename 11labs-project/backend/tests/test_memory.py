import pytest
from app.services.memory import store_post_call_memory, get_caller_profile

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_create_caller_profile(db_pool):
    data_collection = {
        "customer_name": "Sarah Chen",
        "issue_type": "billing",
        "issue_summary": "Double charged",
        "order_id": "ORD-4521",
        "customer_sentiment": "frustrated",
        "open_actions": "Refund pending",
    }
    inserted = await store_post_call_memory(
        pool=db_pool,
        conversation_id="conv_100",
        caller_id="+15551234567",
        agent_id="agent_test",
        data_collection=data_collection,
        transcript_summary="Billing issue call.",
    )
    assert inserted is True

    profile = await get_caller_profile(db_pool, "+15551234567")
    assert profile is not None
    assert profile["customer_name"] == "Sarah Chen"


async def test_update_existing_profile(db_pool):
    data1 = {
        "customer_name": "Sarah Chen",
        "issue_type": "billing",
        "issue_summary": "Double charged",
        "order_id": "ORD-4521",
        "customer_sentiment": "frustrated",
        "open_actions": "Refund pending",
    }
    await store_post_call_memory(
        pool=db_pool,
        conversation_id="conv_200",
        caller_id="+15559999999",
        agent_id="agent_test",
        data_collection=data1,
        transcript_summary="First call.",
    )

    data2 = {
        "customer_name": "Sarah Chen",
        "issue_type": "technical",
        "issue_summary": "App crashing on login",
        "order_id": "",
        "customer_sentiment": "neutral",
        "open_actions": "Escalated to engineering",
    }
    await store_post_call_memory(
        pool=db_pool,
        conversation_id="conv_201",
        caller_id="+15559999999",
        agent_id="agent_test",
        data_collection=data2,
        transcript_summary="Second call.",
    )

    profile = await get_caller_profile(db_pool, "+15559999999")
    assert profile["issue_type"] == "technical"
    assert profile["issue_summary"] == "App crashing on login"
