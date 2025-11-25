"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.proxy.router import router
from src.dashboard.routes import router as dashboard_router
from src.proxy.forwarder import forwarder
from src.budget.redis_client import redis_client
from src.utils.logging import setup_logging
from src.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    setup_logging()
    
    # Check Redis connection
    if not redis_client.ping():
        raise RuntimeError("Redis is not available. Please ensure Redis is running.")
    
    yield
    
    # Shutdown
    await forwarder.close()
    redis_client.close()


app = FastAPI(
    title="TokenGate",
    description="LLM Cost-Control Proxy",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)
app.include_router(dashboard_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    redis_healthy = redis_client.ping()
    
    return {
        "status": "healthy" if redis_healthy else "degraded",
        "redis": "connected" if redis_healthy else "disconnected"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

