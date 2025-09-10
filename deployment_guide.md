# AI Tutor Backend - Deployment & Hardening Guide

Complete guide for deploying the AI Tutor backend from local development to production environments with security hardening and reliability features.

## 🏗️ Deployment Architecture

### Local Development
```
[Frontend:3000] ←→ [Backend:8000] ←→ [Gemini API]
                     ↓
                [Local Storage]
                ├── code/     (temp files)
                └── videos/   (rendered outputs)
```

### Production Architecture
```
[CDN] ←→ [Load Balancer] ←→ [Frontend App]
           ↓
      [API Gateway] ←→ [Backend Cluster]
           ↓              ↓
    [Rate Limiting]  [Object Storage]
           ↓              ↓
    [Monitoring]     [File Cleanup Jobs]
           ↓
    [Gemini API]
```

## 🚀 Process Model & Concurrency

### Development (Single Process)
```bash
# Current: Single uvicorn process
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Production (Multi-Process)

#### Option 1: Uvicorn with Workers
```bash
# Multiple worker processes
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --access-log \
  --no-reload
```

#### Option 2: Gunicorn + Uvicorn Workers
```bash
# More robust process management
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

#### Option 3: Separate Render Workers
For heavy render workloads, consider separating API and render processes:

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    ports:
      - "8000:8000"
    environment:
      - RENDER_MODE=api_only
    
  render-worker:
    build: .
    command: python app/workers/render_worker.py
    environment:
      - RENDER_MODE=worker_only
    volumes:
      - ./storage:/app/storage
```

### Process Configuration

Create `app/deployment/process_config.py`:

```python
"""
Production process configuration.
"""
import os
from typing import Dict, Any

class ProcessConfig:
    """Production process configuration."""
    
    # Worker configuration
    WORKERS = int(os.getenv("WORKERS", "4"))
    WORKER_CLASS = os.getenv("WORKER_CLASS", "uvicorn.workers.UvicornWorker")
    WORKER_CONNECTIONS = int(os.getenv("WORKER_CONNECTIONS", "1000"))
    
    # Process limits
    MAX_REQUESTS = int(os.getenv("MAX_REQUESTS", "1000"))
    MAX_REQUESTS_JITTER = int(os.getenv("MAX_REQUESTS_JITTER", "100"))
    TIMEOUT = int(os.getenv("TIMEOUT", "30"))
    KEEPALIVE = int(os.getenv("KEEPALIVE", "5"))
    
    # Resource limits
    MAX_MEMORY_MB = int(os.getenv("MAX_MEMORY_MB", "512"))
    MAX_CPU_PERCENT = int(os.getenv("MAX_CPU_PERCENT", "80"))
    
    # Render worker separation
    RENDER_MODE = os.getenv("RENDER_MODE", "combined")  # api_only, worker_only, combined
    RENDER_QUEUE_SIZE = int(os.getenv("RENDER_QUEUE_SIZE", "10"))
    
    @classmethod
    def get_gunicorn_config(cls) -> Dict[str, Any]:
        """Get gunicorn configuration."""
        return {
            "bind": f"0.0.0.0:{os.getenv('PORT', '8000')}",
            "workers": cls.WORKERS,
            "worker_class": cls.WORKER_CLASS,
            "worker_connections": cls.WORKER_CONNECTIONS,
            "max_requests": cls.MAX_REQUESTS,
            "max_requests_jitter": cls.MAX_REQUESTS_JITTER,
            "timeout": cls.TIMEOUT,
            "keepalive": cls.KEEPALIVE,
            "preload_app": True,
            "access_logfile": "-",
            "error_logfile": "-",
            "log_level": "info"
        }
```

## 💾 File Storage Strategy

### Local Development
```
backend/
├── app/
│   └── storage/
│       ├── code/     # Temporary Python files
│       └── videos/   # Rendered MP4 files
```

### Production Options

#### Option 1: Persistent Volume (Simple)
```yaml
# docker-compose.yml
services:
  backend:
    volumes:
      - storage_volume:/app/storage
      
volumes:
  storage_volume:
    driver: local
```

#### Option 2: Object Storage (Scalable)
```python
# app/services/storage_service.py
import boto3
from typing import Optional, BinaryIO

