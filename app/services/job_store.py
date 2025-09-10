"""
Enhanced job store with better observability, metrics, and polling optimizations.
Extends the basic job storage with production-ready features.
"""
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict

from app.models import JobStore, RenderJob

logger = logging.getLogger(__name__)

@dataclass
class JobMetrics:
    """Metrics for job monitoring and observability."""
    total_jobs: int = 0
    jobs_by_status: Dict[str, int] = None
    average_queue_time: float = 0.0
    average_render_time: float = 0.0
    success_rate: float = 0.0
    error_rate: float = 0.0
    last_job_created: Optional[str] = None
    last_job_completed: Optional[str] = None
    
    def __post_init__(self):
        if self.jobs_by_status is None:
            self.jobs_by_status = {"queued": 0, "rendering": 0, "ready": 0, "error": 0}

@dataclass
class PollingStrategy:
    """Polling strategy configuration for frontend guidance."""
    initial_interval: float = 2.0  # Start polling every 2 seconds
    max_interval: float = 10.0     # Cap at 10 seconds
    backoff_multiplier: float = 1.5 # Increase interval by 1.5x each time
    max_attempts: int = 180        # Stop after 3 minutes (180 * 2s average)
    
    def get_next_interval(self, attempt: int) -> float:
        """Calculate next polling interval with exponential backoff."""
        interval = self.initial_interval * (self.backoff_multiplier ** (attempt // 5))
        return min(interval, self.max_interval)

class EnhancedJobStore:
    """Enhanced job store with metrics, observability, and polling optimization."""
    
    def __init__(self):
        """Initialize enhanced job store."""
        self._jobs: Dict[str, JobStore] = {}
        self._job_history: List[Dict[str, Any]] = []  # Keep completed job history
        self._polling_strategy = PollingStrategy()
        
        # Metrics tracking
        self._metrics_cache: Optional[JobMetrics] = None
        self._metrics_cache_time: float = 0
        self._metrics_cache_duration: float = 30  # Cache for 30 seconds
        
        logger.info("Enhanced job store initialized")
    
    def add_job(self, job: JobStore) -> None:
        """Add job to store with metrics tracking."""
        self._jobs[job.id] = job
        self._invalidate_metrics_cache()
        
        logger.info(f"Job {job.id} added to store")
    
    def update_job(self, job_id: str, **updates) -> bool:
        """
        Update job with given fields.
        
        Args:
            job_id: Job identifier
            **updates: Fields to update
            
        Returns:
            True if job was updated, False if not found
        """
        job = self._jobs.get(job_id)
        if not job:
            return False
        
        # Track status transitions for metrics
        old_status = job.status
        
        # Update fields
        for field, value in updates.items():
            if hasattr(job, field):
                setattr(job, field, value)
        
        # Always update timestamp
        job.updated_at = datetime.utcnow().isoformat()
        
        # Log status changes
        new_status = job.status
        if old_status != new_status:
            logger.info(f"Job {job_id} status: {old_status} → {new_status}")
            
            # Archive completed jobs to history
            if new_status in ["ready", "error"]:
                self._archive_job(job)
        
        self._invalidate_metrics_cache()
        return True
    
    def get_job(self, job_id: str) -> Optional[JobStore]:
        """Get job by ID."""
        return self._jobs.get(job_id)
    
    def get_jobs_by_status(self, status: str) -> List[JobStore]:
        """Get all jobs with given status."""
        return [job for job in self._jobs.values() if job.status == status]
    
    def get_active_jobs(self) -> List[JobStore]:
        """Get all active (non-completed) jobs."""
        return [job for job in self._jobs.values() if job.status in ["queued", "rendering"]]
    
    def remove_job(self, job_id: str) -> bool:
        """Remove job from store."""
        if job_id in self._jobs:
            job = self._jobs.pop(job_id)
            logger.info(f"Job {job_id} removed from store")
            self._invalidate_metrics_cache()
            return True
        return False
    
    def _archive_job(self, job: JobStore) -> None:
        """Archive completed job to history."""
        job_data = asdict(job)
        job_data["completed_at"] = datetime.utcnow().isoformat()
        
        # Calculate processing times
        created_time = datetime.fromisoformat(job.created_at)
        completed_time = datetime.utcnow()
        job_data["total_processing_time"] = (completed_time - created_time).total_seconds()
        
        self._job_history.append(job_data)
        
        # Keep only last 1000 completed jobs
        if len(self._job_history) > 1000:
            self._job_history = self._job_history[-1000:]
    
    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Clean up old jobs.
        
        Args:
            max_age_hours: Maximum age of jobs to keep
            
        Returns:
            Number of jobs cleaned up
        """
        current_time = datetime.utcnow()
        jobs_to_remove = []
        
        for job_id, job in self._jobs.items():
            job_time = datetime.fromisoformat(job.created_at)
            age_hours = (current_time - job_time).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                jobs_to_remove.append(job_id)
        
        # Remove old jobs
        for job_id in jobs_to_remove:
            self.remove_job(job_id)
        
        # Clean up old history too
        history_cutoff = current_time - timedelta(hours=max_age_hours * 7)  # Keep history 7x longer
        self._job_history = [
            job for job in self._job_history 
            if datetime.fromisoformat(job.get("completed_at", job["created_at"])) > history_cutoff
        ]
        
        if jobs_to_remove:
            logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")
        
        self._invalidate_metrics_cache()
        return len(jobs_to_remove)
    
    def _invalidate_metrics_cache(self):
        """Invalidate metrics cache to force recalculation."""
        self._metrics_cache = None
    
    def get_metrics(self, force_refresh: bool = False) -> JobMetrics:
        """
        Get job store metrics with caching.
        
        Args:
            force_refresh: Force metrics recalculation
            
        Returns:
            Current job metrics
        """
        current_time = time.time()
        
        # Return cached metrics if still valid
        if (not force_refresh and 
            self._metrics_cache and 
            current_time - self._metrics_cache_time < self._metrics_cache_duration):
            return self._metrics_cache
        
        # Calculate fresh metrics
        metrics = self._calculate_metrics()
        
        # Cache the results
        self._metrics_cache = metrics
        self._metrics_cache_time = current_time
        
        return metrics
    
    def _calculate_metrics(self) -> JobMetrics:
        """Calculate current job store metrics."""
        total_jobs = len(self._jobs)
        jobs_by_status = defaultdict(int)
        
        # Count current jobs by status
        for job in self._jobs.values():
            jobs_by_status[job.status] += 1
        
        # Calculate timing metrics from history
        completed_jobs = [job for job in self._job_history if job.get("total_processing_time")]
        successful_jobs = [job for job in completed_jobs if job.get("status") == "ready"]
        
        average_processing_time = 0.0
        success_rate = 0.0
        error_rate = 0.0
        
        if completed_jobs:
            average_processing_time = sum(job["total_processing_time"] for job in completed_jobs) / len(completed_jobs)
            success_rate = len(successful_jobs) / len(completed_jobs) * 100
            error_rate = 100 - success_rate
        
        # Find last job timestamps
        last_job_created = None
        last_job_completed = None
        
        if self._jobs:
            last_job_created = max(job.created_at for job in self._jobs.values())
        
        if self._job_history:
            last_job_completed = max(job.get("completed_at", job["created_at"]) for job in self._job_history)
        
        return JobMetrics(
            total_jobs=total_jobs,
            jobs_by_status=dict(jobs_by_status),
            average_queue_time=0.0,  # Could calculate if we track queue start times
            average_render_time=average_processing_time,
            success_rate=success_rate,
            error_rate=error_rate,
            last_job_created=last_job_created,
            last_job_completed=last_job_completed
        )
    
    def get_polling_strategy(self) -> PollingStrategy:
        """Get recommended polling strategy for frontend."""
        return self._polling_strategy
    
    def get_job_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent job history.
        
        Args:
            limit: Maximum number of historical jobs to return
            
        Returns:
            List of completed job records
        """
        return self._job_history[-limit:]
    
    def get_queue_position(self, job_id: str) -> Optional[int]:
        """
        Get position of job in queue.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Queue position (1-based) or None if not queued
        """
        job = self.get_job(job_id)
        if not job or job.status != "queued":
            return None
        
        queued_jobs = self.get_jobs_by_status("queued")
        # Sort by creation time
        queued_jobs.sort(key=lambda j: j.created_at)
        
        try:
            position = next(i for i, j in enumerate(queued_jobs, 1) if j.id == job_id)
            return position
        except StopIteration:
            return None
    
    def get_estimated_wait_time(self, job_id: str) -> Optional[float]:
        """
        Estimate wait time for queued job based on current queue and average processing time.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Estimated wait time in seconds or None if not applicable
        """
        position = self.get_queue_position(job_id)
        if not position:
            return None
        
        metrics = self.get_metrics()
        
        # Estimate based on average render time and queue position
        if metrics.average_render_time > 0:
            estimated_wait = (position - 1) * metrics.average_render_time
            return max(0, estimated_wait)
        
        # Fallback estimate
        return (position - 1) * 30  # Assume 30 seconds per job

# Global enhanced job store instance
enhanced_job_store = EnhancedJobStore()


