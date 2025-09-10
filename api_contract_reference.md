# API Contract Reference

Complete reference for the AI Tutor backend API. This document serves as the single source of truth for frontend-backend integration.

## 🌐 Base Configuration

### Environment Variables
```bash
# Frontend (.env.local)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Backend (.env)
ALLOWED_ORIGINS=http://localhost:3000
GEMINI_API_KEY=your_actual_api_key_here
```

### Base URL
- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

### Common Headers
All requests should include:
```http
Content-Type: application/json
```

All responses include:
```http
X-Request-ID: abc12345
```

## 📋 API Endpoints

### Health Check

#### `GET /health`
Basic health and status endpoint.

**Request:**
```http
GET /health
```

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000",
  "version": "1.0.0",
  "service": "ai-tutor-backend"
}
```

**Frontend Usage:**
```typescript
const healthCheck = async () => {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
};
```

### Content Generation Endpoints

#### `POST /api/lesson`
Generate educational lesson explanation.

**Request:**
```http
POST /api/lesson
Content-Type: application/json

{
  "topic": "Pythagorean theorem",
  "plan": "Focus on practical applications"  // optional
}
```

**Request Schema:**
```typescript
interface LessonRequest {
  topic: string;        // 3-120 characters, required
  plan?: string;        // 0-500 characters, optional
}
```

**Response (200):**
```json
{
  "explanation": {
    "title": "Pythagorean Theorem",
    "bullets": [
      "States that in a right triangle, a² + b² = c²",
      "c is the hypotenuse (longest side opposite the right angle)",
      "a and b are the two shorter sides (legs)",
      "Used to find unknown side lengths in right triangles",
      "Fundamental principle in geometry and trigonometry"
    ]
  }
}
```

**Response Schema:**
```typescript
interface LessonResponse {
  explanation: {
    title: string;
    bullets: string[];  // 4-7 items
  }
}
```

**Error Responses:**
- `400`: Invalid topic (too short, too long, malicious content)
- `429`: Rate limit exceeded (5 requests per 5 minutes)
- `500`: Server error (Gemini API failure)

#### `POST /api/example`
Generate worked example problem.

**Request:**
```http
POST /api/example
Content-Type: application/json

{
  "topic": "Pythagorean theorem",
  "explanation": {
    "title": "Pythagorean Theorem",
    "bullets": ["...", "...", "..."]
  }
}
```

**Request Schema:**
```typescript
interface ExampleRequest {
  topic: string;
  explanation: {
    title: string;
    bullets: string[];
  }
}
```

**Response (200):**
```json
{
  "example": {
    "prompt": "Find the length of the hypotenuse in a right triangle with legs of 3 and 4 units.",
    "walkthrough": [
      "Identify the given information: legs a = 3, b = 4",
      "Apply Pythagorean theorem: a² + b² = c²",
      "Substitute values: 3² + 4² = c²",
      "Calculate: 9 + 16 = c²",
      "Simplify: 25 = c²",
      "Take square root: c = √25 = 5"
    ],
    "answer": "5 units"
  }
}
```

**Response Schema:**
```typescript
interface ExampleResponse {
  example: {
    prompt: string;
    walkthrough: string[];  // 3-7 steps
    answer?: string;        // optional
  }
}
```

#### `POST /api/manim`
Generate Manim animation code.

**Request:**
```http
POST /api/manim
Content-Type: application/json

{
  "topic": "Pythagorean theorem",
  "example": {
    "prompt": "Find the hypotenuse...",
    "walkthrough": ["...", "...", "..."],
    "answer": "5 units"
  }
}
```

**Request Schema:**
```typescript
interface ManimRequest {
  topic: string;
  example: {
    prompt: string;
    walkthrough: string[];
    answer?: string;
  }
}
```

**Response (200):**
```json
{
  "manim": {
    "language": "python",
    "filename": "pythagorean_theorem",
    "code": "from manim import *\n\nclass PythagoreanTheorem(Scene):\n    def construct(self):\n        # Create right triangle\n        triangle = Polygon(\n            [0, 0, 0], [3, 0, 0], [3, 4, 0],\n            stroke_color=WHITE, fill_opacity=0.1\n        )\n        \n        # Labels for sides\n        a_label = MathTex(\"a = 3\").next_to(triangle, DOWN)\n        b_label = MathTex(\"b = 4\").next_to(triangle, RIGHT)\n        c_label = MathTex(\"c = ?\").next_to(triangle, UP + LEFT)\n        \n        self.play(Create(triangle))\n        self.play(Write(a_label), Write(b_label), Write(c_label))\n        self.wait(1)\n        \n        # Show theorem\n        theorem = MathTex(\"a^2 + b^2 = c^2\").to_edge(UP)\n        self.play(Write(theorem))\n        self.wait(2)",
    "notes": [
      "Uses simple geometric shapes",
      "Includes clear labeling",
      "Demonstrates the relationship visually"
    ]
  }
}
```

**Response Schema:**
```typescript
interface ManimResponse {
  manim: {
    language: "python";
    filename: string;
    code: string;
    notes?: string[];
  }
}
```

### Render Pipeline Endpoints

#### `POST /api/render`
Start animation rendering job.

**Request:**
```http
POST /api/render
Content-Type: application/json

