"""Dashboard routes for monitoring TokenGate."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from src.budget.manager import BudgetManager
from src.anomaly.detector import AnomalyDetector
from src.budget.redis_client import redis_client

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
budget_manager = BudgetManager()
anomaly_detector = AnomalyDetector()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render the main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/api/dashboard/sessions")
async def get_sessions():
    """Get all active sessions with budget and anomaly info."""
    sessions = []
    
    try:
        # Get all session budget keys
        keys = redis_client.client.keys("session:*:budget")
        
        for key in keys:
            session_id = key.split(":")[1]
            
            # Get budget info
            budget_info = budget_manager.get_budget_info(session_id)
            
            # Get anomaly stats
            anomaly_stats = anomaly_detector.get_session_stats(session_id)
            
            sessions.append({
                "session_id": session_id,
                "budget": budget_info["budget"],
                "spent": budget_info["spent"],
                "remaining": budget_info["remaining"],
                "percentage_used": (budget_info["spent"] / budget_info["budget"] * 100) 
                    if budget_info["budget"] > 0 else 0,
                "is_frozen": anomaly_stats["is_frozen"],
                "freeze_reason": anomaly_stats["freeze_reason"],
                "requests_last_minute": anomaly_stats["requests_last_minute"]
            })
        
        return {"sessions": sessions, "total_sessions": len(sessions)}
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/api/dashboard/stats")
async def get_stats():
    """Get overall system statistics."""
    try:
        # Count total sessions
        session_keys = redis_client.client.keys("session:*:budget")
        total_sessions = len(session_keys)
        
        # Count frozen sessions
        frozen_keys = redis_client.client.keys("anomaly:*:frozen_until")
        frozen_sessions = len(frozen_keys)
        
        # Calculate total budget and spent
        total_budget = 0.0
        total_spent = 0.0
        
        for key in session_keys:
            session_id = key.split(":")[1]
            info = budget_manager.get_budget_info(session_id)
            total_budget += info["budget"]
            total_spent += info["spent"]
        
        return {
            "total_sessions": total_sessions,
            "frozen_sessions": frozen_sessions,
            "active_sessions": total_sessions - frozen_sessions,
            "total_budget": total_budget,
            "total_spent": total_spent,
            "total_remaining": total_budget - total_spent
        }
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/api/dashboard/session/{session_id}/reset")
async def reset_session(session_id: str):
    """Reset a session's budget and spending."""
    try:
        budget_manager.reset_session(session_id)
        return {"success": True, "message": f"Session {session_id} reset"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/api/dashboard/session/{session_id}/unfreeze")
async def unfreeze_session(session_id: str):
    """Unfreeze a frozen session."""
    try:
        keys = [
            f"anomaly:{session_id}:frozen_until",
            f"anomaly:{session_id}:freeze_reason"
        ]
        for key in keys:
            redis_client.client.delete(key)
        
        return {"success": True, "message": f"Session {session_id} unfrozen"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

