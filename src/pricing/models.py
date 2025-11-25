"""Pricing table data structures."""
from typing import Dict, Optional
import json
from pathlib import Path


class PricingTable:
    """Manages OpenAI model pricing information."""
    
    def __init__(self, pricing_file: Optional[Path] = None):
        """Initialize pricing table from JSON file."""
        if pricing_file is None:
            # Default to data/pricing_tables.json relative to project root
            pricing_file = Path(__file__).parent.parent.parent / "data" / "pricing_tables.json"
        
        self.pricing_file = pricing_file
        self.prices: Dict[str, Dict[str, float]] = self._load_pricing()
    
    def _load_pricing(self) -> Dict[str, Dict[str, float]]:
        """Load pricing data from JSON file."""
        try:
            with open(self.pricing_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Pricing table file not found: {self.pricing_file}. "
                "Please ensure data/pricing_tables.json exists."
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in pricing table: {e}")
    
    def get_pricing(self, model: str) -> Dict[str, float]:
        """
        Get pricing for a specific model.
        
        Args:
            model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo')
            
        Returns:
            Dictionary with 'input' and 'output' prices per 1K tokens
            
        Raises:
            ValueError: If model is not found in pricing table
        """
        # Try exact match first
        if model in self.prices:
            return self.prices[model]
        
        # Try to find model by prefix (e.g., 'gpt-4-0613' -> 'gpt-4')
        for key in self.prices.keys():
            if model.startswith(key):
                return self.prices[key]
        
        raise ValueError(
            f"Model '{model}' not found in pricing table. "
            f"Available models: {', '.join(self.prices.keys())}"
        )
    
    def has_model(self, model: str) -> bool:
        """Check if model exists in pricing table."""
        try:
            self.get_pricing(model)
            return True
        except ValueError:
            return False

