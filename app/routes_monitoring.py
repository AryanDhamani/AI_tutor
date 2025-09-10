"""
Monitoring and observability routes for AI Tutor backend.
Provides job metrics, system health, and operational insights.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
import logging

from app.services.job_store import enhanced_job_store
from app.services.render_service import render_service
from app.services.validation_service import validation_service
from app.services.logging_service import logger as structured_logger

logger = logging.getLogger(__name__)

# Create monitoring router
monitoring_router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

@monitoring_router.get("/jobs/metrics")
async def get_job_metrics() -> Dict[str, Any]:
    """
    Get comprehensive job metrics and statistics.
    
    Returns:
        Job metrics including counts, timing, and success rates
    """
    try:
        metrics = enhanced_job_store.get_metrics()
        
        return {
            "total_jobs": metrics.total_jobs,
            "jobs_by_status": metrics.jobs_by_status,
            "performance": {
                "average_render_time_seconds": metrics.average_render_time,
                "success_rate_percent": metrics.success_rate,
                "error_rate_percent": metrics.error_rate
            },
            "timestamps": {
                "last_job_created": metrics.last_job_created,
                "last_job_completed": metrics.last_job_completed
            },
            "polling_strategy": {
                "initial_interval_seconds": enhanced_job_store.get_polling_strategy().initial_interval,
                "max_interval_seconds": enhanced_job_store.get_polling_strategy().max_interval,
                "backoff_multiplier": enhanced_job_store.get_polling_strategy().backoff_multiplier,
                "max_attempts": enhanced_job_store.get_polling_strategy().max_attempts
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get job metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job metrics")

@monitoring_router.get("/jobs/queue")
async def get_job_queue() -> Dict[str, Any]:
    """
    Get current job queue status and active jobs.
    
    Returns:
        Information about queued and rendering jobs
    """
    try:
        queued_jobs = enhanced_job_store.get_jobs_by_status("queued")
        rendering_jobs = enhanced_job_store.get_jobs_by_status("rendering")
        
        # Format job info (without sensitive data)
        def format_job(job):
            return {
                "id": job.id,
                "filename": job.filename,
                "status": job.status,
                "created_at": job.created_at,
                "updated_at": job.updated_at
            }
        
        return {
            "queue": {
                "length": len(queued_jobs),
                "jobs": [format_job(job) for job in queued_jobs]
            },
            "rendering": {
                "count": len(rendering_jobs),
                "jobs": [format_job(job) for job in rendering_jobs]
            },
            "estimated_queue_time_seconds": len(queued_jobs) * 30  # Rough estimate
        }
        
    except Exception as e:
        logger.error(f"Failed to get job queue: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job queue")

@monitoring_router.get("/jobs/history")
async def get_job_history(limit: int = 50) -> Dict[str, Any]:
    """
    Get recent job completion history.
    
    Args:
        limit: Maximum number of historical jobs to return (default 50, max 200)
        
    Returns:
        Recent job completion history with performance data
    """
    try:
        # Limit to reasonable bounds
        limit = min(max(1, limit), 200)
        
        history = enhanced_job_store.get_job_history(limit)
        
        return {
            "history_count": len(history),
            "jobs": history,
            "summary": {
                "total_completed": len(history),
                "successful": len([j for j in history if j.get("status") == "ready"]),
                "failed": len([j for j in history if j.get("status") == "error"])
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get job history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job history")

@monitoring_router.get("/system/health")
async def get_system_health() -> Dict[str, Any]:
    """
    Get comprehensive system health status.
    
    Returns:
        System health including job store, rate limiting, and service status
    """
    try:
        # Job store health
        job_metrics = enhanced_job_store.get_metrics()
        active_jobs = enhanced_job_store.get_active_jobs()
        
        # Rate limiting health
        rate_limit_entries = len(validation_service._rate_limit_storage)
        
        # Overall health assessment
        is_healthy = True
        health_issues = []
        
        # Check for too many failed jobs
        if job_metrics.error_rate > 50:
            is_healthy = False
            health_issues.append(f"High error rate: {job_metrics.error_rate:.1f}%")
        
        # Check for stuck jobs (rendering for too long)
        stuck_jobs = [
            job for job in active_jobs 
            if job.status == "rendering" and 
            (datetime.utcnow() - datetime.fromisoformat(job.updated_at)).total_seconds() > 300
        ]
        
        if stuck_jobs:
            is_healthy = False
            health_issues.append(f"{len(stuck_jobs)} jobs stuck in rendering state")
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "issues": health_issues,
            "services": {
                "job_store": {
                    "status": "operational",
                    "active_jobs": len(active_jobs),
                    "total_jobs": job_metrics.total_jobs
                },
                "rate_limiting": {
                    "status": "operational", 
                    "active_limits": rate_limit_entries
                },
                "file_storage": {
                    "status": "operational"  # Could check disk space here
                }
            },
            "metrics": {
                "success_rate": job_metrics.success_rate,
                "average_render_time": job_metrics.average_render_time,
                "queue_length": len(enhanced_job_store.get_jobs_by_status("queued"))
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        return {
            "status": "error",
            "issues": [f"Health check failed: {str(e)}"],
            "services": {},
            "metrics": {}
        }

@monitoring_router.get("/jobs/{job_id}/details")
async def get_job_details(job_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Detailed job information including position and estimates
    """
    try:
        job = enhanced_job_store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Basic job info
        job_info = {
            "id": job.id,
            "status": job.status,
            "filename": job.filename,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "video_path": job.video_path,
            "error_message": job.error_message
        }
        
        # Add queue-specific info
        if job.status == "queued":
            job_info["queue_position"] = enhanced_job_store.get_queue_position(job_id)
            job_info["estimated_wait_time_seconds"] = enhanced_job_store.get_estimated_wait_time(job_id)
        
        # Add timing info for completed jobs
        if job.status in ["ready", "error"]:
            created_time = datetime.fromisoformat(job.created_at)
            updated_time = datetime.fromisoformat(job.updated_at)
            job_info["total_processing_time_seconds"] = (updated_time - created_time).total_seconds()
        
        return job_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job details: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job details")

