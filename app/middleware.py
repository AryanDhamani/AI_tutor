"""
Middleware for AI Tutor backend.
Handles rate limiting, request validation, and observability.
"""
import uuid
import logging
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime

from app.services.validation_service import validation_service
from app.services.logging_service import logger as structured_logger, request_context_manager
from app.models import ErrorResponse

logger = logging.getLogger(__name__)

async def observability_middleware(request: Request, call_next):
    """
    Middleware for request tracing and observability.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response with observability data
    """
    # Generate request ID
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    
    # Get client info
    client_ip = validation_service.get_client_ip(request)
    endpoint = request.url.path
    
    # Create request context
    context = request_context_manager.create_context(request_id, endpoint, client_ip)
    
    # Add request ID to request state
    request.state.request_id = request_id
    request.state.context = context
    
    # Log request start
    structured_logger.log_request_start(context)
    
    try:
        # Process request
        response = await call_next(request)
        
        # Log successful completion
        structured_logger.log_request_end(context, response.status_code)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    except Exception as e:
        # Log error
        context.add_error("middleware_error", str(e))
        structured_logger.log_request_end(context, 500)
        raise
    
    finally:
        # Cleanup context
        request_context_manager.remove_context(request_id)

async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware to enforce rate limiting on API endpoints.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response or rate limit error
    """
    # Only apply rate limiting to API endpoints
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    
    # Get context for logging
    context = getattr(request.state, 'context', None)
    
    # Get client IP and endpoint
    client_ip = validation_service.get_client_ip(request)
    endpoint = request.url.path
    
    # Different limits for different endpoints
    limits = {
        "/api/lesson": (5, 5),    # 5 requests per 5 minutes
        "/api/example": (5, 5),   # 5 requests per 5 minutes  
        "/api/manim": (3, 5),     # 3 requests per 5 minutes (more expensive)
        "/api/render": (2, 10),   # 2 requests per 10 minutes (very expensive)
    }
    
    # Get appropriate limit or use default
    limit, window_minutes = limits.get(endpoint, (10, 5))  # Default: 10 per 5 minutes
    
    # Check rate limit
    if not validation_service.check_rate_limit(client_ip, endpoint, limit, window_minutes):
        # Log rate limit violation
        if context:
            structured_logger.log_rate_limit(context, limit, f"{window_minutes} minutes")
        
        logger.warning(f"Rate limit exceeded: {client_ip} -> {endpoint}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=ErrorResponse(
                error="RATE_LIMIT_EXCEEDED",
                message=f"Too many requests. Limit: {limit} requests per {window_minutes} minutes",
                timestamp=datetime.utcnow().isoformat()
            ).dict()
        )
    
    # Proceed to next middleware/endpoint
    return await call_next(request)

async def validation_middleware(request: Request, call_next):
    """
    Middleware for basic request validation.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response or validation error
    """
    # Only validate API POST requests
    if not (request.url.path.startswith("/api/") and request.method == "POST"):
        return await call_next(request)
    
    # Check content type for POST requests
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content=ErrorResponse(
                error="INVALID_CONTENT_TYPE",
                message="Content-Type must be application/json",
                timestamp=datetime.utcnow().isoformat()
            ).dict()
        )
    
    # Proceed to next middleware/endpoint
    return await call_next(request)
