"""
Testing Guide for AI Tutor Backend API.
Provides curl commands and examples for testing all endpoints.
"""

# Test data for API endpoints
TEST_DATA = {
    "valid_topic": "Pythagorean theorem",
    "invalid_topic_short": "ab",
    "invalid_topic_long": "a" * 125,
    "malicious_topic": "<script>alert('xss')</script>math",
    
    "valid_lesson_request": {
        "topic": "Pythagorean theorem",
        "plan": "Focus on practical applications and visual understanding"
    },
    
    "valid_explanation": {
        "title": "Pythagorean Theorem",
        "bullets": [
            "States that in a right triangle, a² + b² = c²",
            "c is the hypotenuse (longest side)",
            "Used to find unknown side lengths",
            "Fundamental principle in geometry"
        ]
    },
    
    "valid_example": {
        "prompt": "Find the hypotenuse of a right triangle with legs 3 and 4",
        "walkthrough": [
            "Identify given: a = 3, b = 4",
            "Apply theorem: a² + b² = c²",
            "Calculate: 9 + 16 = 25",
            "Take square root: c = 5"
        ],
        "answer": "5 units"
    },
    
    "valid_filename": "pythagorean_demo",
    "invalid_filename": "file/with/slashes",
    "dangerous_code": "import os; os.system('rm -rf /')",
}

# cURL test commands
CURL_TESTS = {
    "health_check": """
# Test health endpoint
curl -X GET http://localhost:8000/health
""",
    
    "lesson_generation": """
# Test lesson generation
curl -X POST http://localhost:8000/api/lesson \\
  -H "Content-Type: application/json" \\
  -d '{
    "topic": "Pythagorean theorem",
    "plan": "Focus on practical applications"
  }'
""",
    
    "example_generation": """
# Test example generation (requires explanation from lesson)
curl -X POST http://localhost:8000/api/example \\
  -H "Content-Type: application/json" \\
  -d '{
    "topic": "Pythagorean theorem",
    "explanation": {
      "title": "Pythagorean Theorem",
      "bullets": [
        "States that in a right triangle, a² + b² = c²",
        "c is the hypotenuse (longest side)",
        "Used to find unknown side lengths"
      ]
    }
  }'
""",
    
    "manim_generation": """
# Test Manim code generation (requires example)
curl -X POST http://localhost:8000/api/manim \\
  -H "Content-Type: application/json" \\
  -d '{
    "topic": "Pythagorean theorem", 
    "example": {
      "prompt": "Find hypotenuse with legs 3 and 4",
      "walkthrough": ["Given: a=3, b=4", "Apply: a²+b²=c²", "Result: c=5"],
      "answer": "5 units"
    }
  }'
""",
    
    "render_request": """
# Test render request (placeholder - not yet implemented)
curl -X POST http://localhost:8000/api/render \\
  -H "Content-Type: application/json" \\
  -d '{
    "filename": "pythagorean_demo",
    "code": "from manim import *\\n\\nclass Demo(Scene):\\n    def construct(self):\\n        text = Text(\\"Demo\\")\\n        self.add(text)"
  }'
""",
    
    "validation_tests": """
# Test validation errors

# Topic too short
curl -X POST http://localhost:8000/api/lesson \\
  -H "Content-Type: application/json" \\
  -d '{"topic": "ab"}'

# Topic too long  
curl -X POST http://localhost:8000/api/lesson \\
  -H "Content-Type: application/json" \\
  -d '{"topic": "' + 'a' * 125 + '"}'

# Malicious content
curl -X POST http://localhost:8000/api/lesson \\
  -H "Content-Type: application/json" \\
  -d '{"topic": "<script>alert(\\"xss\\")</script>"}'

# Invalid filename
curl -X POST http://localhost:8000/api/render \\
  -H "Content-Type: application/json" \\
  -d '{
    "filename": "bad/filename",
    "code": "valid manim code here"
  }'
""",
    
    "rate_limit_test": """
# Test rate limiting (run multiple times quickly)
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/lesson \\
    -H "Content-Type: application/json" \\
    -d '{"topic": "test topic '$i'"}' &
done
wait
"""
}

# Test scenarios and expected responses
TEST_SCENARIOS = {
    "happy_path": {
        "description": "Complete workflow from topic to rendered video",
        "steps": [
            "POST /api/lesson with valid topic",
            "POST /api/example with lesson result",
            "POST /api/manim with example result", 
            "POST /api/render with manim result",
            "GET /api/render/{jobId} until ready"
        ],
        "expected_flow": "All requests succeed, video renders successfully"
    },
    
    "validation_errors": {
        "description": "Test all validation rules",
        "tests": [
            "Topic too short -> 400 error",
            "Topic too long -> 400 error",
            "Malicious topic -> 400 error",
            "Invalid filename -> 400 error",
            "Dangerous code -> 400 error",
            "Missing required fields -> 422 error"
        ]
    },
    
    "rate_limiting": {
        "description": "Test rate limit enforcement",
        "test": "Make 6+ requests to /api/lesson quickly",
        "expected": "First 5 succeed, 6th returns 429 Too Many Requests"
    },
    
    "error_handling": {
        "description": "Test error responses and recovery",
        "scenarios": [
            "Invalid JSON -> 422 Unprocessable Entity",
            "Missing Content-Type -> 415 Unsupported Media Type",
            "Gemini API failure -> 500 Internal Server Error",
            "Network timeout -> 504 Gateway Timeout"
        ]
    }
}

def generate_test_script():
    """Generate a bash script for comprehensive API testing."""
    return """#!/bin/bash

# AI Tutor Backend API Test Script
# Run this script to test all endpoints

echo "Testing AI Tutor Backend API..."
echo "Base URL: http://localhost:8000"
echo

# Test 1: Health check
echo "1. Testing health endpoint..."
curl -s http://localhost:8000/health | jq .
echo

# Test 2: Lesson generation
echo "2. Testing lesson generation..."
LESSON_RESPONSE=$(curl -s -X POST http://localhost:8000/api/lesson \\
  -H "Content-Type: application/json" \\
  -d '{"topic": "Pythagorean theorem"}')
echo $LESSON_RESPONSE | jq .
echo

# Test 3: Example generation (using lesson result)
echo "3. Testing example generation..."
EXAMPLE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/example \\
  -H "Content-Type: application/json" \\
  -d "{
    \\"topic\\": \\"Pythagorean theorem\\",
    \\"explanation\\": $(echo $LESSON_RESPONSE | jq .explanation)
  }")
echo $EXAMPLE_RESPONSE | jq .
echo

# Test 4: Validation error
echo "4. Testing validation (topic too short)..."
curl -s -X POST http://localhost:8000/api/lesson \\
  -H "Content-Type: application/json" \\
  -d '{"topic": "ab"}' | jq .
echo

# Test 5: Rate limiting (make multiple requests)
echo "5. Testing rate limiting..."
for i in {1..6}; do
  echo "Request $i:"
  curl -s -X POST http://localhost:8000/api/lesson \\
    -H "Content-Type: application/json" \\
    -d "{\\"topic\\": \\"test $i\\"}" | jq '.error // "Success"'
done

echo "Test script completed!"
"""

# Save test script
def save_test_script():
    with open("test_api.sh", "w") as f:
        f.write(generate_test_script())
    print("Test script saved as test_api.sh")
    print("Run with: chmod +x test_api.sh && ./test_api.sh")


