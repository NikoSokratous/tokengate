"""Request forwarding logic to OpenAI API."""
import httpx
from typing import Dict, Any, Optional
from src.config.settings import settings


class OpenAIForwarder:
    """Handles forwarding requests to OpenAI API."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize forwarder with OpenAI credentials."""
        self.api_key = api_key or settings.openai_api_key
        self.base_url = base_url or settings.openai_base_url.rstrip('/')
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),
                follow_redirects=True
            )
        return self._client
    
    async def forward_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Dict[str, Any]
    ) -> tuple[int, Dict[str, Any], Dict[str, str]]:
        """
        Forward request to OpenAI API.
        
        Args:
            method: HTTP method (typically POST)
            path: API path (e.g., '/v1/chat/completions')
            headers: Request headers (Authorization will be replaced)
            body: Request body as dictionary
            
        Returns:
            Tuple of (status_code, response_body, response_headers)
        """
        # Prepare URL
        url = f"{self.base_url}{path}"
        
        # Prepare headers (replace Authorization with our key)
        forward_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Preserve other headers that might be useful
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower not in ["authorization", "host", "content-length"]:
                forward_headers[key] = value
        
        try:
            # Make request
            response = await self.client.request(
                method=method,
                url=url,
                headers=forward_headers,
                json=body
            )
            
            # Parse response
            try:
                response_body = response.json()
            except Exception:
                # If not JSON, return text
                response_body = {"error": {"message": response.text}}
            
            # Extract response headers
            response_headers = dict(response.headers)
            
            return response.status_code, response_body, response_headers
            
        except httpx.TimeoutException:
            return 504, {
                "error": {
                    "message": "Request timeout while forwarding to OpenAI",
                    "type": "timeout_error"
                }
            }, {}
        except httpx.RequestError as e:
            return 502, {
                "error": {
                    "message": f"Failed to forward request to OpenAI: {str(e)}",
                    "type": "connection_error"
                }
            }, {}
        except Exception as e:
            return 500, {
                "error": {
                    "message": f"Unexpected error: {str(e)}",
                    "type": "internal_error"
                }
            }, {}
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global forwarder instance
forwarder = OpenAIForwarder()