class StorageService:
    """Abstracted storage service supporting local and cloud storage."""
    
    def __init__(self):
        self.storage_type = os.getenv("STORAGE_TYPE", "local")  # local, s3, gcs
        
        if self.storage_type == "s3":
            self.s3_client = boto3.client('s3')
            self.bucket_name = os.getenv("S3_BUCKET_NAME")
        elif self.storage_type == "gcs":
            from google.cloud import storage
            self.gcs_client = storage.Client()
            self.bucket_name = os.getenv("GCS_BUCKET_NAME")
    
    async def save_video(self, filename: str, video_data: BinaryIO) -> str:
        """Save video file and return URL."""
        if self.storage_type == "local":
            # Save to local filesystem
            file_path = f"/app/storage/videos/{filename}"
            with open(file_path, "wb") as f:
                f.write(video_data.read())
            return f"/static/videos/{filename}"
        
        elif self.storage_type == "s3":
            # Upload to S3
            key = f"videos/{filename}"
            self.s3_client.upload_fileobj(video_data, self.bucket_name, key)
            return f"https://{self.bucket_name}.s3.amazonaws.com/{key}"
        
        elif self.storage_type == "gcs":
            # Upload to Google Cloud Storage
            bucket = self.gcs_client.bucket(self.bucket_name)
            blob = bucket.blob(f"videos/{filename}")
            blob.upload_from_file(video_data)
            return f"https://storage.googleapis.com/{self.bucket_name}/videos/{filename}"
    
    async def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up old files."""
        if self.storage_type == "local":
            # Local filesystem cleanup
            import glob
            import os
            import time
            
            pattern = "/app/storage/videos/*.mp4"
            current_time = time.time()
            
            for file_path in glob.glob(pattern):
                file_age = current_time - os.path.getctime(file_path)
                if file_age > max_age_hours * 3600:
                    os.remove(file_path)
        
        # Cloud storage cleanup would use API calls to list and delete old objects
```

#### Storage Security
```python
# app/services/secure_storage.py
import hashlib
import hmac
from datetime import datetime, timedelta

class SecureStorageService:
    """Secure storage with signed URLs and access control."""
    
    def __init__(self):
        self.secret_key = os.getenv("STORAGE_SECRET_KEY")
    
    def generate_signed_url(self, filename: str, expires_in_hours: int = 1) -> str:
        """Generate signed URL for temporary access."""
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        expires_timestamp = int(expires_at.timestamp())
        
        # Create signature
        message = f"{filename}:{expires_timestamp}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"/api/video/{filename}?expires={expires_timestamp}&signature={signature}"
    
    def verify_signed_url(self, filename: str, expires: str, signature: str) -> bool:
        """Verify signed URL is valid and not expired."""
        try:
            expires_timestamp = int(expires)
            if datetime.utcnow().timestamp() > expires_timestamp:
                return False  # Expired
            
            # Verify signature
            message = f"{filename}:{expires_timestamp}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except (ValueError, TypeError):
            return False
```

## 🔒 Security Hardening

### 1. CORS Configuration
```python
# app/security/cors_config.py
from fastapi.middleware.cors import CORSMiddleware

def configure_cors(app, environment: str = "production"):
    """Configure CORS based on environment."""
    
    if environment == "development":
        # Permissive for development
        allowed_origins = ["http://localhost:3000", "http://localhost:3001"]
        allow_credentials = True
    
    elif environment == "production":
        # Strict for production
        allowed_origins = [
            "https://yourdomain.com",
            "https://www.yourdomain.com",
            "https://app.yourdomain.com"
        ]
        allow_credentials = False
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "OPTIONS"],  # Only needed methods
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
        max_age=600,  # Cache preflight for 10 minutes
    )
```

### 2. Input Sanitization & Validation
```python
# app/security/input_sanitizer.py
import re
import html
from typing import str

class InputSanitizer:
    """Enhanced input sanitization for production."""
    
    # Patterns for dangerous content
    SCRIPT_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'data:text/html',
        r'vbscript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
    ]
    
    SQL_INJECTION_PATTERNS = [
        r'(\b(select|insert|update|delete|drop|create|alter|exec|execute)\b)',
        r'(\bunion\b.*\bselect\b)',
        r'(\bor\b.*=.*)',
        r'(--|\#|/\*|\*/)',
    ]
    
    @classmethod
    def sanitize_topic(cls, topic: str) -> str:
        """Sanitize topic input with enhanced security."""
        if not topic:
            raise ValueError("Topic cannot be empty")
        
        # HTML escape
        topic = html.escape(topic.strip())
        
        # Remove control characters
        topic = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', topic)
        
        # Check for script injection
        for pattern in cls.SCRIPT_PATTERNS:
            if re.search(pattern, topic, re.IGNORECASE):
                raise ValueError("Topic contains potentially unsafe content")
        
        # Check for SQL injection attempts
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, topic, re.IGNORECASE):
                raise ValueError("Topic contains invalid characters")
        
        # Length validation
        if len(topic) < 3 or len(topic) > 120:
            raise ValueError("Topic must be 3-120 characters")
        
        return topic
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename with path traversal protection."""
        if not filename:
            raise ValueError("Filename cannot be empty")
        
        # Remove any path components
        filename = os.path.basename(filename)
        
        # Remove extension if present
        filename = re.sub(r'\.[^.]*$', '', filename)
        
        # Only allow safe characters
        filename = re.sub(r'[^a-zA-Z0-9_-]', '_', filename)
        
        # Prevent reserved names
        reserved = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'}
        if filename.lower() in reserved:
            filename = f"file_{filename}"
        
        # Ensure reasonable length
        if len(filename) > 50:
            filename = filename[:50]
        
        return filename
