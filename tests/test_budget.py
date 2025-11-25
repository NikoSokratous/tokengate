"""Tests for budget management."""
import pytest
from src.budget.manager import BudgetManager
from src.config.settings import settings


def test_set_and_get_budget(budget_manager):
    """Test setting and getting budget."""
    session_id = "test-session-1"
    budget_amount = 25.50
    
    # Set budget
    result = budget_manager.set_budget(session_id, budget_amount)
    assert result is True
    
    # Get budget
    retrieved = budget_manager.get_budget(session_id)
    assert retrieved == budget_amount


def test_get_default_budget(budget_manager):
    """Test getting default budget when not set."""
    session_id = "test-session-2"
    
    # Budget not set, should return None
    budget = budget_manager.get_budget(session_id)
    assert budget is None
    
    # But get_budget_info should use default
    info = budget_manager.get_budget_info(session_id)
    assert info["budget"] == settings.default_budget


def test_get_spent_defaults_to_zero(budget_manager):
    """Test that spent defaults to zero."""
    session_id = "test-session-3"
    
    spent = budget_manager.get_spent(session_id)
    assert spent == 0.0


def test_check_budget_sufficient(budget_manager):
    """Test budget check when sufficient funds available."""
    session_id = "test-session-4"
    budget_amount = 10.0
    
    budget_manager.set_budget(session_id, budget_amount)
    
    # Check with small cost
    has_budget = budget_manager.check_budget(session_id, 5.0)
    assert has_budget is True


def test_check_budget_insufficient(budget_manager):
    """Test budget check when insufficient funds."""
    session_id = "test-session-5"
    budget_amount = 10.0
    
    budget_manager.set_budget(session_id, budget_amount)
    
    # Check with large cost
    has_budget = budget_manager.check_budget(session_id, 15.0)
    assert has_budget is False


def test_deduct_cost(budget_manager):
    """Test deducting cost from budget."""
    session_id = "test-session-6"
    budget_amount = 10.0
    cost = 3.5
    
    budget_manager.set_budget(session_id, budget_amount)
    
    # Deduct cost
    remaining = budget_manager.deduct_cost(session_id, cost)
    
    # Check remaining
    assert remaining == pytest.approx(budget_amount - cost, abs=0.01)
    
    # Check spent
    spent = budget_manager.get_spent(session_id)
    assert spent == pytest.approx(cost, abs=0.01)


def test_deduct_cost_multiple_times(budget_manager):
    """Test deducting cost multiple times."""
    session_id = "test-session-7"
    budget_amount = 10.0
    
    budget_manager.set_budget(session_id, budget_amount)
    
    # Deduct multiple times
    budget_manager.deduct_cost(session_id, 2.0)
    budget_manager.deduct_cost(session_id, 3.0)
    remaining = budget_manager.deduct_cost(session_id, 1.5)
    
    # Total deducted: 2.0 + 3.0 + 1.5 = 6.5
    assert remaining == pytest.approx(3.5, abs=0.01)
    
    spent = budget_manager.get_spent(session_id)
    assert spent == pytest.approx(6.5, abs=0.01)


def test_get_budget_info(budget_manager):
    """Test getting complete budget information."""
    session_id = "test-session-8"
    budget_amount = 20.0
    
    budget_manager.set_budget(session_id, budget_amount)
    budget_manager.deduct_cost(session_id, 7.5)
    
    info = budget_manager.get_budget_info(session_id)
    
    assert info["budget"] == budget_amount
    assert info["spent"] == pytest.approx(7.5, abs=0.01)
    assert info["remaining"] == pytest.approx(12.5, abs=0.01)


def test_reset_session(budget_manager):
    """Test resetting a session."""
    session_id = "test-session-9"
    budget_amount = 10.0
    
    budget_manager.set_budget(session_id, budget_amount)
    budget_manager.deduct_cost(session_id, 5.0)
    
    # Reset
    result = budget_manager.reset_session(session_id)
    assert result is True
    
    # Check that budget and spent are cleared
    budget = budget_manager.get_budget(session_id)
    assert budget is None
    
    spent = budget_manager.get_spent(session_id)
    assert spent == 0.0

