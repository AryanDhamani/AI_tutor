"""
API routes for the AI Tutor backend.
Defines all endpoints with their request/response contracts.
"""
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
import time

from app.models import (
    LessonRequest, LessonResponse,
    ExampleRequest, ExampleResponse, 
    ManimRequest, ManimResponse,
    RenderRequest, RenderJob,
    ErrorResponse
)
from app.services.gemini_service import gemini_service
from app.services.validation_service import validation_service
from app.services.render_service import render_service
from app.services.logging_service import logger as structured_logger

# Set up logging
logger = logging.getLogger(__name__)

# Create router
api_router = APIRouter(prefix="/api", tags=["AI Tutor API"])


@api_router.post("/lesson", response_model=LessonResponse)
async def generate_lesson(request_data: LessonRequest, request: Request) -> LessonResponse:
    """
    Generate lesson explanation using Gemini AI.
    
    Args:
        request: Topic and optional lesson plan guidance
        
    Returns:
        LessonResponse with explanation containing title and bullet points
    """
    context = getattr(request.state, 'context', None)
    start_time = time.time()
    
    try:
        # Validate inputs
        try:
            validated_topic = validation_service.validate_topic(request_data.topic)
            validated_plan = validation_service.validate_plan(request_data.plan) if request_data.plan else None
        except ValueError as e:
            if context:
                structured_logger.log_validation_error(context, "topic", str(e), request_data.topic)
            raise
        
        # Set topic hash for logging
        if context:
            context.set_topic_hash(validated_topic)
        
        logger.info(f"Generating lesson for topic: {validated_topic}")
        
        # Call Gemini with timing
        gemini_start = time.time()
        explanation = await gemini_service.generate_lesson_explanation(
            topic=validated_topic,
            plan=validated_plan
        )
        gemini_duration = time.time() - gemini_start
        
        # Log Gemini call
        if context:
            structured_logger.log_gemini_call(context, "lesson", gemini_duration, True)
        
        return LessonResponse(explanation=explanation)
        
    except ValueError as e:
        logger.error(f"Lesson generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in lesson generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during lesson generation"
        )


@api_router.post("/example", response_model=ExampleResponse)
async def generate_example(request: ExampleRequest) -> ExampleResponse:
    """
    Generate worked example using Gemini AI.
    
    Args:
        request: Topic and previous explanation for context
        
    Returns:
        ExampleResponse with problem prompt, walkthrough steps, and answer
    """
    try:
        # Validate inputs
        validated_topic = validation_service.validate_topic(request.topic)
        
        logger.info(f"Generating example for topic: {validated_topic}")
        example = await gemini_service.generate_example(
            topic=validated_topic,
            explanation=request.explanation
        )
        return ExampleResponse(example=example)
        
    except ValueError as e:
        logger.error(f"Example generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in example generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during example generation"
        )


@api_router.post("/manim", response_model=ManimResponse)
async def generate_manim_code(request: ManimRequest) -> ManimResponse:
    """
    Generate Manim animation code using Gemini AI.
    
    Args:
        request: Topic and previous example for animation context
        
    Returns:
        ManimResponse with Python code, filename, and optional notes
    """
    try:
        # Validate inputs
        validated_topic = validation_service.validate_topic(request.topic)
        
        logger.info(f"Generating Manim code for topic: {validated_topic}")
        manim_data = await gemini_service.generate_manim_code(
            topic=validated_topic,
            example=request.example
        )
        return ManimResponse(manim=manim_data)
        
    except ValueError as e:
        logger.error(f"Manim code generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in Manim code generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during Manim code generation"
        )


@api_router.post("/render", response_model=RenderJob)
async def render_animation(request: RenderRequest) -> RenderJob:
    """
    Queue animation for rendering.
    
    Args:
        request: Filename and Manim code to render
        
    Returns:
        RenderJob with job ID and initial status
    """
    try:
        # Validate inputs
        validated_filename = validation_service.validate_filename(request.filename)
        validated_code = validation_service.validate_code(request.code)
        
        logger.info(f"Render request for filename: {validated_filename}")
        
        # Create render job
        render_job = render_service.create_render_job(validated_filename, validated_code)
        
        return render_job
        
    except ValueError as e:
        logger.error(f"Render validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in render request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during render request"
        )


@api_router.get("/render/{job_id}", response_model=RenderJob)
async def get_render_status(job_id: str) -> RenderJob:
    """
    Get rendering job status.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        RenderJob with current status and video URL if ready
    """
    try:
        logger.info(f"Status request for job: {job_id}")
        
        # Get job status
        job_status = render_service.get_job_status(job_id)
        
        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        return job_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error getting job status"
        )


# Topic endpoints for frontend
@api_router.get("/topics/suggestions")
async def get_topic_suggestions(limit: int = 12):
    """Get suggested learning topics."""
    suggestions = [
        "Quadratic Equations", "Linear Algebra", "Calculus Basics", 
        "Trigonometry", "Statistics", "Probability", "Geometry",
        "Derivatives", "Integrals", "Functions", "Graphing", "Vectors"
    ]
    return {"suggestions": suggestions[:limit]}

@api_router.get("/topics/categories") 
async def get_topic_categories():
    """Get topic categories."""
    categories = [
        {"name": "Algebra", "count": 25},
        {"name": "Calculus", "count": 18},
        {"name": "Geometry", "count": 15},
        {"name": "Statistics", "count": 12},
        {"name": "Trigonometry", "count": 10}
    ]
    return {"categories": categories}

# Error handlers are configured in main.py