```

### 3. Rate Limiting & DDoS Protection
```python
# app/security/advanced_rate_limiting.py
from collections import defaultdict, deque
import time
import hashlib

class AdvancedRateLimit:
    """Production-grade rate limiting with multiple strategies."""
    
    def __init__(self):
        self.ip_requests = defaultdict(deque)
        self.user_requests = defaultdict(deque)
        self.endpoint_requests = defaultdict(deque)
        self.blocked_ips = set()
        self.suspicious_ips = defaultdict(int)
    
    def check_rate_limit(self, client_ip: str, endpoint: str, user_id: str = None) -> tuple[bool, str]:
        """Advanced rate limiting with multiple checks."""
        current_time = time.time()
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            return False, "IP address is blocked"
        
        # Check for suspicious behavior
        if self.suspicious_ips[client_ip] > 10:
            self.blocked_ips.add(client_ip)
            return False, "IP address blocked due to suspicious activity"
        
        # Per-IP rate limiting
        if not self._check_ip_limit(client_ip, current_time):
            self.suspicious_ips[client_ip] += 1
            return False, "Too many requests from this IP"
        
        # Per-endpoint rate limiting
        if not self._check_endpoint_limit(endpoint, current_time):
            return False, "Endpoint rate limit exceeded"
        
        # Per-user rate limiting (if authenticated)
        if user_id and not self._check_user_limit(user_id, current_time):
            return False, "User rate limit exceeded"
        
        return True, "Request allowed"
    
    def _check_ip_limit(self, client_ip: str, current_time: float) -> bool:
        """Check per-IP rate limits."""
        requests = self.ip_requests[client_ip]
        
        # Remove old requests (1 hour window)
        while requests and requests[0] < current_time - 3600:
            requests.popleft()
        
        # Check limits: 100 requests per hour
        if len(requests) >= 100:
            return False
        
        requests.append(current_time)
        return True
```

### 4. Security Headers
```python
# app/security/security_headers.py
from fastapi import Request, Response

async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    # Content Security Policy
    csp = [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "font-src 'self'",
        "connect-src 'self'",
        "media-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'"
    ]
    response.headers["Content-Security-Policy"] = "; ".join(csp)
    
    return response
```

## 🛡️ Reliability Features

### 1. Timeouts & Circuit Breakers
```python
# app/reliability/circuit_breaker.py
import asyncio
import time
from enum import Enum
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker for external service calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time < self.recovery_timeout:
                raise Exception("Circuit breaker is OPEN")
            else:
                self.state = CircuitState.HALF_OPEN
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Usage in Gemini service
gemini_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=120)

async def call_gemini_with_circuit_breaker(prompt: str):
    """Call Gemini with circuit breaker protection."""
    return await gemini_circuit_breaker.call(
        genai.GenerativeModel('gemini-pro').generate_content_async,
        prompt
    )
```

### 2. Retry Logic with Exponential Backoff
```python
# app/reliability/retry_handler.py
import asyncio
import random
from typing import Callable, Any, Type, Tuple

