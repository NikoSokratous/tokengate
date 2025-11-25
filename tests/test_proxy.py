"""Tests for proxy forwarding."""
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from src.proxy.forwarder import OpenAIForwarder


@pytest.mark.asyncio
async def test_forward_request_success(mock_forwarder):
    """Test successful request forwarding."""
    # Mock response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    # Mock json() as a regular method (not async)
    mock_response.json = lambda: {
        "id": "chatcmpl-123",
        "choices": [{"message": {"role": "assistant", "content": "Hello!"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    }
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = ""
    
    mock_forwarder.client.request = AsyncMock(return_value=mock_response)
    
    status_code, response_body, response_headers = await mock_forwarder.forward_request(
        method="POST",
        path="/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        body={"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}
    )
    
    assert status_code == 200
    assert "choices" in response_body
    assert mock_forwarder.client.request.called


@pytest.mark.asyncio
async def test_forward_request_timeout(mock_forwarder):
    """Test request forwarding with timeout."""
    mock_forwarder.client.request = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
    
    status_code, response_body, _ = await mock_forwarder.forward_request(
        method="POST",
        path="/v1/chat/completions",
        headers={},
        body={}
    )
    
    assert status_code == 504
    assert "error" in response_body
    assert response_body["error"]["type"] == "timeout_error"


@pytest.mark.asyncio
async def test_forward_request_connection_error(mock_forwarder):
    """Test request forwarding with connection error."""
    mock_forwarder.client.request = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
    
    status_code, response_body, _ = await mock_forwarder.forward_request(
        method="POST",
        path="/v1/chat/completions",
        headers={},
        body={}
    )
    
    assert status_code == 502
    assert "error" in response_body
    assert response_body["error"]["type"] == "connection_error"


@pytest.mark.asyncio
async def test_forward_request_non_json_response(mock_forwarder):
    """Test handling non-JSON response."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    # Mock json() to raise an exception
    def raise_error():
        raise ValueError("Not JSON")
    mock_response.json = raise_error
    mock_response.text = "Plain text response"
    mock_response.headers = {}
    
    mock_forwarder.client.request = AsyncMock(return_value=mock_response)
    
    status_code, response_body, _ = await mock_forwarder.forward_request(
        method="POST",
        path="/v1/chat/completions",
        headers={},
        body={}
    )
    
    assert status_code == 200
    assert "error" in response_body

