from fastapi import FastAPI, Request
import time
from fastapi.middleware.cors import CORSMiddleware
from app.utils.neo4j_client import neo4j_client
from app.api import webhooks, analysis, schema
import uvicorn
from contextlib import asynccontextmanager
from app.utils.logger import request_logger


# Define the lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    print("🚀 CodeFlow Catalyst Backend Starting...")
    await neo4j_client.connect()
    print("✅ FastAPI server ready")

    yield  # The application runs while yielded

    # Code to run on shutdown
    print("👋 CodeFlow Catalyst Backend Shutting Down...")
    await neo4j_client.close()


app = FastAPI(
    title="CodeFlow Catalyst",
    description="AI-Powered Impact Analysis Platform",
    version="1.0.0",
    lifespan=lifespan  # Pass the lifespan handler to the app
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# @app.on_event("startup")
# async def startup_event():
#     """Initialize services on startup"""
#     print("🚀 CodeFlow Catalyst Backend Starting...")
#     await neo4j_client.connect()
#     print("✅ FastAPI server ready")


# @app.on_event("shutdown")
# async def shutdown_event():
#     """Cleanup on shutdown"""
#     await neo4j_client.close()
#     print("👋 CodeFlow Catalyst Backend Shutting Down...")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CodeFlow Catalyst",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # A simple check to see if the driver is initialized
        if neo4j_client.driver:
            await neo4j_client.driver.verify_connectivity()
            db_status = "connected"
        else:
            db_status = "disconnected"
    except Exception as e:
        print(f"Health check DB error: {e}")
        db_status = "error"

    return {
        "status": "ok",
        "database": db_status,
        "ai_service": "connected"  # Placeholder
    }


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all requests"""
    start_time = time.time()

    response = await call_next(request)

    duration_ms = (time.time() - start_time) * 1000

    request_logger.log_request(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms
    )

    return response

# Add monitoring endpoint


@app.get("/api/v1/monitoring/requests")
async def get_recent_requests(limit: int = 50):
    """Get recent API requests"""
    return request_logger.get_recent_requests(limit)


@app.get("/api/v1/monitoring/stats")
async def get_request_stats():
    """Get API statistics"""
    return request_logger.get_stats()

# Include API routers
app.include_router(webhooks.router, prefix="/api/v1", tags=["webhooks"])
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
app.include_router(schema.router, prefix="/api/v1", tags=["schema"])


if __name__ == "__main__":
    # uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
