"""
FastAPI main application for AI Tutor backend.
Handles CORS, health checks, and API routing.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from datetime import datetime
from pathlib import Path

from app.config import config
from app.routes import api_router
from app.routes_monitoring import monitoring_router
from app.middleware import observability_middleware, rate_limit_middleware, validation_middleware
from app.services.render_service import render_service
from app.services.validation_service import validation_service

# Validate configuration on startup
try:
    config.validate()
except ValueError as e:
    print(f"Configuration error: {e}")
    print("Please check your .env file and ensure all required variables are set.")
    exit(1)

# Create FastAPI app
app = FastAPI(
    title="AI Tutor Backend",
    description="Backend API for AI-powered educational content generation with Manim animations",
    version="1.0.0",
    docs_url="/docs" if config.DEBUG else None,  # Only show docs in debug mode
    redoc_url="/redoc" if config.DEBUG else None,
)

# Configure CORS
allowed_origins = [origin.strip() for origin in config.ALLOWED_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add custom middleware (order matters - observability first)
app.middleware("http")(observability_middleware)
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(validation_middleware)

# Include API routes
app.include_router(api_router)
app.include_router(monitoring_router)

# Setup static file serving for videos
videos_dir = Path(__file__).parent / "storage" / "videos"
videos_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/videos", StaticFiles(directory=str(videos_dir)), name="videos")

@app.get("/health")
async def health_check():
    """Health check endpoint to verify the server is running."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "service": "ai-tutor-backend"
        }
    )

@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "message": "AI Tutor Backend API",
        "version": "1.0.0",
        "docs": "/docs" if config.DEBUG else "disabled",
        "health": "/health"
    }

# Background cleanup task
import asyncio

async def cleanup_task():
    """Background task to clean up old jobs and files."""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            render_service.cleanup_old_jobs(max_age_hours=24)
            validation_service.clean_rate_limit_storage(max_age_hours=24)
        except Exception as e:
            print(f"Cleanup task error: {e}")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Print startup information and start background tasks."""
    print(f"🚀 AI Tutor Backend starting up...")
    print(f"📍 Server will run on {config.HOST}:{config.PORT}")
    print(f"🌐 CORS allowed origins: {config.ALLOWED_ORIGINS}")
    print(f"🎥 Manim quality: {config.MANIM_QUALITY}")
    print(f"⏱️  Render timeout: {config.RENDER_TIMEOUT_SEC}s")
    print(f"🔧 Debug mode: {config.DEBUG}")
    
    # Start background cleanup task
    asyncio.create_task(cleanup_task())
    print(f"🧹 Background cleanup task started")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )
