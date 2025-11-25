"""Tests for pricing calculations."""
import pytest
from src.pricing.calculator import CostCalculator
from src.pricing.models import PricingTable


def test_estimate_cost_with_known_tokens(cost_calculator):
    """Test cost estimation with known token counts."""
    model = "gpt-4"
    input_tokens = 1000
    max_tokens = 500
    
    cost = cost_calculator.estimate_cost(
        model=model,
        input_tokens=input_tokens,
        max_tokens=max_tokens
    )
    
    # gpt-4: input $0.03/1K, output $0.06/1K
    # Expected: (1000/1000 * 0.03) + (500/1000 * 0.06) = 0.03 + 0.03 = 0.06
    assert cost == pytest.approx(0.06, abs=0.001)


def test_estimate_cost_with_messages(cost_calculator):
    """Test cost estimation with messages."""
    model = "gpt-3.5-turbo"
    messages = [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"}
    ]
    
    cost = cost_calculator.estimate_cost(
        model=model,
        messages=messages,
        max_tokens=100
    )
    
    # Should return a positive cost
    assert cost > 0


def test_calculate_actual_cost(cost_calculator):
    """Test calculating actual cost from usage."""
    model = "gpt-4"
    usage = {
        "prompt_tokens": 1000,
        "completion_tokens": 500,
        "total_tokens": 1500
    }
    
    cost = cost_calculator.calculate_actual_cost(model, usage)
    
    # gpt-4: input $0.03/1K, output $0.06/1K
    # Expected: (1000/1000 * 0.03) + (500/1000 * 0.06) = 0.03 + 0.03 = 0.06
    assert cost == pytest.approx(0.06, abs=0.001)


def test_calculate_actual_cost_embedding(cost_calculator):
    """Test calculating cost for embedding model."""
    model = "text-embedding-ada-002"
    usage = {
        "prompt_tokens": 1000,
        "total_tokens": 1000
    }
    
    cost = cost_calculator.calculate_actual_cost(model, usage)
    
    # text-embedding-ada-002: input $0.0001/1K, output $0.0/1K
    # Expected: (1000/1000 * 0.0001) + (0/1000 * 0.0) = 0.0001
    assert cost == pytest.approx(0.0001, abs=0.00001)


def test_extract_usage_from_response(cost_calculator):
    """Test extracting usage from response."""
    response_data = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        },
        "choices": [{"message": {"role": "assistant", "content": "Hello!"}}]
    }
    
    usage = cost_calculator.extract_usage_from_response(response_data)
    
    assert usage is not None
    assert usage["prompt_tokens"] == 100
    assert usage["completion_tokens"] == 50
    assert usage["total_tokens"] == 150


def test_extract_usage_not_found(cost_calculator):
    """Test extracting usage when not present."""
    response_data = {
        "id": "chatcmpl-123",
        "choices": [{"message": {"role": "assistant", "content": "Hello!"}}]
    }
    
    usage = cost_calculator.extract_usage_from_response(response_data)
    
    assert usage is None


def test_pricing_table_get_pricing(pricing_table):
    """Test getting pricing for a model."""
    pricing = pricing_table.get_pricing("gpt-4")
    
    assert "input" in pricing
    assert "output" in pricing
    assert pricing["input"] > 0
    assert pricing["output"] > 0


def test_pricing_table_model_not_found(pricing_table):
    """Test getting pricing for unknown model."""
    with pytest.raises(ValueError):
        pricing_table.get_pricing("unknown-model-xyz")


def test_pricing_table_has_model(pricing_table):
    """Test checking if model exists."""
    assert pricing_table.has_model("gpt-4") is True
    assert pricing_table.has_model("unknown-model") is False

