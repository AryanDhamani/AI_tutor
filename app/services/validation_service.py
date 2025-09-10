"""
Validation and safety service for AI Tutor backend.
Implements server-side validation rules and security measures.
"""
import re
import time
import logging
from typing import Dict, List, Set
from collections import defaultdict, deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ValidationService:
    """Service for validating inputs and enforcing safety rules."""
    
    # Rate limiting storage (in-memory for MVP)
    _rate_limit_storage: Dict[str, deque] = defaultdict(deque)
    
    # Dangerous imports that should be blocked in code
    DANGEROUS_IMPORTS = {
        'os', 'sys', 'subprocess', 'importlib', 'exec', 'eval',
        'open', 'file', '__import__', 'globals', 'locals',
        'compile', 'execfile', 'input', 'raw_input'
    }
    
    # Dangerous functions/keywords that should be blocked
    DANGEROUS_KEYWORDS = {
        'exec(', 'eval(', 'compile(', '__import__(',
        'globals(', 'locals(', 'vars(', 'dir(',
        'getattr(', 'setattr(', 'delattr(', 'hasattr(',
        'input(', 'raw_input('
    }
    
    @classmethod
    def validate_topic(cls, topic: str) -> str:
        """
        Validate educational topic input.
        
        Args:
            topic: User-provided topic string
            
        Returns:
            Cleaned and validated topic
            
        Raises:
            ValueError: If topic is invalid
        """
        if not topic:
            raise ValueError("Topic cannot be empty")
        
        # Strip whitespace
        topic = topic.strip()
        
        # Check length constraints
        if len(topic) < 3:
            raise ValueError("Topic must be at least 3 characters long")
        
        if len(topic) > 120:
            raise ValueError("Topic must be no more than 120 characters long")
        
        # Remove control characters
        topic = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', topic)
        
        # Check for potentially malicious content
        suspicious_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, topic, re.IGNORECASE):
                raise ValueError("Topic contains potentially unsafe content")
        
        # Ensure topic has some meaningful content
        if not re.search(r'[a-zA-Z0-9]', topic):
            raise ValueError("Topic must contain alphanumeric characters")
        
        return topic
    
    @classmethod
    def validate_filename(cls, filename: str) -> str:
        """
        Validate and sanitize filename for safe filesystem operations.
        
        Args:
            filename: User-provided filename
            
        Returns:
            Safe, sanitized filename
            
        Raises:
            ValueError: If filename is invalid
        """
        if not filename:
            raise ValueError("Filename cannot be empty")
        
        # Strip whitespace and file extensions
        filename = filename.strip()
        filename = re.sub(r'\.[^.]*$', '', filename)  # Remove extension
        
        # Check length
        if len(filename) < 1:
            raise ValueError("Filename must have content")
        
        if len(filename) > 50:
            raise ValueError("Filename must be no more than 50 characters")
        
        # Allow only safe characters: letters, numbers, underscores, hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', filename):
            raise ValueError("Filename can only contain letters, numbers, underscores, and hyphens")
        
        # Prevent reserved names
        reserved_names = {
            'con', 'prn', 'aux', 'nul',
            'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9',
            'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
        }
        
        if filename.lower() in reserved_names:
            raise ValueError(f"Filename '{filename}' is reserved and cannot be used")
        
        # Ensure doesn't start with special characters
        if filename.startswith(('-', '_')):
            filename = 'file_' + filename
        
        return filename
    
    @classmethod
    def validate_code(cls, code: str) -> str:
        """
        Validate and scan Manim code for security issues.
        
        Args:
            code: Python code to validate
            
        Returns:
            Validated code
            
        Raises:
            ValueError: If code contains unsafe content
        """
        if not code:
            raise ValueError("Code cannot be empty")
        
        code = code.strip()
        
        # Check length constraints
        if len(code) < 10:
            raise ValueError("Code is too short to be valid")
        
        if len(code) > 5000:
            raise ValueError("Code exceeds maximum length of 5000 characters")
        
        # Convert to lowercase for pattern matching
        code_lower = code.lower()
        
        # Check for dangerous imports
        import_pattern = r'(?:^|\n)\s*(?:import|from)\s+([^\s\n]+)'
        imports = re.findall(import_pattern, code_lower, re.MULTILINE)
        
        for imp in imports:
            # Clean up import name
            imp_clean = imp.split('.')[0].strip()
            if imp_clean in cls.DANGEROUS_IMPORTS:
                raise ValueError(f"Dangerous import detected: {imp}")
        
        # Check for dangerous keywords/functions
        for keyword in cls.DANGEROUS_KEYWORDS:
            if keyword in code_lower:
                raise ValueError(f"Dangerous function detected: {keyword.rstrip('(')}")
        
        # Check for file operations
        file_patterns = [
            r'open\s*\(',
            r'file\s*\(',
            r'\.write\s*\(',
            r'\.read\s*\(',
            r'\.readlines\s*\(',
        ]
        
        for pattern in file_patterns:
            if re.search(pattern, code_lower):
                raise ValueError("File operations are not allowed in animation code")
        
        # Check for network operations
        network_patterns = [
            r'urllib',
            r'requests',
            r'http',
            r'socket',
            r'urllib2',
        ]
        
        for pattern in network_patterns:
            if pattern in code_lower:
                raise ValueError("Network operations are not allowed in animation code")
        
        # Ensure it looks like Manim code
        if 'from manim import' not in code_lower and 'import manim' not in code_lower:
            raise ValueError("Code must import manim")
        
        if 'class ' not in code_lower:
            raise ValueError("Code must define a Scene class")
        
        if 'def construct' not in code_lower:
            raise ValueError("Code must have a construct method")
        
        return code
    
    @classmethod
    def check_rate_limit(cls, client_ip: str, endpoint: str, limit: int = 10, window_minutes: int = 5) -> bool:
        """
        Check if client has exceeded rate limit for an endpoint.
        
        Args:
            client_ip: Client IP address
            endpoint: API endpoint being accessed
            limit: Maximum requests allowed in time window
            window_minutes: Time window in minutes
            
        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()
        window_seconds = window_minutes * 60
        key = f"{client_ip}:{endpoint}"
        
        # Get request times for this client/endpoint
        request_times = cls._rate_limit_storage[key]
        
        # Remove old requests outside the time window
        while request_times and request_times[0] < current_time - window_seconds:
            request_times.popleft()
        
        # Check if limit exceeded
        if len(request_times) >= limit:
            logger.warning(f"Rate limit exceeded for {client_ip} on {endpoint}")
            return False
        
        # Add current request time
        request_times.append(current_time)
        
        return True
    
    @classmethod
    def validate_plan(cls, plan: str) -> str:
        """
        Validate optional lesson plan input.
        
        Args:
            plan: Optional lesson plan guidance
            
        Returns:
            Validated plan or empty string
        """
        if not plan:
            return ""
        
        plan = plan.strip()
        
        # Length constraints
        if len(plan) > 500:
            raise ValueError("Lesson plan guidance must be no more than 500 characters")
        
        # Remove control characters
        plan = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', plan)
        
        return plan
    
    @classmethod
    def get_client_ip(cls, request) -> str:
        """
        Extract client IP address from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address
        """
        # Check for forwarded headers first (for proxies/load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    @classmethod
    def clean_rate_limit_storage(cls, max_age_hours: int = 24):
        """
        Clean old entries from rate limit storage to prevent memory leaks.
        
        Args:
            max_age_hours: Maximum age of entries to keep
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        keys_to_remove = []
        
        for key, request_times in cls._rate_limit_storage.items():
            # Remove old requests
            while request_times and request_times[0] < current_time - max_age_seconds:
                request_times.popleft()
            
            # Mark empty deques for removal
            if not request_times:
                keys_to_remove.append(key)
        
        # Remove empty entries
        for key in keys_to_remove:
            del cls._rate_limit_storage[key]
        
        logger.info(f"Cleaned rate limit storage, removed {len(keys_to_remove)} old entries")

# Global validation service instance
validation_service = ValidationService()


