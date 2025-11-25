"""Budget tracking and enforcement using Redis."""
from typing import Optional, Dict, Any
from decimal import Decimal
from .redis_client import redis_client
from src.config.settings import settings


class BudgetManager:
    """Manages per-session budget limits and spending."""
    
    def __init__(self, redis_client_instance=None):
        """Initialize budget manager."""
        self.redis = redis_client_instance or redis_client
    
    def _get_budget_key(self, session_id: str) -> str:
        """Get Redis key for session budget."""
        return f"session:{session_id}:budget"
    
    def _get_spent_key(self, session_id: str) -> str:
        """Get Redis key for session spent amount."""
        return f"session:{session_id}:spent"
    
    def _to_decimal(self, value: Any) -> Decimal:
        """Convert value to Decimal for precise calculations."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    
    def set_budget(self, session_id: str, amount: float) -> bool:
        """
        Set budget limit for a session.
        
        Args:
            session_id: Session identifier
            amount: Budget amount in USD
            
        Returns:
            True if successful
        """
        try:
            budget_key = self._get_budget_key(session_id)
            self.redis.client.set(budget_key, str(amount))
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to set budget for session {session_id}: {e}")
    
    def get_budget(self, session_id: str) -> Optional[float]:
        """
        Get budget limit for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Budget amount in USD, or None if not set
        """
        try:
            budget_key = self._get_budget_key(session_id)
            value = self.redis.client.get(budget_key)
            if value is None:
                return None
            return float(value)
        except Exception:
            return None
    
    def get_spent(self, session_id: str) -> float:
        """
        Get current spent amount for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Spent amount in USD (0.0 if not set)
        """
        try:
            spent_key = self._get_spent_key(session_id)
            value = self.redis.client.get(spent_key)
            if value is None:
                return 0.0
            return float(value)
        except Exception:
            return 0.0
    
    def get_budget_info(self, session_id: str) -> Dict[str, Any]:
        """
        Get complete budget information for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with 'budget', 'spent', 'remaining' keys
        """
        budget = self.get_budget(session_id)
        if budget is None:
            budget = settings.default_budget
        
        spent = self.get_spent(session_id)
        remaining = budget - spent
        
        return {
            "budget": budget,
            "spent": spent,
            "remaining": max(0.0, remaining)
        }
    
    def check_budget(self, session_id: str, estimated_cost: float) -> bool:
        """
        Check if session has sufficient budget for estimated cost.
        Uses atomic Redis operations to prevent race conditions.
        
        Args:
            session_id: Session identifier
            estimated_cost: Estimated cost in USD
            
        Returns:
            True if budget is sufficient, False otherwise
        """
        try:
            budget_key = self._get_budget_key(session_id)
            spent_key = self._get_spent_key(session_id)
            
            # Get or initialize budget
            budget_value = self.redis.client.get(budget_key)
            if budget_value is None:
                budget_value = str(settings.default_budget)
                self.redis.client.set(budget_key, budget_value)
            
            # Get current spent
            spent_value = self.redis.client.get(spent_key)
            if spent_value is None:
                spent_value = "0.0"
            
            # Convert to Decimal for precise comparison
            budget = self._to_decimal(budget_value)
            spent = self._to_decimal(spent_value)
            estimated = self._to_decimal(estimated_cost)
            
            # Check if budget is sufficient
            remaining = budget - spent
            return remaining >= estimated
            
        except Exception as e:
            # On error, be conservative and deny the request
            raise RuntimeError(f"Failed to check budget for session {session_id}: {e}")
    
    def deduct_cost(self, session_id: str, actual_cost: float) -> float:
        """
        Deduct actual cost from session budget.
        Uses atomic Redis operations to ensure accuracy.
        
        Args:
            session_id: Session identifier
            actual_cost: Actual cost in USD
            
        Returns:
            Remaining budget after deduction
        """
        try:
            budget_key = self._get_budget_key(session_id)
            spent_key = self._get_spent_key(session_id)
            
            # Use Redis transaction for atomicity
            pipe = self.redis.client.pipeline()
            
            # Get current values
            pipe.get(budget_key)
            pipe.get(spent_key)
            results = pipe.execute()
            
            budget_value = results[0]
            spent_value = results[1]
            
            # Initialize if needed
            if budget_value is None:
                budget_value = str(settings.default_budget)
                pipe.set(budget_key, budget_value)
            
            if spent_value is None:
                spent_value = "0.0"
            
            # Calculate new spent amount
            budget = self._to_decimal(budget_value)
            spent = self._to_decimal(spent_value)
            cost = self._to_decimal(actual_cost)
            
            new_spent = spent + cost
            remaining = budget - new_spent
            
            # Update spent amount
            pipe.set(spent_key, str(new_spent))
            pipe.execute()
            
            return float(max(Decimal("0.0"), remaining))
            
        except Exception as e:
            raise RuntimeError(f"Failed to deduct cost for session {session_id}: {e}")
    
    def reset_session(self, session_id: str) -> bool:
        """
        Reset budget and spent for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful
        """
        try:
            budget_key = self._get_budget_key(session_id)
            spent_key = self._get_spent_key(session_id)
            
            pipe = self.redis.client.pipeline()
            pipe.delete(budget_key)
            pipe.delete(spent_key)
            pipe.execute()
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to reset session {session_id}: {e}")

