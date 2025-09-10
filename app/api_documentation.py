"""
API Documentation and Flow Specification for AI Tutor Backend.
Documents all endpoint behaviors, request/response flows, and usage patterns.
"""

from typing import Dict, Any

# Complete API Endpoint Specifications
API_ENDPOINTS = {
    "lesson": {
        "method": "POST",
        "path": "/api/lesson",
        "purpose": "Generate educational lesson explanation using Gemini AI",
        "input": {
            "topic": "string (3-120 chars, validated)",
            "plan": "string (optional, 0-500 chars)"
        },
        "output": {
            "explanation": {
                "title": "string (clear lesson title)",
                "bullets": "array of 4-7 concise bullet points"
            }
        },
        "validation": [
            "Topic length and character validation",
            "Control character stripping",
            "Malicious content detection",
            "Plan length validation"
        ],
        "rate_limit": "5 requests per 5 minutes per IP",
        "typical_response_time": "2-5 seconds",
        "error_cases": [
            "Invalid topic (400)",
            "Rate limit exceeded (429)",
            "Gemini API failure (500)",
            "Invalid JSON format (422)"
        ]
    },
    
    "example": {
        "method": "POST", 
        "path": "/api/example",
        "purpose": "Generate worked example problem using lesson context",
        "input": {
            "topic": "string (3-120 chars, validated)",
            "explanation": {
                "title": "string",
                "bullets": "array of strings"
            }
        },
        "output": {
            "example": {
                "prompt": "string (clear problem statement)",
                "walkthrough": "array of 3-7 solution steps",
                "answer": "string (optional final answer)"
            }
        },
        "validation": [
            "Topic validation (same as lesson)",
            "Explanation structure validation"
        ],
        "rate_limit": "5 requests per 5 minutes per IP",
        "typical_response_time": "3-6 seconds",
        "dependencies": ["Requires previous lesson explanation"]
    },
    
    "manim": {
        "method": "POST",
        "path": "/api/manim", 
        "purpose": "Generate Manim animation code for educational content",
        "input": {
            "topic": "string (3-120 chars, validated)",
            "example": {
                "prompt": "string",
                "walkthrough": "array of strings", 
                "answer": "string (optional)"
            }
        },
        "output": {
            "manim": {
                "language": "python",
                "filename": "string (safe filename)",
                "code": "string (40-80 lines of Manim code)",
                "notes": "array of implementation notes (optional)"
            }
        },
        "validation": [
            "Topic validation",
            "Code safety scanning",
            "Import restrictions",
            "Manim structure validation"
        ],
        "rate_limit": "3 requests per 5 minutes per IP",
        "typical_response_time": "4-8 seconds",
        "dependencies": ["Requires previous example"]
    },
    
    "render": {
        "method": "POST",
        "path": "/api/render",
        "purpose": "Queue Manim animation for rendering",
        "input": {
            "filename": "string (1-50 chars, safe characters only)",
            "code": "string (10-5000 chars, validated Python code)"
        },
        "output": {
            "jobId": "string (unique identifier)",
            "status": "queued",
            "videoUrl": "null (not ready yet)",
            "error": "null"
        },
        "validation": [
            "Filename safety validation",
            "Code safety scanning",
            "Dangerous import detection",
            "File operation blocking"
        ],
        "rate_limit": "2 requests per 10 minutes per IP",
        "typical_response_time": "< 1 second (queuing only)",
        "dependencies": ["Requires Manim code from previous step"]
    },
    
    "render_status": {
        "method": "GET",
        "path": "/api/render/{jobId}",
        "purpose": "Check rendering job status and get video URL",
        "input": {
            "jobId": "string (path parameter)"
        },
        "output": {
            "jobId": "string",
            "status": "queued|rendering|ready|error",
            "videoUrl": "string (when status=ready)",
            "error": "string (when status=error)"
        },
        "validation": [
            "Job ID format validation"
        ],
        "rate_limit": "No specific limit (polling endpoint)",
        "typical_response_time": "< 100ms",
        "polling_strategy": "Frontend polls every 2-3 seconds until ready/error"
    }
}

