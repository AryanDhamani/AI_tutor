"""
Logging and observability service for AI Tutor backend.
Provides structured logging, request tracing, and performance metrics.
"""
import logging
import time
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from collections import defaultdict, deque
from functools import wraps

from app.config import config

class RequestContext:
    """Context for tracking request-specific information."""
    
    def __init__(self, request_id: str = None, endpoint: str = None, client_ip: str = None):
        self.request_id = request_id or str(uuid.uuid4())[:8]
        self.endpoint = endpoint
        self.client_ip = client_ip
        self.start_time = time.time()
        self.topic_hash = None
        self.gemini_duration = 0.0
        self.render_duration = 0.0
        self.errors = []
        self.metadata = {}
    
    def add_error(self, error_type: str, message: str, details: Dict = None):
        """Add error to request context."""
        self.errors.append({
            "type": error_type,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def set_topic_hash(self, topic: str):
        """Set topic hash for privacy-safe logging."""
        import hashlib
        self.topic_hash = hashlib.md5(topic.encode()).hexdigest()[:8]
    
    def get_duration(self) -> float:
        """Get total request duration."""
        return time.time() - self.start_time

class PerformanceMetrics:
    """Collects and aggregates performance metrics."""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.request_times = deque(maxlen=window_size)
        self.gemini_times = deque(maxlen=window_size)
        self.render_times = deque(maxlen=window_size)
        self.error_counts = defaultdict(int)
        self.endpoint_stats = defaultdict(lambda: {"count": 0, "total_time": 0.0, "errors": 0})
        self.topic_stats = defaultdict(lambda: {"count": 0, "avg_time": 0.0})
    
    def record_request(self, context: RequestContext):
        """Record request metrics."""
        duration = context.get_duration()
        self.request_times.append(duration)
        
        if context.gemini_duration > 0:
            self.gemini_times.append(context.gemini_duration)
        
        if context.render_duration > 0:
            self.render_times.append(context.render_duration)
        
        # Endpoint stats
        if context.endpoint:
            stats = self.endpoint_stats[context.endpoint]
            stats["count"] += 1
            stats["total_time"] += duration
            if context.errors:
                stats["errors"] += 1
        
        # Topic stats (using hash for privacy)
        if context.topic_hash:
            topic_stats = self.topic_stats[context.topic_hash]
            topic_stats["count"] += 1
            # Update rolling average
            old_avg = topic_stats["avg_time"]
            count = topic_stats["count"]
            topic_stats["avg_time"] = (old_avg * (count - 1) + duration) / count
        
        # Error stats
        for error in context.errors:
            self.error_counts[error["type"]] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        def safe_avg(values):
            return sum(values) / len(values) if values else 0.0
        
        def safe_percentile(values, percentile):
            if not values:
                return 0.0
            sorted_values = sorted(values)
            index = int(len(sorted_values) * percentile / 100)
            return sorted_values[min(index, len(sorted_values) - 1)]
        
        return {
            "request_metrics": {
                "total_requests": len(self.request_times),
                "avg_duration_ms": safe_avg(self.request_times) * 1000,
                "p95_duration_ms": safe_percentile(self.request_times, 95) * 1000,
                "p99_duration_ms": safe_percentile(self.request_times, 99) * 1000
            },
            "gemini_metrics": {
                "total_calls": len(self.gemini_times),
                "avg_duration_ms": safe_avg(self.gemini_times) * 1000,
                "p95_duration_ms": safe_percentile(self.gemini_times, 95) * 1000
            },
            "render_metrics": {
                "total_renders": len(self.render_times),
                "avg_duration_ms": safe_avg(self.render_times) * 1000,
                "p95_duration_ms": safe_percentile(self.render_times, 95) * 1000
            },
            "error_counts": dict(self.error_counts),
            "endpoint_stats": {
                endpoint: {
                    "count": stats["count"],
                    "avg_duration_ms": (stats["total_time"] / stats["count"] * 1000) if stats["count"] > 0 else 0,
                    "error_rate": (stats["errors"] / stats["count"] * 100) if stats["count"] > 0 else 0
                }
                for endpoint, stats in self.endpoint_stats.items()
            }
        }

class StructuredLogger:
    """Structured logger with request context and performance tracking."""
    
    def __init__(self):
        self.logger = logging.getLogger("ai_tutor")
        self.metrics = PerformanceMetrics()
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration."""
        # Create custom formatter
        class StructuredFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                
                # Add request context if available
                if hasattr(record, 'request_id'):
                    log_entry["request_id"] = record.request_id
                if hasattr(record, 'endpoint'):
                    log_entry["endpoint"] = record.endpoint
                if hasattr(record, 'client_ip'):
                    log_entry["client_ip"] = record.client_ip
                if hasattr(record, 'duration_ms'):
                    log_entry["duration_ms"] = record.duration_ms
                if hasattr(record, 'topic_hash'):
                    log_entry["topic_hash"] = record.topic_hash
                
                # Add extra fields
                if hasattr(record, 'extra'):
                    log_entry.update(record.extra)
                
                return json.dumps(log_entry, default=str)
        
        # Setup handler
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        
        # Configure logger
        self.logger.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
        self.logger.addHandler(handler)
        self.logger.propagate = False
    
    def log_request_start(self, context: RequestContext):
        """Log request start."""
        self.logger.info(
            f"Request started: {context.endpoint}",
            extra={
                "request_id": context.request_id,
                "endpoint": context.endpoint,
                "client_ip": context.client_ip,
                "event": "request_start"
            }
        )
    
    def log_request_end(self, context: RequestContext, status_code: int = 200):
        """Log request completion."""
        duration_ms = context.get_duration() * 1000
        
        # Record metrics
        self.metrics.record_request(context)
        
        # Log completion
        log_level = logging.ERROR if context.errors or status_code >= 400 else logging.INFO
        
        extra_data = {
            "request_id": context.request_id,
            "endpoint": context.endpoint,
            "client_ip": context.client_ip,
            "duration_ms": duration_ms,
            "status_code": status_code,
            "event": "request_end"
        }
        
        if context.topic_hash:
            extra_data["topic_hash"] = context.topic_hash
        
        if context.gemini_duration > 0:
            extra_data["gemini_duration_ms"] = context.gemini_duration * 1000
        
        if context.render_duration > 0:
            extra_data["render_duration_ms"] = context.render_duration * 1000
        
        if context.errors:
            extra_data["errors"] = context.errors
        
        message = f"Request completed: {context.endpoint} ({duration_ms:.1f}ms)"
        if context.errors:
            message += f" with {len(context.errors)} errors"
        
        self.logger.log(log_level, message, extra=extra_data)
    
    def log_gemini_call(self, context: RequestContext, operation: str, duration: float, success: bool = True, error: str = None):
        """Log Gemini API call."""
        context.gemini_duration += duration
        
        extra_data = {
            "request_id": context.request_id,
            "operation": operation,
            "duration_ms": duration * 1000,
            "success": success,
            "event": "gemini_call"
        }
        
        if context.topic_hash:
            extra_data["topic_hash"] = context.topic_hash
        
        if error:
            extra_data["error"] = error
            context.add_error("gemini_error", error)
        
        log_level = logging.ERROR if not success else logging.INFO
        message = f"Gemini {operation}: {'success' if success else 'failed'} ({duration * 1000:.1f}ms)"
        
        self.logger.log(log_level, message, extra=extra_data)
    
    def log_render_job(self, context: RequestContext, job_id: str, status: str, duration: float = None, error: str = None):
        """Log render job lifecycle."""
        extra_data = {
            "request_id": context.request_id,
            "job_id": job_id,
            "status": status,
            "event": "render_job"
        }
        
        if duration is not None:
            extra_data["duration_ms"] = duration * 1000
            context.render_duration = duration
        
        if error:
            extra_data["error"] = error
            context.add_error("render_error", error)
        
        log_level = logging.ERROR if status == "error" else logging.INFO
        message = f"Render job {job_id}: {status}"
        
        self.logger.log(log_level, message, extra=extra_data)
    
    def log_validation_error(self, context: RequestContext, field: str, error: str, value: str = None):
        """Log validation errors."""
        context.add_error("validation_error", error, {"field": field, "value": value})
        
        extra_data = {
            "request_id": context.request_id,
            "field": field,
            "error": error,
            "event": "validation_error"
        }
        
        if value and len(str(value)) <= 100:  # Don't log large values
            extra_data["value"] = value
        
        self.logger.warning(f"Validation error on {field}: {error}", extra=extra_data)
    
    def log_rate_limit(self, context: RequestContext, limit: int, window: str):
        """Log rate limiting events."""
        context.add_error("rate_limit", f"Exceeded {limit} requests per {window}")
        
        extra_data = {
            "request_id": context.request_id,
            "client_ip": context.client_ip,
            "endpoint": context.endpoint,
            "limit": limit,
            "window": window,
            "event": "rate_limit"
        }
        
        self.logger.warning(f"Rate limit exceeded: {context.client_ip} on {context.endpoint}", extra=extra_data)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.metrics.get_stats()

# Request context middleware helper
class RequestContextManager:
    """Manages request contexts throughout the request lifecycle."""
    
    def __init__(self):
        self._contexts = {}
    
    def create_context(self, request_id: str, endpoint: str, client_ip: str) -> RequestContext:
        """Create new request context."""
        context = RequestContext(request_id, endpoint, client_ip)
        self._contexts[request_id] = context
        return context
    
    def get_context(self, request_id: str) -> Optional[RequestContext]:
        """Get existing request context."""
        return self._contexts.get(request_id)
    
    def remove_context(self, request_id: str):
        """Remove request context."""
        self._contexts.pop(request_id, None)
    
    def cleanup_old_contexts(self, max_age_seconds: int = 3600):
        """Clean up old contexts to prevent memory leaks."""
        current_time = time.time()
        old_contexts = [
            request_id for request_id, context in self._contexts.items()
            if current_time - context.start_time > max_age_seconds
        ]
        
        for request_id in old_contexts:
            self.remove_context(request_id)
        
        if old_contexts:
            logger.info(f"Cleaned up {len(old_contexts)} old request contexts")

# Performance timing decorator
def timed_operation(operation_name: str):
    """Decorator to time operations and log performance."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"{operation_name} completed in {duration * 1000:.1f}ms")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"{operation_name} failed after {duration * 1000:.1f}ms: {e}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"{operation_name} completed in {duration * 1000:.1f}ms")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"{operation_name} failed after {duration * 1000:.1f}ms: {e}")
                raise
        
        return async_wrapper if hasattr(func, '__call__') and hasattr(func, '__await__') else sync_wrapper
    return decorator

# Global instances
logger = StructuredLogger()
request_context_manager = RequestContextManager()


