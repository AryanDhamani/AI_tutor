#!/usr/bin/env python3
"""
Performance testing script for AI Tutor backend.
Tests response times, concurrency, and system limits.
"""

import asyncio
import aiohttp
import time
import statistics
import json
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import concurrent.futures

BASE_URL = "http://localhost:8000"

@dataclass
class PerformanceResult:
    """Performance test result."""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    max_response_time_ms: float
    min_response_time_ms: float
    requests_per_second: float
    error_rate_percent: float

class PerformanceTester:
    """Performance testing suite."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.results: List[PerformanceResult] = []
    
    def log(self, message: str):
        """Log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    async def make_async_request(self, session: aiohttp.ClientSession, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Make async HTTP request."""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                async with session.get(url) as response:
                    response_data = await response.json()
                    duration_ms = (time.time() - start_time) * 1000
                    return {
                        "success": 200 <= response.status < 300,
                        "duration_ms": duration_ms,
                        "status_code": response.status,
                        "data": response_data
                    }
            elif method.upper() == "POST":
                async with session.post(url, json=data) as response:
                    response_data = await response.json()
                    duration_ms = (time.time() - start_time) * 1000
                    return {
                        "success": 200 <= response.status < 300,
                        "duration_ms": duration_ms,
                        "status_code": response.status,
                        "data": response_data
                    }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "duration_ms": duration_ms,
                "status_code": None,
                "error": str(e)
            }
    
    def calculate_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def analyze_results(self, test_name: str, results: List[Dict], test_duration: float) -> PerformanceResult:
        """Analyze performance test results."""
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r["success"])
        failed_requests = total_requests - successful_requests
        
        # Get response times for successful requests
        response_times = [r["duration_ms"] for r in results if r["success"]]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            p95_response_time = self.calculate_percentile(response_times, 95)
            p99_response_time = self.calculate_percentile(response_times, 99)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
        else:
            avg_response_time = p95_response_time = p99_response_time = 0
            max_response_time = min_response_time = 0
        
        requests_per_second = total_requests / test_duration if test_duration > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        return PerformanceResult(
            test_name=test_name,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            max_response_time_ms=max_response_time,
            min_response_time_ms=min_response_time,
            requests_per_second=requests_per_second,
            error_rate_percent=error_rate
        )
    
    async def test_health_endpoint_load(self, concurrent_requests: int = 50, total_requests: int = 500) -> PerformanceResult:
        """Load test the health endpoint."""
        self.log(f"Load testing health endpoint: {concurrent_requests} concurrent, {total_requests} total")
        
        start_time = time.time()
        results = []
        
        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(concurrent_requests)
            
            async def make_request():
                async with semaphore:
                    return await self.make_async_request(session, "GET", "/health")
            
            # Create tasks
            tasks = [make_request() for _ in range(total_requests)]
            
            # Execute all requests
            results = await asyncio.gather(*tasks)
        
        test_duration = time.time() - start_time
        self.log(f"Completed {total_requests} requests in {test_duration:.2f}s")
        
        result = self.analyze_results("Health Endpoint Load Test", results, test_duration)
        self.results.append(result)
        return result
    
    async def test_lesson_endpoint_load(self, concurrent_requests: int = 10, total_requests: int = 50) -> PerformanceResult:
        """Load test the lesson endpoint (lighter load due to Gemini calls)."""
        self.log(f"Load testing lesson endpoint: {concurrent_requests} concurrent, {total_requests} total")
        
        start_time = time.time()
        results = []
        
        # Test data variations
        test_topics = [
            "Pythagorean theorem",
            "Quadratic equations", 
            "Newton's laws of motion",
            "Chemical bonding",
            "Photosynthesis"
        ]
        
        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(concurrent_requests)
            
            async def make_request(topic_index: int):
                async with semaphore:
                    topic = test_topics[topic_index % len(test_topics)]
                    data = {"topic": f"{topic} test {topic_index}"}
                    return await self.make_async_request(session, "POST", "/api/lesson", data)
            
            # Create tasks
            tasks = [make_request(i) for i in range(total_requests)]
            
            # Execute all requests
            results = await asyncio.gather(*tasks)
        
        test_duration = time.time() - start_time
        self.log(f"Completed {total_requests} lesson requests in {test_duration:.2f}s")
        
        result = self.analyze_results("Lesson Endpoint Load Test", results, test_duration)
        self.results.append(result)
        return result
    
    async def test_rate_limit_behavior(self) -> PerformanceResult:
        """Test rate limiting behavior."""
        self.log("Testing rate limit behavior...")
        
        start_time = time.time()
        results = []
        
        async with aiohttp.ClientSession() as session:
            # Make requests rapidly to trigger rate limiting
            for i in range(20):  # More than the 5 per 5 minutes limit
                data = {"topic": f"rate limit test {i}"}
                result = await self.make_async_request(session, "POST", "/api/lesson", data)
                results.append(result)
                
                # Small delay to avoid overwhelming
                await asyncio.sleep(0.1)
        
        test_duration = time.time() - start_time
        
        # Check if we hit rate limits (status 429)
        rate_limited_count = sum(1 for r in results if r.get("status_code") == 429)
        self.log(f"Rate limited {rate_limited_count} out of {len(results)} requests")
        
        result = self.analyze_results("Rate Limit Behavior Test", results, test_duration)
        self.results.append(result)
        return result
    
    async def test_concurrent_different_endpoints(self) -> PerformanceResult:
        """Test concurrent requests to different endpoints."""
        self.log("Testing concurrent requests to different endpoints...")
        
        start_time = time.time()
        results = []
        
        async with aiohttp.ClientSession() as session:
            # Mix of different endpoints
            tasks = []
            
            # Health checks (fast)
            for i in range(20):
                tasks.append(self.make_async_request(session, "GET", "/health"))
            
            # Monitoring endpoints (medium)
            for i in range(10):
                tasks.append(self.make_async_request(session, "GET", "/monitoring/system/health"))
                tasks.append(self.make_async_request(session, "GET", "/monitoring/jobs/metrics"))
            
            # API endpoints (slower, fewer)
            for i in range(5):
                data = {"topic": f"concurrent test {i}"}
                tasks.append(self.make_async_request(session, "POST", "/api/lesson", data))
            
            # Execute all concurrently
            results = await asyncio.gather(*tasks)
        
        test_duration = time.time() - start_time
        self.log(f"Completed {len(results)} mixed requests in {test_duration:.2f}s")
        
        result = self.analyze_results("Mixed Endpoints Concurrent Test", results, test_duration)
        self.results.append(result)
        return result
    
    async def test_sustained_load(self, duration_seconds: int = 60) -> PerformanceResult:
        """Test sustained load over time."""
        self.log(f"Running sustained load test for {duration_seconds} seconds...")
        
        start_time = time.time()
        results = []
        request_count = 0
        
        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < duration_seconds:
                # Make health check requests at steady rate
                result = await self.make_async_request(session, "GET", "/health")
                results.append(result)
                request_count += 1
                
                # Wait 1 second between requests
                await asyncio.sleep(1)
        
        test_duration = time.time() - start_time
        self.log(f"Sustained load test completed: {request_count} requests over {test_duration:.2f}s")
        
        result = self.analyze_results("Sustained Load Test", results, test_duration)
        self.results.append(result)
        return result
    
    def print_result(self, result: PerformanceResult):
        """Print detailed result."""
        print(f"\n📊 {result.test_name}")
        print("-" * 50)
        print(f"Total requests:      {result.total_requests}")
        print(f"Successful:          {result.successful_requests}")
        print(f"Failed:              {result.failed_requests}")
        print(f"Error rate:          {result.error_rate_percent:.1f}%")
        print(f"Requests/second:     {result.requests_per_second:.1f}")
        print(f"Avg response time:   {result.avg_response_time_ms:.1f}ms")
        print(f"P95 response time:   {result.p95_response_time_ms:.1f}ms")
        print(f"P99 response time:   {result.p99_response_time_ms:.1f}ms")
        print(f"Min response time:   {result.min_response_time_ms:.1f}ms")
        print(f"Max response time:   {result.max_response_time_ms:.1f}ms")
    
    def print_summary(self):
        """Print performance test summary."""
        print("\n" + "=" * 60)
        print("PERFORMANCE TEST SUMMARY")
        print("=" * 60)
        
        if not self.results:
            print("No results to display")
            return
        
        # Overall statistics
        total_requests = sum(r.total_requests for r in self.results)
        total_successful = sum(r.successful_requests for r in self.results)
        total_failed = sum(r.failed_requests for r in self.results)
        
        print(f"Total requests across all tests: {total_requests}")
        print(f"Total successful: {total_successful}")
        print(f"Total failed: {total_failed}")
        print(f"Overall success rate: {(total_successful/total_requests)*100:.1f}%")
        
        # Performance recommendations
        print(f"\n📈 PERFORMANCE ANALYSIS:")
        
        for result in self.results:
            if result.avg_response_time_ms > 5000:  # 5 seconds
                print(f"⚠️  {result.test_name}: High response times ({result.avg_response_time_ms:.1f}ms avg)")
            
            if result.error_rate_percent > 5:  # 5% error rate
                print(f"⚠️  {result.test_name}: High error rate ({result.error_rate_percent:.1f}%)")
            
            if result.requests_per_second < 1 and "lesson" not in result.test_name.lower():
                print(f"⚠️  {result.test_name}: Low throughput ({result.requests_per_second:.1f} req/s)")
        
        # Find best performing test
        health_tests = [r for r in self.results if "health" in r.test_name.lower()]
        if health_tests:
            best_health = min(health_tests, key=lambda x: x.avg_response_time_ms)
            print(f"\n🚀 Best health endpoint performance: {best_health.avg_response_time_ms:.1f}ms avg, {best_health.requests_per_second:.1f} req/s")

async def main():
    """Main performance test runner."""
    print("⚡ AI Tutor Backend Performance Test Suite")
    print("=" * 60)
    
    tester = PerformanceTester()
    
    try:
        # Quick connectivity test
        async with aiohttp.ClientSession() as session:
            result = await tester.make_async_request(session, "GET", "/health")
            if not result["success"]:
                print(f"❌ Cannot connect to server at {BASE_URL}")
                print("   Make sure the server is running: python run_server.py")
                return 1
        
        print(f"✅ Connected to server at {BASE_URL}")
        print("Starting performance tests...\n")
        
        # Run performance tests
        tests = [
            tester.test_health_endpoint_load(concurrent_requests=50, total_requests=500),
            tester.test_lesson_endpoint_load(concurrent_requests=5, total_requests=20),
            tester.test_rate_limit_behavior(),
            tester.test_concurrent_different_endpoints(),
            tester.test_sustained_load(duration_seconds=30)
        ]
        
        for test_coro in tests:
            result = await test_coro
            tester.print_result(result)
        
        # Print summary
        tester.print_summary()
        
        print(f"\n🎯 Performance testing completed!")
        print("   Review the results above for any performance issues.")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nPerformance test interrupted by user")
        return 1
    except Exception as e:
        print(f"Performance test failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))


