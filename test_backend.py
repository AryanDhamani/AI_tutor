#!/usr/bin/env python3
"""
Comprehensive test suite for AI Tutor backend.
Tests all endpoints, error scenarios, and full pipeline integration.
"""

import requests
import json
import time
import sys
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

@dataclass
class TestResult:
    """Test result container."""
    name: str
    success: bool
    duration_ms: float
    error: Optional[str] = None
    response_data: Optional[Dict] = None
    status_code: Optional[int] = None

class BackendTester:
    """Comprehensive backend testing suite."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.results: List[TestResult] = []
        
        # Test data
        self.test_topic = "Pythagorean theorem"
        self.test_topic_invalid_short = "ab"
        self.test_topic_invalid_long = "a" * 125
        self.test_topic_malicious = "<script>alert('xss')</script>pythagorean"
        
        # Store responses for chaining tests
        self.lesson_response = None
        self.example_response = None
        self.manim_response = None
        self.render_job_id = None
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def make_request(self, method: str, endpoint: str, data: Dict = None, timeout: int = 30) -> TestResult:
        """Make HTTP request and return result."""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, timeout=timeout)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = {"text": response.text}
            
            success = 200 <= response.status_code < 300
            error = None if success else f"HTTP {response.status_code}: {response_data}"
            
            return TestResult(
                name=f"{method} {endpoint}",
                success=success,
                duration_ms=duration_ms,
                error=error,
                response_data=response_data,
                status_code=response.status_code
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                name=f"{method} {endpoint}",
                success=False,
                duration_ms=duration_ms,
                error=str(e),
                status_code=None
            )
    
    def test_health_check(self) -> TestResult:
        """Test health endpoint."""
        self.log("Testing health check endpoint...")
        result = self.make_request("GET", "/health")
        
        if result.success:
            required_fields = ["status", "timestamp", "version", "service"]
            missing_fields = [f for f in required_fields if f not in result.response_data]
            if missing_fields:
                result.success = False
                result.error = f"Missing required fields: {missing_fields}"
        
        self.results.append(result)
        return result
    
    def test_lesson_generation(self) -> TestResult:
        """Test lesson generation endpoint."""
        self.log("Testing lesson generation...")
        
        data = {
            "topic": self.test_topic,
            "plan": "Focus on practical applications and visual understanding"
        }
        
        result = self.make_request("POST", "/api/lesson", data)
        
        if result.success:
            # Validate response structure
            response = result.response_data
            if "explanation" not in response:
                result.success = False
                result.error = "Missing 'explanation' in response"
            else:
                explanation = response["explanation"]
                required_fields = ["title", "bullets"]
                missing_fields = [f for f in required_fields if f not in explanation]
                if missing_fields:
                    result.success = False
                    result.error = f"Missing fields in explanation: {missing_fields}"
                elif not isinstance(explanation["bullets"], list) or len(explanation["bullets"]) < 4:
                    result.success = False
                    result.error = f"Invalid bullets: expected list with 4+ items, got {explanation.get('bullets')}"
                else:
                    # Store for chaining
                    self.lesson_response = response
        
        self.results.append(result)
        return result
    
    def test_example_generation(self) -> TestResult:
        """Test example generation endpoint."""
        self.log("Testing example generation...")
        
        if not self.lesson_response:
            # Use fallback data
            explanation_data = {
                "title": "Pythagorean Theorem",
                "bullets": [
                    "States that in a right triangle, a² + b² = c²",
                    "c is the hypotenuse (longest side)",
                    "Used to find unknown side lengths",
                    "Fundamental principle in geometry"
                ]
            }
        else:
            explanation_data = self.lesson_response["explanation"]
        
        data = {
            "topic": self.test_topic,
            "explanation": explanation_data
        }
        
        result = self.make_request("POST", "/api/example", data)
        
        if result.success:
            # Validate response structure
            response = result.response_data
            if "example" not in response:
                result.success = False
                result.error = "Missing 'example' in response"
            else:
                example = response["example"]
                required_fields = ["prompt", "walkthrough"]
                missing_fields = [f for f in required_fields if f not in example]
                if missing_fields:
                    result.success = False
                    result.error = f"Missing fields in example: {missing_fields}"
                elif not isinstance(example["walkthrough"], list) or len(example["walkthrough"]) < 3:
                    result.success = False
                    result.error = f"Invalid walkthrough: expected list with 3+ items"
                else:
                    # Store for chaining
                    self.example_response = response
        
        self.results.append(result)
        return result
    
    def test_manim_generation(self) -> TestResult:
        """Test Manim code generation endpoint."""
        self.log("Testing Manim code generation...")
        
        if not self.example_response:
            # Use fallback data
            example_data = {
                "prompt": "Find the hypotenuse of a right triangle with legs 3 and 4",
                "walkthrough": [
                    "Identify given: a = 3, b = 4",
                    "Apply theorem: a² + b² = c²",
                    "Calculate: 9 + 16 = 25",
                    "Take square root: c = 5"
                ],
                "answer": "5 units"
            }
        else:
            example_data = self.example_response["example"]
        
        data = {
            "topic": self.test_topic,
            "example": example_data
        }
        
        result = self.make_request("POST", "/api/manim", data, timeout=60)
        
        if result.success:
            # Validate response structure
            response = result.response_data
            if "manim" not in response:
                result.success = False
                result.error = "Missing 'manim' in response"
            else:
                manim = response["manim"]
                required_fields = ["language", "filename", "code"]
                missing_fields = [f for f in required_fields if f not in manim]
                if missing_fields:
                    result.success = False
                    result.error = f"Missing fields in manim: {missing_fields}"
                elif "from manim import" not in manim["code"] and "import manim" not in manim["code"]:
                    result.success = False
                    result.error = "Generated code doesn't import manim"
                elif "class " not in manim["code"]:
                    result.success = False
                    result.error = "Generated code doesn't define a class"
                else:
                    # Store for chaining
                    self.manim_response = response
        
        self.results.append(result)
        return result
    
    def test_render_request(self) -> TestResult:
        """Test render job creation."""
        self.log("Testing render job creation...")
        
        if not self.manim_response:
            # Use simple test code
            test_code = '''from manim import *

class TestScene(Scene):
    def construct(self):
        text = Text("Test Animation")
        self.add(text)
        self.wait(1)'''
            filename = "test_scene"
        else:
            manim_data = self.manim_response["manim"]
            test_code = manim_data["code"]
            filename = manim_data["filename"]
        
        data = {
            "filename": filename,
            "code": test_code
        }
        
        result = self.make_request("POST", "/api/render", data)
        
        if result.success:
            # Validate response structure
            response = result.response_data
            required_fields = ["jobId", "status"]
            missing_fields = [f for f in required_fields if f not in response]
            if missing_fields:
                result.success = False
                result.error = f"Missing fields in render response: {missing_fields}"
            elif response["status"] != "queued":
                result.success = False
                result.error = f"Expected status 'queued', got '{response['status']}'"
            else:
                # Store job ID for polling
                self.render_job_id = response["jobId"]
        
        self.results.append(result)
        return result
    
    def test_render_status_polling(self, max_wait_seconds: int = 300) -> TestResult:
        """Test render status polling."""
        self.log("Testing render status polling...")
        
        if not self.render_job_id:
            result = TestResult(
                name="Render Status Polling",
                success=False,
                duration_ms=0,
                error="No render job ID available"
            )
            self.results.append(result)
            return result
        
        start_time = time.time()
        poll_count = 0
        
        while time.time() - start_time < max_wait_seconds:
            poll_count += 1
            self.log(f"Polling render status (attempt {poll_count})...")
            
            result = self.make_request("GET", f"/api/render/{self.render_job_id}")
            
            if not result.success:
                self.results.append(result)
                return result
            
            status = result.response_data.get("status")
            self.log(f"Render status: {status}")
            
            if status == "ready":
                video_url = result.response_data.get("videoUrl")
                if not video_url:
                    result.success = False
                    result.error = "Status is 'ready' but no videoUrl provided"
                else:
                    self.log(f"Render completed! Video URL: {video_url}")
                    result.name = "Render Status Polling (Success)"
                break
            elif status == "error":
                error_msg = result.response_data.get("error", "Unknown error")
                result.success = False
                result.error = f"Render failed: {error_msg}"
                result.name = "Render Status Polling (Error)"
                break
            elif status in ["queued", "rendering"]:
                # Continue polling
                time.sleep(3)
                continue
            else:
                result.success = False
                result.error = f"Unknown render status: {status}"
                break
        else:
            # Timeout
            result.success = False
            result.error = f"Render polling timed out after {max_wait_seconds} seconds"
            result.name = "Render Status Polling (Timeout)"
        
        result.duration_ms = (time.time() - start_time) * 1000
        self.results.append(result)
        return result
    
    def test_validation_errors(self) -> List[TestResult]:
        """Test validation error scenarios."""
        self.log("Testing validation errors...")
        
        test_cases = [
            {
                "name": "Topic too short",
                "data": {"topic": self.test_topic_invalid_short},
                "endpoint": "/api/lesson",
                "expected_status": 400
            },
            {
                "name": "Topic too long", 
                "data": {"topic": self.test_topic_invalid_long},
                "endpoint": "/api/lesson",
                "expected_status": 400
            },
            {
                "name": "Malicious topic",
                "data": {"topic": self.test_topic_malicious},
                "endpoint": "/api/lesson", 
                "expected_status": 400
            },
            {
                "name": "Invalid filename",
                "data": {"filename": "bad/filename", "code": "test"},
                "endpoint": "/api/render",
                "expected_status": 400
            },
            {
                "name": "Missing required field",
                "data": {"plan": "test"},  # Missing topic
                "endpoint": "/api/lesson",
                "expected_status": 422
            }
        ]
        
        results = []
        for case in test_cases:
            self.log(f"Testing: {case['name']}")
            result = self.make_request("POST", case["endpoint"], case["data"])
            
            # Check if we got expected error status
            if result.status_code == case["expected_status"]:
                result.success = True
                result.error = None
            else:
                result.success = False
                result.error = f"Expected status {case['expected_status']}, got {result.status_code}"
            
            result.name = f"Validation: {case['name']}"
            results.append(result)
            self.results.append(result)
        
        return results
    
    def test_rate_limiting(self) -> TestResult:
        """Test rate limiting (careful not to hit real limits)."""
        self.log("Testing rate limiting...")
        
        # Make several quick requests to lesson endpoint
        start_time = time.time()
        request_count = 6  # Should hit limit of 5 per 5 minutes
        
        for i in range(request_count):
            data = {"topic": f"test topic {i}"}
            result = self.make_request("POST", "/api/lesson", data)
            
            if result.status_code == 429:
                # Hit rate limit as expected
                duration_ms = (time.time() - start_time) * 1000
                success_result = TestResult(
                    name="Rate Limiting Test",
                    success=True,
                    duration_ms=duration_ms,
                    error=None,
                    response_data={"requests_before_limit": i + 1}
                )
                self.results.append(success_result)
                return success_result
        
        # Didn't hit rate limit
        duration_ms = (time.time() - start_time) * 1000
        result = TestResult(
            name="Rate Limiting Test",
            success=False,
            duration_ms=duration_ms,
            error=f"Expected to hit rate limit after {request_count} requests, but didn't"
        )
        self.results.append(result)
        return result
    
    def test_monitoring_endpoints(self) -> List[TestResult]:
        """Test monitoring and observability endpoints."""
        self.log("Testing monitoring endpoints...")
        
        endpoints = [
            "/monitoring/jobs/metrics",
            "/monitoring/jobs/queue", 
            "/monitoring/jobs/history",
            "/monitoring/system/health",
            "/monitoring/performance/metrics"
        ]
        
        results = []
        for endpoint in endpoints:
            self.log(f"Testing: {endpoint}")
            result = self.make_request("GET", endpoint)
            result.name = f"Monitoring: {endpoint}"
            results.append(result)
            self.results.append(result)
        
        return results
    
    def run_full_pipeline_test(self) -> bool:
        """Run complete pipeline test: lesson → example → manim → render."""
        self.log("=" * 60)
        self.log("RUNNING FULL PIPELINE TEST")
        self.log("=" * 60)
        
        pipeline_success = True
        
        # Step 1: Health check
        if not self.test_health_check().success:
            self.log("❌ Health check failed!", "ERROR")
            return False
        self.log("✅ Health check passed")
        
        # Step 2: Lesson generation
        if not self.test_lesson_generation().success:
            self.log("❌ Lesson generation failed!", "ERROR")
            pipeline_success = False
        else:
            self.log("✅ Lesson generation passed")
        
        # Step 3: Example generation
        if not self.test_example_generation().success:
            self.log("❌ Example generation failed!", "ERROR")
            pipeline_success = False
        else:
            self.log("✅ Example generation passed")
        
        # Step 4: Manim generation
        if not self.test_manim_generation().success:
            self.log("❌ Manim generation failed!", "ERROR")
            pipeline_success = False
        else:
            self.log("✅ Manim generation passed")
        
        # Step 5: Render request
        if not self.test_render_request().success:
            self.log("❌ Render request failed!", "ERROR")
            pipeline_success = False
        else:
            self.log("✅ Render request passed")
        
        # Step 6: Render polling (only if previous steps succeeded)
        if pipeline_success:
            render_result = self.test_render_status_polling()
            if not render_result.success:
                self.log("❌ Render polling failed!", "ERROR")
                pipeline_success = False
            else:
                self.log("✅ Render polling passed")
        
        return pipeline_success
    
    def run_error_scenario_tests(self) -> bool:
        """Run error scenario tests."""
        self.log("=" * 60)
        self.log("RUNNING ERROR SCENARIO TESTS")
        self.log("=" * 60)
        
        # Validation errors
        validation_results = self.test_validation_errors()
        validation_success = all(r.success for r in validation_results)
        
        if validation_success:
            self.log("✅ All validation error tests passed")
        else:
            self.log("❌ Some validation error tests failed!", "ERROR")
        
        # Rate limiting (optional - may not trigger in test environment)
        rate_limit_result = self.test_rate_limiting()
        # Don't fail overall test if rate limiting doesn't trigger
        
        return validation_success
    
    def run_monitoring_tests(self) -> bool:
        """Run monitoring endpoint tests."""
        self.log("=" * 60)
        self.log("RUNNING MONITORING TESTS")
        self.log("=" * 60)
        
        monitoring_results = self.test_monitoring_endpoints()
        monitoring_success = all(r.success for r in monitoring_results)
        
        if monitoring_success:
            self.log("✅ All monitoring endpoint tests passed")
        else:
            self.log("❌ Some monitoring endpoint tests failed!", "ERROR")
        
        return monitoring_success
    
    def print_summary(self):
        """Print test summary."""
        self.log("=" * 60)
        self.log("TEST SUMMARY")
        self.log("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        self.log(f"Total tests: {total_tests}")
        self.log(f"Passed: {passed_tests}")
        self.log(f"Failed: {failed_tests}")
        self.log(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            self.log("\nFAILED TESTS:", "ERROR")
            for result in self.results:
                if not result.success:
                    self.log(f"❌ {result.name}: {result.error}", "ERROR")
        
        # Performance summary
        if self.results:
            durations = [r.duration_ms for r in self.results if r.duration_ms > 0]
            if durations:
                avg_duration = sum(durations) / len(durations)
                max_duration = max(durations)
                self.log(f"\nPerformance:")
                self.log(f"Average response time: {avg_duration:.1f}ms")
                self.log(f"Slowest response: {max_duration:.1f}ms")

def main():
    """Main test runner."""
    print("🚀 AI Tutor Backend Test Suite")
    print("=" * 60)
    
    # Check if Gemini API key is set
    if not GEMINI_API_KEY:
        print("⚠️  WARNING: GEMINI_API_KEY not set. Some tests may fail.")
        print("   Set the environment variable or update your .env file.")
        print()
    
    # Initialize tester
    tester = BackendTester()
    
    try:
        # Test server connectivity
        tester.log("Testing server connectivity...")
        health_result = tester.make_request("GET", "/health")
        if not health_result.success:
            tester.log(f"❌ Cannot connect to server at {BASE_URL}", "ERROR")
            tester.log(f"   Make sure the server is running: python run_server.py", "ERROR")
            return 1
        
        tester.log(f"✅ Connected to server at {BASE_URL}")
        
        # Run test suites
        pipeline_success = tester.run_full_pipeline_test()
        error_success = tester.run_error_scenario_tests()
        monitoring_success = tester.run_monitoring_tests()
        
        # Print summary
        tester.print_summary()
        
        # Overall result
        overall_success = pipeline_success and error_success and monitoring_success
        
        if overall_success:
            tester.log("🎉 ALL TESTS PASSED! Backend is ready for frontend integration.")
            return 0
        else:
            tester.log("❌ SOME TESTS FAILED. Check the issues above.", "ERROR")
            return 1
            
    except KeyboardInterrupt:
        tester.log("Test interrupted by user", "ERROR")
        return 1
    except Exception as e:
        tester.log(f"Test suite failed with error: {e}", "ERROR")
        return 1

if __name__ == "__main__":
    sys.exit(main())