@monitoring_router.post("/jobs/cleanup")
async def cleanup_old_jobs(max_age_hours: int = 24) -> Dict[str, Any]:
    """
    Manually trigger cleanup of old jobs.
    
    Args:
        max_age_hours: Maximum age of jobs to keep (default 24)
        
    Returns:
        Cleanup results
    """
    try:
        # Validate input
        max_age_hours = min(max(1, max_age_hours), 168)  # Between 1 hour and 1 week
        
        # Perform cleanup
        jobs_cleaned = enhanced_job_store.cleanup_old_jobs(max_age_hours)
        validation_service.clean_rate_limit_storage(max_age_hours)
        
        return {
            "cleanup_completed": True,
            "max_age_hours": max_age_hours,
            "jobs_cleaned": jobs_cleaned,
            "message": f"Cleaned up {jobs_cleaned} jobs older than {max_age_hours} hours"
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup old jobs")

@monitoring_router.get("/performance/metrics")
async def get_performance_metrics() -> Dict[str, Any]:
    """
    Get detailed performance metrics including request timing and error rates.
    
    Returns:
        Comprehensive performance metrics
    """
    try:
        # Get logging service metrics
        performance_metrics = structured_logger.get_metrics()
        
        # Get job store metrics
        job_metrics = enhanced_job_store.get_metrics()
        
        # Combine metrics
        return {
            "performance": performance_metrics,
            "jobs": {
                "total_jobs": job_metrics.total_jobs,
                "jobs_by_status": job_metrics.jobs_by_status,
                "success_rate_percent": job_metrics.success_rate,
                "error_rate_percent": job_metrics.error_rate,
                "average_render_time_seconds": job_metrics.average_render_time
            },
            "system": {
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_info": "Available via /monitoring/system/health"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")

from datetime import datetime
