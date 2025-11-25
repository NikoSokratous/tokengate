"""Request validation helpers."""
from typing import Dict, Any, Optional


def extract_session_id(
    headers: Dict[str, str],
    query_params: Dict[str, Any],
    strict_mode: bool = False
) -> Optional[str]:
    """
    Extract session_id from request.
    
    Args:
        headers: Request headers
        query_params: Query parameters
        strict_mode: If True, require session_id
        
    Returns:
        Session ID or None
    """
    # Try header first (preferred)
    session_id = headers.get("X-Session-ID") or headers.get("x-session-id")
    
    # Fall back to query parameter
    if not session_id:
        session_id = query_params.get("session_id")
    
    # In strict mode, session_id is required
    if strict_mode and not session_id:
        return None
    
    # Default to "default" if not in strict mode
    return session_id or "default"


def validate_chat_completion_request(body: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate chat completion request structure.
    
    Args:
        body: Request body
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(body, dict):
        return False, "Request body must be a JSON object"
    
    if "model" not in body:
        return False, "Missing required field: model"
    
    if "messages" not in body:
        return False, "Missing required field: messages"
    
    if not isinstance(body["messages"], list):
        return False, "Field 'messages' must be an array"
    
    if len(body["messages"]) == 0:
        return False, "Field 'messages' cannot be empty"
    
    return True, None


def validate_embedding_request(body: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate embedding request structure.
    
    Args:
        body: Request body
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(body, dict):
        return False, "Request body must be a JSON object"
    
    if "model" not in body:
        return False, "Missing required field: model"
    
    if "input" not in body:
        return False, "Missing required field: input"
    
    return True, None

