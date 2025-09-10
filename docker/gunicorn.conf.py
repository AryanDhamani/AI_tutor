"""
Gunicorn configuration for production deployment.
"""
import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = int(os.getenv('WORKERS', multiprocessing.cpu_count() * 2))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100

# Timeouts
timeout = 30
keepalive = 5
graceful_timeout = 30

# Process naming
proc_name = "ai-tutor-backend"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Security
limit_request_line = 8192
limit_request_fields = 100
limit_request_field_size = 8190

# Performance
preload_app = True
worker_tmp_dir = "/dev/shm"

# Hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("🚀 AI Tutor Backend starting...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("🔄 Reloading workers...")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("✅ AI Tutor Backend ready to serve requests")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info(f"💀 Worker {worker.pid} killed")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"👶 Forking worker {worker.pid}")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"🎯 Worker {worker.pid} ready")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.error(f"💥 Worker {worker.pid} aborted")

# Resource limits
tmp_upload_dir = None
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# Environment-specific settings
if os.getenv('ENVIRONMENT') == 'development':
    reload = True
    workers = 1
    loglevel = 'debug'
else:
    reload = False
    # Production optimizations
    worker_tmp_dir = "/dev/shm"  # Use tmpfs for better performance
    
# Memory and process management
def max_worker_memory_usage():
    """Maximum memory usage per worker (in MB)."""
    return int(os.getenv('MAX_WORKER_MEMORY_MB', '512'))

def worker_memory_monitor():
    """Monitor worker memory usage."""
    import psutil
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    if memory_mb > max_worker_memory_usage():
        print(f"⚠️  Worker {os.getpid()} memory usage: {memory_mb:.1f}MB")
        return True
    return False

# Custom worker class with memory monitoring
class MemoryMonitorWorker:
    def __init__(self):
        self.memory_check_interval = 100  # Check every 100 requests
        self.request_count = 0
    
    def increment_request_count(self):
        self.request_count += 1
        if self.request_count % self.memory_check_interval == 0:
            if worker_memory_monitor():
                # Could implement worker restart logic here
                pass


