import pytest
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_extract_returns_structured_fields(client):
    mock_response = AsyncMock()
    mock_response.content = [
        AsyncMock(text='{"customer_name":"Sarah Chen","issue_type":"billing","issue_summary":"Double charged","order_id":"ORD-4521","customer_sentiment":"frustrated","open_actions":"Refund pending"}')
    ]

    with patch("app.services.demo_extraction.get_anthropic_client") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(return_value=mock_response)
        resp = await client.post(
            "/api/demo/extract",
            json={"transcript": "Customer: Hi, my name is Sarah Chen. I was double charged."},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["customer_name"] == "Sarah Chen"
    assert data["issue_type"] == "billing"