class RetryHandler:
    """Retry handler with exponential backoff and jitter."""
    
    @staticmethod
    async def retry_with_backoff(
        func: Callable,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ) -> Any:
        """Retry function with exponential backoff."""
        
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return await func()
            except retry_exceptions as e:
                last_exception = e
                
                if attempt == max_attempts - 1:
                    break
                
                # Calculate delay with exponential backoff
                delay = min(base_delay * (exponential_base ** attempt), max_delay)
                
                # Add jitter to prevent thundering herd
                if jitter:
                    delay = delay * (0.5 + random.random() * 0.5)
                
                await asyncio.sleep(delay)
        
        raise last_exception

# Usage in services
async def robust_gemini_call(prompt: str):
    """Gemini call with retry logic."""
    return await RetryHandler.retry_with_backoff(
        lambda: genai.GenerativeModel('gemini-pro').generate_content_async(prompt),
        max_attempts=3,
        base_delay=2.0,
        retry_exceptions=(ConnectionError, TimeoutError, Exception)
    )
```

### 3. Resource Management & Cleanup
```python
# app/reliability/resource_manager.py
import asyncio
import psutil
import logging
from datetime import datetime, timedelta

class ResourceManager:
    """Monitor and manage system resources."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.max_memory_mb = int(os.getenv("MAX_MEMORY_MB", "512"))
        self.max_cpu_percent = int(os.getenv("MAX_CPU_PERCENT", "80"))
        self.cleanup_interval = int(os.getenv("CLEANUP_INTERVAL", "3600"))  # 1 hour
    
    async def start_monitoring(self):
        """Start resource monitoring background task."""
        while True:
            try:
                await self._check_resources()
                await self._cleanup_resources()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                self.logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute
    
    async def _check_resources(self):
        """Check system resource usage."""
        # Memory check
        memory_usage = psutil.virtual_memory()
        memory_mb = memory_usage.used / 1024 / 1024
        
        if memory_mb > self.max_memory_mb:
            self.logger.warning(f"High memory usage: {memory_mb:.1f}MB > {self.max_memory_mb}MB")
            await self._emergency_cleanup()
        
        # CPU check
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > self.max_cpu_percent:
            self.logger.warning(f"High CPU usage: {cpu_percent:.1f}% > {self.max_cpu_percent}%")
    
    async def _cleanup_resources(self):
        """Clean up system resources."""
        # Clean old files
        await self._cleanup_old_files()
        
        # Clean old job records
        await self._cleanup_old_jobs()
        
        # Clean rate limit storage
        await self._cleanup_rate_limits()
    
    async def _emergency_cleanup(self):
        """Emergency cleanup when resources are critical."""
        self.logger.warning("Performing emergency cleanup due to resource pressure")
        
        # Aggressive cleanup
        await self._cleanup_old_files(max_age_hours=1)
        await self._cleanup_old_jobs(max_age_hours=1)
        
        # Force garbage collection
        import gc
        gc.collect()
```

## 📚 Operational Documentation

### 1. Deployment Checklist
```markdown
# Production Deployment Checklist

## Pre-Deployment
- [ ] Environment variables configured
- [ ] Secrets properly managed (not in code)
- [ ] Database/storage configured
- [ ] SSL certificates installed
- [ ] Domain DNS configured
- [ ] Monitoring setup
- [ ] Backup strategy in place

## Security
- [ ] CORS properly configured for production domains
- [ ] Rate limiting enabled and tested
- [ ] Input validation and sanitization active
- [ ] Security headers configured
- [ ] File upload restrictions in place
- [ ] No debug information in production logs

## Performance
- [ ] Multiple worker processes configured
- [ ] Connection pooling enabled
- [ ] Static file serving optimized
- [ ] Caching strategy implemented
- [ ] Resource limits configured

## Monitoring
- [ ] Health checks configured
- [ ] Error tracking setup
- [ ] Performance monitoring active
- [ ] Log aggregation configured
- [ ] Alerting rules defined

## Testing
- [ ] End-to-end tests pass in staging
- [ ] Load testing completed
- [ ] Security scanning completed
- [ ] Backup/restore tested
- [ ] Rollback procedure tested
```

### 2. Known Limitations
```markdown
# Known Limitations & Considerations

## Security Limitations
- **Python Code Execution**: Manim code is executed without full sandboxing
  - Mitigation: Input validation, import restrictions, resource limits
  - Future: Consider containerized execution or WebAssembly

- **File System Access**: Temporary files stored on local filesystem
  - Mitigation: Secure file handling, regular cleanup, size limits
  - Future: Move to containerized storage

## Scalability Limitations
- **Gemini API Rate Limits**: Limited by Google's API quotas
  - Mitigation: Request queuing, user rate limiting
  - Future: Multiple API keys, request caching

- **Render Queue**: In-memory job storage doesn't persist across restarts
  - Mitigation: Fast restart, job expiration
  - Future: External queue system (Redis, RabbitMQ)

- **Concurrent Renders**: Resource-intensive operations
  - Mitigation: Job queuing, resource monitoring
  - Future: Dedicated render cluster

## Operational Limitations
- **No Authentication**: Currently open API
  - Future: Implement API keys or OAuth

- **No Request Caching**: Duplicate requests always hit Gemini API
  - Future: Intelligent caching based on topic/content

- **Limited Error Recovery**: Some failures require manual intervention
  - Future: Automated recovery procedures

## Resource Limitations
- **Memory Usage**: Manim rendering can be memory-intensive
  - Mitigation: Resource monitoring, cleanup
  - Future: Memory limits per job

- **Disk Space**: Videos accumulate over time
  - Mitigation: Automatic cleanup, file expiration
  - Future: Cloud storage with lifecycle policies

- **Network Bandwidth**: Video serving can consume bandwidth
  - Mitigation: File size limits, CDN usage
  - Future: Streaming optimization
```

### 3. Monitoring & Alerting
```python
# app/monitoring/alerts.py
class AlertManager:
    """Production alerting configuration."""
    
    ALERT_RULES = {
        "high_error_rate": {
            "condition": "error_rate > 5%",
            "window": "5 minutes",
            "severity": "warning"
        },
        "api_latency": {
            "condition": "p95_latency > 10 seconds",
            "window": "5 minutes", 
            "severity": "warning"
        },
        "render_failures": {
            "condition": "render_failure_rate > 20%",
            "window": "10 minutes",
            "severity": "critical"
        },
        "disk_space": {
            "condition": "disk_usage > 80%",
            "window": "1 minute",
            "severity": "warning"
        },
        "memory_usage": {
            "condition": "memory_usage > 80%",
            "window": "5 minutes",
            "severity": "critical"
        }
    }
```

### 4. Runbook
```markdown
# AI Tutor Backend Runbook

## Common Issues

### High Error Rate
**Symptoms**: Error rate > 5% for 5+ minutes
**Likely Cause**: Gemini API issues, validation failures
**Investigation**: 
1. Check `/monitoring/system/health`
2. Review error logs for patterns
3. Check Gemini API status
**Resolution**: 
- Restart service if needed
- Adjust rate limits
- Update validation rules

### Slow Response Times
**Symptoms**: P95 latency > 10 seconds
**Likely Cause**: Gemini API latency, resource constraints
**Investigation**:
1. Check `/monitoring/performance/metrics`
2. Monitor CPU/memory usage
3. Check render queue length
**Resolution**:
- Scale worker processes
- Implement request caching
- Optimize code generation

### Render Failures
**Symptoms**: Render failure rate > 20%
**Likely Cause**: Invalid Manim code, resource limits
**Investigation**:
1. Check render job error messages
2. Review generated code quality
3. Monitor system resources
**Resolution**:
- Improve code validation
- Adjust resource limits
- Update Manim templates

### Storage Issues
**Symptoms**: Disk usage > 80%
**Likely Cause**: Accumulating video files
**Investigation**:
1. Check storage usage
2. Review cleanup job logs
**Resolution**:
- Run manual cleanup
- Adjust retention policies
- Monitor cleanup job schedule
```

## 🎯 Deployment Commands

### Development to Staging
```bash
# Build and deploy to staging
docker build -t ai-tutor-backend:staging .
docker run -d \
  --name ai-tutor-staging \
  -p 8000:8000 \
  -e ENVIRONMENT=staging \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  -e ALLOWED_ORIGINS=https://staging.yourdomain.com \
  ai-tutor-backend:staging
```

### Production Deployment
```bash
# Production deployment with docker-compose
docker-compose -f docker-compose.prod.yml up -d

# Or with Kubernetes
kubectl apply -f k8s/
kubectl rollout status deployment/ai-tutor-backend
```

### Health Check
```bash
# Verify deployment
curl https://yourdomain.com/health
curl https://yourdomain.com/monitoring/system/health
```

This completes the deployment and hardening guide. The system is now ready for production deployment with comprehensive security, reliability, and operational considerations.


