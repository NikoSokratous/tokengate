"""Pytest configuration and fixtures."""
import pytest
from fakeredis import FakeRedis
from unittest.mock import Mock, AsyncMock

from src.budget.redis_client import RedisClient
from src.budget.manager import BudgetManager
from src.pricing.calculator import CostCalculator
from src.pricing.models import PricingTable
from src.proxy.forwarder import OpenAIForwarder


@pytest.fixture
def fake_redis():
    """Provide a fake Redis instance for testing."""
    return FakeRedis(decode_responses=True)


@pytest.fixture
def redis_client(fake_redis):
    """Provide a RedisClient with fake Redis."""
    client = RedisClient()
    client._client = fake_redis
    return client


@pytest.fixture
def budget_manager(redis_client):
    """Provide a BudgetManager with fake Redis."""
    return BudgetManager(redis_client_instance=redis_client)


@pytest.fixture
def pricing_table():
    """Provide a PricingTable instance."""
    return PricingTable()


@pytest.fixture
def cost_calculator(pricing_table):
    """Provide a CostCalculator instance."""
    return CostCalculator(pricing_table)


@pytest.fixture
def mock_forwarder():
    """Provide a mock OpenAIForwarder."""
    forwarder = OpenAIForwarder(api_key="test-key", base_url="https://api.openai.com/v1")
    forwarder._client = AsyncMock()
    return forwarder

