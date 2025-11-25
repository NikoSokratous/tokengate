"""OpenAI endpoint handlers with budget enforcement."""
from fastapi import APIRouter, Request, Response, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import json

from src.proxy.forwarder import forwarder
from src.budget.manager import BudgetManager
from src.pricing.calculator import CostCalculator
from src.anomaly.detector import AnomalyDetector
from src.utils.validators import extract_session_id, validate_chat_completion_request, validate_embedding_request
from src.utils.logging import log_request
from src.config.settings import settings


router = APIRouter()
budget_manager = BudgetManager()
cost_calculator = CostCalculator()
anomaly_detector = AnomalyDetector()


async def process_request(
    request: Request,
    path: str,
    validate_func=None
) -> Response:
    """
    Process an OpenAI API request with budget enforcement.
    
    Args:
        request: FastAPI request object
        path: API path to forward to
        validate_func: Optional validation function for request body
        
    Returns:
        FastAPI Response
    """
    # Parse request body
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": {"message": "Invalid JSON in request body", "type": "invalid_request_error"}}
        )
    
    # Validate request structure if validator provided
    if validate_func:
        is_valid, error_msg = validate_func(body)
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={"error": {"message": error_msg, "type": "invalid_request_error"}}
            )
    
    # Extract session_id
    query_params = dict(request.query_params)
    session_id = extract_session_id(
        dict(request.headers),
        query_params,
        strict_mode=settings.strict_mode
    )
    
    if session_id is None:
        return JSONResponse(
            status_code=400,
            content={"error": {"message": "session_id is required (X-Session-ID header or session_id query param)", "type": "invalid_request_error"}}
        )
    
    # Get model
    model = body.get("model", "unknown")
    
    # Check for anomalies first
    is_anomalous, anomaly_reason = anomaly_detector.check_anomalies(
        session_id=session_id,
        model=model,
        messages=body.get("messages"),
        max_tokens=body.get("max_tokens"),
        estimated_cost=0.0  # Will update after estimation
    )
    
    if is_anomalous:
        log_request(
            session_id=session_id,
            model=model,
            estimated_cost=0.0,
            decision="blocked_anomaly",
            error=anomaly_reason
        )
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "message": f"Request blocked due to anomaly detection: {anomaly_reason}",
                    "type": "rate_limit_exceeded",
                    "anomaly_reason": anomaly_reason
                }
            }
        )
    
    # Estimate cost
    try:
        estimated_cost = cost_calculator.estimate_cost(
            model=model,
            max_tokens=body.get("max_tokens"),
            messages=body.get("messages"),
            input_tokens=None  # We don't know input tokens yet
        )
    except Exception as e:
        log_request(
            session_id=session_id,
            model=model,
            estimated_cost=0.0,
            decision="error",
            error=f"Failed to estimate cost: {str(e)}"
        )
        return JSONResponse(
            status_code=500,
            content={"error": {"message": f"Failed to estimate cost: {str(e)}", "type": "internal_error"}}
        )
    
    # Check budget
    try:
        has_budget = budget_manager.check_budget(session_id, estimated_cost)
    except Exception as e:
        log_request(
            session_id=session_id,
            model=model,
            estimated_cost=estimated_cost,
            decision="error",
            error=f"Budget check failed: {str(e)}"
        )
        return JSONResponse(
            status_code=503,
            content={"error": {"message": "Budget service unavailable", "type": "service_unavailable"}}
        )
    
    if not has_budget:
        log_request(
            session_id=session_id,
            model=model,
            estimated_cost=estimated_cost,
            decision="blocked"
        )
        budget_info = budget_manager.get_budget_info(session_id)
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "message": f"Budget exceeded. Remaining: ${budget_info['remaining']:.4f}, Required: ${estimated_cost:.4f}",
                    "type": "insufficient_quota",
                    "budget_info": budget_info
                }
            }
        )
    
    # Forward request to OpenAI
    status_code, response_body, response_headers = await forwarder.forward_request(
        method=request.method,
        path=path,
        headers=dict(request.headers),
        body=body
    )
    
    # Calculate actual cost from response
    actual_cost = 0.0
    input_tokens = None
    output_tokens = None
    
    if status_code == 200 and "usage" in response_body:
        usage = response_body["usage"]
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        try:
            actual_cost = cost_calculator.calculate_actual_cost(model, usage)
        except Exception as e:
            # Log error but don't fail the request
            log_request(
                session_id=session_id,
                model=model,
                estimated_cost=estimated_cost,
                decision="allowed",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error=f"Failed to calculate actual cost: {str(e)}"
            )
    
    # Deduct cost from budget (only if request was successful)
    if status_code == 200 and actual_cost > 0:
        try:
            budget_manager.deduct_cost(session_id, actual_cost)
        except Exception as e:
            # Log error but don't fail the request
            log_request(
                session_id=session_id,
                model=model,
                estimated_cost=estimated_cost,
                decision="allowed",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                actual_cost=actual_cost,
                error=f"Failed to deduct cost: {str(e)}"
            )
    
    # Log request
    log_request(
        session_id=session_id,
        model=model,
        estimated_cost=estimated_cost,
        decision="allowed" if status_code == 200 else "error",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        actual_cost=actual_cost if status_code == 200 else None
    )
    
    # Return response
    response = JSONResponse(
        status_code=status_code,
        content=response_body
    )
    
    # Preserve important headers
    for key, value in response_headers.items():
        key_lower = key.lower()
        if key_lower in ["content-type", "x-request-id"]:
            response.headers[key] = value
    
    return response


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Handle chat completions endpoint."""
    return await process_request(request, "/v1/chat/completions", validate_chat_completion_request)


@router.post("/v1/embeddings")
async def embeddings(request: Request):
    """Handle embeddings endpoint."""
    return await process_request(request, "/v1/embeddings", validate_embedding_request)


@router.post("/v1/completions")
async def completions(request: Request):
    """Handle legacy completions endpoint."""
    return await process_request(request, "/v1/completions")