{
  "filename": "pythagorean_theorem",
  "code": "from manim import *\n\nclass PythagoreanTheorem(Scene):\n..."
}
```

**Request Schema:**
```typescript
interface RenderRequest {
  filename: string;  // 1-50 chars, safe characters only [a-zA-Z0-9_-]
  code: string;      // 10-5000 chars, validated Python/Manim code
}
```

**Response (200):**
```json
{
  "jobId": "abc123def456",
  "status": "queued",
  "videoUrl": null,
  "error": null
}
```

**Response Schema:**
```typescript
interface RenderJobStart {
  jobId: string;
  status: "queued";
  videoUrl: null;
  error: null;
}
```

**Error Responses:**
- `400`: Invalid filename or dangerous code
- `429`: Rate limit exceeded (2 requests per 10 minutes)
- `500`: Server error

#### `GET /api/render/{jobId}`
Get rendering job status.

**Request:**
```http
GET /api/render/abc123def456
```

**Response (200) - Queued:**
```json
{
  "jobId": "abc123def456",
  "status": "queued",
  "videoUrl": null,
  "error": null
}
```

**Response (200) - Rendering:**
```json
{
  "jobId": "abc123def456",
  "status": "rendering",
  "videoUrl": null,
  "error": null
}
```

**Response (200) - Ready:**
```json
{
  "jobId": "abc123def456",
  "status": "ready",
  "videoUrl": "/static/videos/pythagorean_theorem_20240101_120000.mp4",
  "error": null
}
```

**Response (200) - Error:**
```json
{
  "jobId": "abc123def456",
  "status": "error",
  "videoUrl": null,
  "error": "Manim rendering failed: Invalid scene class"
}
```

**Response Schema:**
```typescript
interface RenderJob {
  jobId: string;
  status: "queued" | "rendering" | "ready" | "error";
  videoUrl?: string;    // Present when status === "ready"
  error?: string;       // Present when status === "error"
}
```

**Error Responses:**
- `404`: Job not found (may have expired)
- `500`: Server error

### Static File Serving

#### `GET /static/videos/{filename}`
Serve rendered video files.

**Request:**
```http
GET /static/videos/pythagorean_theorem_20240101_120000.mp4
```

**Response:**
- `200`: Video file (MP4 format)
- `404`: File not found

**Frontend Usage:**
```typescript
// Video URL from render job
const videoUrl = renderJob.videoUrl; // "/static/videos/..."
const fullUrl = `${API_BASE_URL}${videoUrl}`;

