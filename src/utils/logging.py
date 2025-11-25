"""Structured logging setup."""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from src.config.settings import settings


def setup_logging():
    """Configure structured JSON logging."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format='%(message)s',
        handlers=[logging.StreamHandler()]
    )


def log_request(
    session_id: str,
    model: str,
    estimated_cost: float,
    decision: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    actual_cost: Optional[float] = None,
    error: Optional[str] = None
):
    """
    Log a request with structured data.
    
    Args:
        session_id: Session identifier
        model: Model name
        estimated_cost: Estimated cost before request
        decision: 'allowed' or 'blocked'
        input_tokens: Actual input tokens (if available)
        output_tokens: Actual output tokens (if available)
        actual_cost: Actual cost after request (if available)
        error: Error message (if any)
    """
    log_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "session_id": session_id,
        "model": model,
        "estimated_cost": estimated_cost,
        "decision": decision,
    }
    
    if input_tokens is not None:
        log_data["input_tokens"] = input_tokens
    
    if output_tokens is not None:
        log_data["output_tokens"] = output_tokens
    
    if actual_cost is not None:
        log_data["actual_cost"] = actual_cost
    
    if error:
        log_data["error"] = error
    
    logger = logging.getLogger("tokengate")
    logger.info(json.dumps(log_data))