# Complete Request/Response Flow
API_FLOW = {
    "sequential_generation": {
        "description": "Standard workflow for generating complete educational content",
        "steps": [
            {
                "step": 1,
                "endpoint": "/api/lesson",
                "action": "Generate lesson explanation",
                "input": {"topic": "user_topic", "plan": "optional_guidance"},
                "output": "explanation_data",
                "frontend_action": "Display in 'Explanation' tab"
            },
            {
                "step": 2, 
                "endpoint": "/api/example",
                "action": "Generate worked example",
                "input": {"topic": "user_topic", "explanation": "from_step_1"},
                "output": "example_data",
                "frontend_action": "Display in 'Example' tab",
                "dependency": "Uses explanation from step 1"
            },
            {
                "step": 3,
                "endpoint": "/api/manim", 
                "action": "Generate animation code",
                "input": {"topic": "user_topic", "example": "from_step_2"},
                "output": "manim_data",
                "frontend_action": "Display in 'Animation Code' tab",
                "dependency": "Uses example from step 2"
            },
            {
                "step": 4,
                "endpoint": "/api/render",
                "action": "Queue animation rendering", 
                "input": {"filename": "from_step_3", "code": "from_step_3"},
                "output": "render_job",
                "frontend_action": "Start polling for render status"
            },
            {
                "step": 5,
                "endpoint": "/api/render/{jobId}",
                "action": "Poll rendering status",
                "input": {"jobId": "from_step_4"},
                "output": "updated_job_status",
                "frontend_action": "Update progress, show video when ready",
                "polling": "Every 2-3 seconds until ready/error"
            }
        ]
    },
    
    "parallel_generation": {
        "description": "Optimized workflow - generate lesson, example, and manim in parallel",
        "steps": [
            {
                "step": "1a-1c",
                "endpoints": ["/api/lesson", "/api/example", "/api/manim"],
                "action": "Generate all content in parallel",
                "note": "Frontend shows partial results immediately",
                "retry_strategy": "Individual tab retry on failure"
            },
            {
                "step": 2,
                "endpoint": "/api/render", 
                "action": "Render when manim code is ready",
                "dependency": "Waits for manim generation to complete"
            }
        ]
    },
    
    "error_handling": {
        "description": "Error handling and retry strategies",
        "scenarios": [
            {
                "error": "Rate limit exceeded (429)",
                "strategy": "Show rate limit message, suggest waiting",
                "retry": "Automatic retry after rate limit window"
            },
            {
                "error": "Validation failed (400)",
                "strategy": "Show specific validation error to user",
                "retry": "User must fix input and retry"
            },
            {
                "error": "Gemini API failure (500)",
                "strategy": "Show generic error, offer retry",
                "retry": "Allow immediate retry with exponential backoff"
            },
            {
                "error": "Render failure",
                "strategy": "Show render error, offer code regeneration",
                "retry": "Regenerate manim code or manual code editing"
            }
        ]
    }
}

# Frontend Integration Specifications
FRONTEND_INTEGRATION = {
    "environment_setup": {
        "env_variable": "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000",
        "cors_origin": "http://localhost:3000",
        "api_calls": "Use fetch() or axios with proper error handling"
    },
    
    "ui_behavior": {
        "generate_button": {
            "action": "Triggers parallel API calls to /lesson, /example, /manim",
            "loading_state": "Show loading indicators per tab",
            "partial_results": "Display results as they arrive",
            "error_handling": "Show error state per tab with retry option"
        },
        
        "render_button": {
            "action": "Calls /api/render then starts polling",
            "states": ["Disabled (no code)", "Queued", "Rendering", "Ready", "Error"],
            "polling": "Every 2-3 seconds using /api/render/{jobId}",
            "video_display": "Embed video player when ready"
        },
        
        "tabs": {
            "explanation": "Shows lesson.explanation data",
            "example": "Shows example.prompt, walkthrough, answer",
            "code": "Shows manim.code with syntax highlighting",
            "video": "Shows render progress and final video"
        }
    },
    
    "error_states": {
        "network_error": "Show connection error with retry",
        "rate_limit": "Show rate limit message with countdown",
        "validation_error": "Show specific field errors",
        "server_error": "Show generic error with retry option"
    }
}

def get_endpoint_spec(endpoint_name: str) -> Dict[str, Any]:
    """Get specification for a specific endpoint."""
    return API_ENDPOINTS.get(endpoint_name, {})

def get_flow_spec(flow_name: str) -> Dict[str, Any]:
    """Get specification for a specific flow."""
    return API_FLOW.get(flow_name, {})


