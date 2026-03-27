import pytest
from unittest.mock import AsyncMock, patch, MagicMock

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_extract_returns_structured_fields(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"customer_name":"Sarah Chen","issue_type":"billing","issue_summary":"Double charged","order_id":"ORD-4521","customer_sentiment":"frustrated","open_actions":"Refund pending"}'
                }
            }
        ]
    }

    with patch("app.services.demo_extraction.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        resp = await client.post(
            "/api/demo/extract",
            json={"transcript": "Customer: Hi, my name is Sarah Chen. I was double charged."},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["customer_name"] == "Sarah Chen"
    assert data["issue_type"] == "billing"
