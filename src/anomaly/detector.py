"""Anomaly and loop detection for identifying suspicious request patterns."""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import hashlib
import json
from src.budget.redis_client import redis_client


class AnomalyDetector:
    """Detects anomalous patterns in API requests."""
    
    def __init__(self, redis_client_instance=None):
        """Initialize anomaly detector."""
        self.redis = redis_client_instance or redis_client
        
        # Configuration thresholds
        self.max_requests_per_minute = 100
        self.max_identical_requests = 3
        self.velocity_threshold = 1.0  # USD per minute
        self.freeze_duration_seconds = 300  # 5 minutes
    
    def _get_request_hash(self, model: str, messages: Any, max_tokens: Optional[int]) -> str:
        """Generate hash of request to detect identical requests."""
        request_data = {
            "model": model,
            "messages": json.dumps(messages) if messages else "",
            "max_tokens": max_tokens
        }
        data_str = json.dumps(request_data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _get_keys(self, session_id: str) -> Dict[str, str]:
        """Get Redis keys for tracking."""
        return {
            "request_count": f"anomaly:{session_id}:requests:1min",
            "request_history": f"anomaly:{session_id}:history",
            "last_request_hash": f"anomaly:{session_id}:last_hash",
            "identical_count": f"anomaly:{session_id}:identical_count",
            "spend_velocity": f"anomaly:{session_id}:velocity",
            "frozen_until": f"anomaly:{session_id}:frozen_until"
        }
    
    def is_session_frozen(self, session_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if session is frozen due to anomaly detection.
        
        Returns:
            Tuple of (is_frozen, reason)
        """
        keys = self._get_keys(session_id)
        frozen_until = self.redis.client.get(keys["frozen_until"])
        
        if frozen_until:
            frozen_time = datetime.fromisoformat(frozen_until)
            if datetime.utcnow() < frozen_time:
                reason = self.redis.client.get(f"anomaly:{session_id}:freeze_reason")
                return True, reason
            else:
                # Freeze expired, clean up
                self._unfreeze_session(session_id)
        
        return False, None
    
    def check_anomalies(
        self,
        session_id: str,
        model: str,
        messages: Any,
        max_tokens: Optional[int],
        estimated_cost: float
    ) -> tuple[bool, Optional[str]]:
        """
        Check for anomalous patterns in request.
        
        Returns:
            Tuple of (is_anomalous, reason)
        """
        keys = self._get_keys(session_id)
        
        # Check if already frozen
        is_frozen, freeze_reason = self.is_session_frozen(session_id)
        if is_frozen:
            return True, f"Session frozen: {freeze_reason}"
        
        # Check 1: Rate limiting (requests per minute)
        request_count = self.redis.client.incr(keys["request_count"])
        self.redis.client.expire(keys["request_count"], 60)
        
        if request_count > self.max_requests_per_minute:
            self._freeze_session(
                session_id,
                f"Exceeded rate limit: {request_count} requests/minute"
            )
            return True, f"Rate limit exceeded: {request_count} requests in 1 minute"
        
        # Check 2: Identical consecutive requests
        request_hash = self._get_request_hash(model, messages, max_tokens)
        last_hash = self.redis.client.get(keys["last_request_hash"])
        
        if last_hash == request_hash:
            identical_count = self.redis.client.incr(keys["identical_count"])
            self.redis.client.expire(keys["identical_count"], 300)
            
            if identical_count >= self.max_identical_requests:
                self._freeze_session(
                    session_id,
                    f"Loop detected: {identical_count} identical consecutive requests"
                )
                return True, f"Loop detected: {identical_count} identical requests"
        else:
            # Reset identical count for new request
            self.redis.client.delete(keys["identical_count"])
        
        # Update last request hash
        self.redis.client.setex(keys["last_request_hash"], 300, request_hash)
        
        # Check 3: Spending velocity (cost per minute)
        now = datetime.utcnow()
        timestamp = now.timestamp()
        
        # Add current cost to velocity tracker
        velocity_key = keys["spend_velocity"]
        self.redis.client.zadd(velocity_key, {str(timestamp): estimated_cost})
        
        # Remove entries older than 1 minute
        one_minute_ago = (now - timedelta(minutes=1)).timestamp()
        self.redis.client.zremrangebyscore(velocity_key, 0, one_minute_ago)
        
        # Calculate spending in last minute
        recent_costs = self.redis.client.zrange(velocity_key, 0, -1, withscores=True)
        total_cost_per_minute = sum(float(score) for _, score in recent_costs)
        
        if total_cost_per_minute > self.velocity_threshold:
            self._freeze_session(
                session_id,
                f"High spending velocity: ${total_cost_per_minute:.4f}/minute"
            )
            return True, f"High spending velocity: ${total_cost_per_minute:.4f}/minute"
        
        # Set expiry on velocity key
        self.redis.client.expire(velocity_key, 120)
        
        # Log request in history
        self._log_request(session_id, model, estimated_cost)
        
        return False, None
    
    def _freeze_session(self, session_id: str, reason: str):
        """Freeze a session temporarily."""
        keys = self._get_keys(session_id)
        frozen_until = datetime.utcnow() + timedelta(seconds=self.freeze_duration_seconds)
        
        self.redis.client.setex(
            keys["frozen_until"],
            self.freeze_duration_seconds,
            frozen_until.isoformat()
        )
        self.redis.client.setex(
            f"anomaly:{session_id}:freeze_reason",
            self.freeze_duration_seconds,
            reason
        )
    
    def _unfreeze_session(self, session_id: str):
        """Manually unfreeze a session."""
        keys = self._get_keys(session_id)
        self.redis.client.delete(keys["frozen_until"])
        self.redis.client.delete(f"anomaly:{session_id}:freeze_reason")
    
    def _log_request(self, session_id: str, model: str, cost: float):
        """Log request for audit trail."""
        keys = self._get_keys(session_id)
        timestamp = datetime.utcnow().isoformat()
        
        request_log = json.dumps({
            "timestamp": timestamp,
            "model": model,
            "cost": cost
        })
        
        # Keep last 100 requests
        self.redis.client.lpush(keys["request_history"], request_log)
        self.redis.client.ltrim(keys["request_history"], 0, 99)
        self.redis.client.expire(keys["request_history"], 3600)
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get anomaly detection stats for a session."""
        keys = self._get_keys(session_id)
        
        is_frozen, freeze_reason = self.is_session_frozen(session_id)
        request_count = self.redis.client.get(keys["request_count"]) or 0
        identical_count = self.redis.client.get(keys["identical_count"]) or 0
        
        # Get spending velocity
        recent_costs = self.redis.client.zrange(keys["spend_velocity"], 0, -1, withscores=True)
        velocity = sum(float(score) for _, score in recent_costs)
        
        return {
            "is_frozen": is_frozen,
            "freeze_reason": freeze_reason,
            "requests_last_minute": int(request_count),
            "identical_consecutive": int(identical_count),
            "spending_velocity_per_minute": velocity,
            "max_requests_per_minute": self.max_requests_per_minute,
            "max_identical_requests": self.max_identical_requests,
            "velocity_threshold": self.velocity_threshold
        }

