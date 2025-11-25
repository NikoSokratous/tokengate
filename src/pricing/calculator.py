"""Cost estimation and calculation logic."""
from typing import Dict, Any, Optional
from .models import PricingTable


class CostCalculator:
    """Calculates costs for OpenAI API requests."""
    
    def __init__(self, pricing_table: Optional[PricingTable] = None):
        """Initialize calculator with pricing table."""
        self.pricing_table = pricing_table or PricingTable()
    
    def estimate_cost(
        self,
        model: str,
        input_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
        messages: Optional[list] = None
    ) -> float:
        """
        Estimate cost before making a request.
        
        Args:
            model: Model name
            input_tokens: Known input token count (if available)
            max_tokens: Maximum tokens requested in response
            messages: List of messages (for chat completions)
            
        Returns:
            Estimated cost in USD
        """
        try:
            pricing = self.pricing_table.get_pricing(model)
        except ValueError:
            # If model not found, use a conservative estimate (gpt-4 pricing)
            pricing = {"input": 0.03, "output": 0.06}
        
        input_price_per_1k = pricing.get("input", 0.0)
        output_price_per_1k = pricing.get("output", 0.0)
        
        # Estimate input tokens
        if input_tokens is not None:
            estimated_input = input_tokens
        elif messages:
            # Rough estimation: ~4 tokens per word, average message ~50 words
            estimated_input = sum(len(str(msg).split()) * 4 for msg in messages)
        else:
            # Default conservative estimate
            estimated_input = 1000
        
        # Estimate output tokens
        if max_tokens is not None:
            estimated_output = max_tokens
        else:
            # Default to 500 tokens for chat completions
            estimated_output = 500
        
        # Calculate cost
        input_cost = (estimated_input / 1000.0) * input_price_per_1k
        output_cost = (estimated_output / 1000.0) * output_price_per_1k
        
        return input_cost + output_cost
    
    def calculate_actual_cost(
        self,
        model: str,
        usage: Dict[str, Any]
    ) -> float:
        """
        Calculate actual cost from OpenAI API response usage field.
        
        Args:
            model: Model name used in the request
            usage: Usage dictionary from OpenAI response (contains prompt_tokens, completion_tokens, total_tokens)
            
        Returns:
            Actual cost in USD
        """
        try:
            pricing = self.pricing_table.get_pricing(model)
        except ValueError:
            # If model not found, use a conservative estimate
            pricing = {"input": 0.03, "output": 0.06}
        
        input_price_per_1k = pricing.get("input", 0.0)
        output_price_per_1k = pricing.get("output", 0.0)
        
        # Extract token counts
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        # Calculate cost
        input_cost = (prompt_tokens / 1000.0) * input_price_per_1k
        output_cost = (completion_tokens / 1000.0) * output_price_per_1k
        
        return input_cost + output_cost
    
    def extract_usage_from_response(self, response_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract usage information from OpenAI API response.
        
        Args:
            response_data: Response JSON from OpenAI API
            
        Returns:
            Usage dictionary or None if not found
        """
        # Check for usage in response (non-streaming)
        if "usage" in response_data:
            return response_data["usage"]
        
        # Check for usage in choices (some response formats)
        if "choices" in response_data and len(response_data["choices"]) > 0:
            choice = response_data["choices"][0]
            if "usage" in choice:
                return choice["usage"]
        
        return None