// Use in video element
<video controls src={fullUrl} />
```

## 📊 Monitoring Endpoints

### System Health

#### `GET /monitoring/system/health`
Comprehensive system health check.

**Response:**
```json
{
  "status": "healthy",
  "issues": [],
  "services": {
    "job_store": { "status": "operational", "active_jobs": 2 },
    "rate_limiting": { "status": "operational", "active_limits": 15 },
    "file_storage": { "status": "operational" }
  },
  "metrics": {
    "success_rate": 95.5,
    "average_render_time": 45.2,
    "queue_length": 1
  }
}
```

### Performance Metrics

#### `GET /monitoring/performance/metrics`
Detailed performance analytics.

**Response:**
```json
{
  "performance": {
    "request_metrics": {
      "total_requests": 1000,
      "avg_duration_ms": 2500.5,
      "p95_duration_ms": 4200.0,
      "p99_duration_ms": 8500.0
    },
    "gemini_metrics": {
      "total_calls": 750,
      "avg_duration_ms": 2100.3,
      "p95_duration_ms": 3800.0
    },
    "render_metrics": {
      "total_renders": 50,
      "avg_duration_ms": 45000.0,
      "p95_duration_ms": 120000.0
    },
    "endpoint_stats": {
      "/api/lesson": {
        "count": 300,
        "avg_duration_ms": 2400.0,
        "error_rate": 2.1
      }
    }
  }
}
```

## 🚨 Error Handling

### Standard Error Format

All error responses follow this format:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": [
    {
      "field": "topic",
      "message": "Topic must be between 3 and 120 characters",
      "code": "VALIDATION_ERROR"
    }
  ],
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

### Error Codes

| Code | Status | Description | Frontend Action |
|------|--------|-------------|-----------------|
| `VALIDATION_ERROR` | 400 | Invalid input data | Show field-specific error |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests | Show rate limit message with retry time |
| `GEMINI_API_ERROR` | 500 | AI service failure | Show generic error with retry option |
| `RENDER_ERROR` | 500 | Video rendering failed | Show render error with code regeneration option |
| `JOB_NOT_FOUND` | 404 | Render job expired | Handle as job completion |

### Frontend Error Handling Pattern

```typescript
const handleAPIError = (error: Response) => {
  switch (error.status) {
    case 400:
      // Validation error - show specific field errors
      showValidationErrors(error.body.details);
      break;
    case 429:
      // Rate limited - show retry guidance
      showRateLimitMessage(error.body.message);
      break;
    case 500:
      // Server error - show generic error with retry
      showServerError("Something went wrong. Please try again.");
      break;
    default:
      showGenericError("Request failed. Please check your connection.");
  }
};
```

## 🔄 Polling Strategy

### Render Status Polling

**Recommended Pattern:**
```typescript
const pollRenderStatus = async (jobId: string) => {
  const maxAttempts = 180; // 6 minutes with 2s interval
  let attempt = 0;
  
  const poll = async (): Promise<RenderJob> => {
    const response = await fetch(`${API_BASE_URL}/api/render/${jobId}`);
    
    if (response.status === 429) {
      // Rate limited - wait longer
      const retryAfter = response.headers.get('Retry-After');
      const delay = retryAfter ? parseInt(retryAfter) * 1000 : 60000;
      await sleep(delay);
      return poll();
    }
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const job = await response.json();
    
    if (job.status === 'ready' || job.status === 'error') {
      return job;
    }
    
    if (attempt++ < maxAttempts) {
      await sleep(2000); // 2 second interval
      return poll();
    }
    
    throw new Error('Polling timeout');
  };
  
  return poll();
};
```

### Polling Configuration

- **Initial Interval**: 2 seconds
- **Max Interval**: 10 seconds (for exponential backoff)
- **Max Attempts**: 180 (approximately 6 minutes)
- **Timeout**: 300 seconds absolute maximum

## 📏 Rate Limits

### Per-Endpoint Limits

| Endpoint | Limit | Window | Reason |
|----------|-------|--------|---------|
| `/api/lesson` | 5 requests | 5 minutes | Gemini API limits |
| `/api/example` | 5 requests | 5 minutes | Gemini API limits |
| `/api/manim` | 3 requests | 5 minutes | Expensive generation |
| `/api/render` | 2 requests | 10 minutes | Resource intensive |
| `/health` | No limit | - | Health checks |
| `/monitoring/*` | No limit | - | Monitoring |

### Rate Limit Response

When rate limited (HTTP 429):
```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Limit: 5 requests per 5 minutes",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

Headers may include:
```http
Retry-After: 300
```

## 🔧 Frontend Implementation Tips

### 1. API Client Configuration

```typescript
class APIClient {
  private baseURL: string;
  private timeout: number;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    this.timeout = parseInt(process.env.NEXT_PUBLIC_API_TIMEOUT || '30000');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new APIError(response.status, await this.getErrorMessage(response));
      }

      return response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }
}
```

### 2. TypeScript Types

```typescript
// Export all types for frontend use
export interface LessonRequest {
  topic: string;
  plan?: string;
}

export interface LessonResponse {
  explanation: {
    title: string;
    bullets: string[];
  }
}

export interface ExampleRequest {
  topic: string;
  explanation: {
    title: string;
    bullets: string[];
  }
}

export interface ExampleResponse {
  example: {
    prompt: string;
    walkthrough: string[];
    answer?: string;
  }
}

export interface ManimRequest {
  topic: string;
  example: {
    prompt: string;
    walkthrough: string[];
    answer?: string;
  }
}

export interface ManimResponse {
  manim: {
    language: "python";
    filename: string;
    code: string;
    notes?: string[];
  }
}

export interface RenderRequest {
  filename: string;
  code: string;
}

export interface RenderJob {
  jobId: string;
  status: "queued" | "rendering" | "ready" | "error";
  videoUrl?: string;
  error?: string;
}
```

### 3. State Management

```typescript
// Use this pattern for consistent state management
interface APIState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

const useAPIState = <T>() => {
  const [state, setState] = useState<APIState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const setLoading = () => setState(prev => ({ ...prev, loading: true, error: null }));
  const setSuccess = (data: T) => setState({ data, loading: false, error: null });
  const setError = (error: string) => setState(prev => ({ ...prev, loading: false, error }));

  return { ...state, setLoading, setSuccess, setError };
};
```

## ✅ Integration Checklist

- [ ] Environment variables configured correctly
- [ ] CORS working (no console errors)
- [ ] All API endpoints responding
- [ ] Request/response schemas match exactly
- [ ] Error handling implemented for all scenarios
- [ ] Rate limiting handled gracefully
- [ ] Polling strategy implemented correctly
- [ ] Video serving and playback working
- [ ] TypeScript types match API contracts
- [ ] Loading and error states working

This completes the API contract reference. Use this as the authoritative source for all frontend-backend integration work.

