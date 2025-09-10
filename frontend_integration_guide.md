# Frontend Integration Guide

Complete guide for integrating the AI Tutor frontend with the backend API. This ensures zero UI changes when swapping from mocks to the real API.

## 🔧 Environment Configuration

### Frontend Environment Setup

In your `ai-tutor-mvp/.env.local` file:

```bash
# Backend API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Optional: API timeout settings
NEXT_PUBLIC_API_TIMEOUT=30000

# Optional: Polling configuration
NEXT_PUBLIC_POLLING_INTERVAL=2000
NEXT_PUBLIC_MAX_POLLING_ATTEMPTS=180
```

### Backend Environment Setup

Ensure your backend `.env` file has:

```bash
# CORS Configuration - CRITICAL for frontend access
ALLOWED_ORIGINS=http://localhost:3000

# Other settings
GEMINI_API_KEY=your_actual_api_key_here
MANIM_QUALITY=L
RENDER_TIMEOUT_SEC=180
DEBUG=true
LOG_LEVEL=INFO
```

## 🔄 API Mapping - 1:1 Correspondence

### Generate Button Flow (Parallel Calls)

The frontend "Generate" button should trigger **3 parallel API calls**:

#### 1. Lesson Generation
```typescript
// Frontend Call
const lessonResponse = await fetch(`${API_BASE_URL}/api/lesson`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    topic: userTopic,
    plan: optionalGuidance  // Can be null/undefined
  })
});

// Expected Response Schema
interface LessonResponse {
  explanation: {
    title: string;
    bullets: string[];  // 4-7 items
  }
}
```

#### 2. Example Generation
```typescript
// Frontend Call
const exampleResponse = await fetch(`${API_BASE_URL}/api/example`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    topic: userTopic,
    explanation: lessonResponse.explanation  // From step 1
  })
});

// Expected Response Schema
interface ExampleResponse {
  example: {
    prompt: string;
    walkthrough: string[];  // 3-7 steps
    answer?: string;        // Optional
  }
}
```

#### 3. Manim Code Generation
```typescript
// Frontend Call
const manimResponse = await fetch(`${API_BASE_URL}/api/manim`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    topic: userTopic,
    example: exampleResponse.example  // From step 2
  })
});

// Expected Response Schema
interface ManimResponse {
  manim: {
    language: "python";
    filename: string;
    code: string;
    notes?: string[];  // Optional implementation notes
  }
}
```

### Render Animation Flow

#### 1. Start Render Job
```typescript
// Frontend Call
const renderResponse = await fetch(`${API_BASE_URL}/api/render`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    filename: manimResponse.manim.filename,
    code: manimResponse.manim.code
  })
});

// Expected Response Schema
interface RenderJobStart {
  jobId: string;
  status: "queued";
  videoUrl: null;
  error: null;
}
```

#### 2. Poll Render Status
```typescript
// Frontend Polling Loop
const pollRenderStatus = async (jobId: string) => {
  const response = await fetch(`${API_BASE_URL}/api/render/${jobId}`);
  const status = await response.json();
  
  return status;  // See RenderJob schema below
};

// Expected Response Schema
interface RenderJob {
  jobId: string;
  status: "queued" | "rendering" | "ready" | "error";
  videoUrl?: string;    // Present when status === "ready"
  error?: string;       // Present when status === "error"
}
```

## 🎯 Frontend Implementation Patterns

### 1. API Client Setup

```typescript
// api/client.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

class APIClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new APIError(
        response.status, 
        await this.getErrorMessage(response)
      );
    }

    return response.json();
  }

  private async getErrorMessage(response: Response): Promise<string> {
    try {
      const error = await response.json();
      return error.message || `HTTP ${response.status}`;
    } catch {
      return `HTTP ${response.status}`;
    }
  }

  // API Methods
  async generateLesson(topic: string, plan?: string): Promise<LessonResponse> {
    return this.request('/api/lesson', {
      method: 'POST',
      body: JSON.stringify({ topic, plan }),
    });
  }

  async generateExample(topic: string, explanation: ExplanationData): Promise<ExampleResponse> {
    return this.request('/api/example', {
      method: 'POST',
      body: JSON.stringify({ topic, explanation }),
    });
  }

  async generateManim(topic: string, example: ExampleData): Promise<ManimResponse> {
    return this.request('/api/manim', {
      method: 'POST',
      body: JSON.stringify({ topic, example }),
    });
  }

  async startRender(filename: string, code: string): Promise<RenderJobStart> {
    return this.request('/api/render', {
      method: 'POST',
      body: JSON.stringify({ filename, code }),
    });
  }

  async getRenderStatus(jobId: string): Promise<RenderJob> {
    return this.request(`/api/render/${jobId}`);
  }
}

export const apiClient = new APIClient();
```

### 2. Error Handling

```typescript
// types/errors.ts
export class APIError extends Error {
  constructor(
    public status: number,
    public message: string,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }

  get isValidationError() {
    return this.status === 400;
  }

  get isRateLimited() {
    return this.status === 429;
  }

  get isServerError() {
    return this.status >= 500;
  }
}

// Error handling in components
const handleAPIError = (error: APIError, setError: (msg: string) => void) => {
  if (error.isValidationError) {
    setError(`Invalid input: ${error.message}`);
  } else if (error.isRateLimited) {
    setError('Too many requests. Please wait a moment and try again.');
  } else if (error.isServerError) {
    setError('Server error. Please try again later.');
  } else {
    setError(`Request failed: ${error.message}`);
  }
};
```

### 3. Tab State Management

```typescript
// hooks/useTabResults.ts
interface TabResults {
  explanation: ExplanationData | null;
  example: ExampleData | null;
  manim: ManimData | null;
  renderJob: RenderJob | null;
}

interface TabStates {
  explanation: 'idle' | 'loading' | 'success' | 'error';
  example: 'idle' | 'loading' | 'success' | 'error';
  manim: 'idle' | 'loading' | 'success' | 'error';
  render: 'idle' | 'loading' | 'success' | 'error';
}

export const useTabResults = () => {
  const [results, setResults] = useState<TabResults>({
    explanation: null,
    example: null,
    manim: null,
    renderJob: null,
  });

  const [states, setStates] = useState<TabStates>({
    explanation: 'idle',
    example: 'idle',
    manim: 'idle',
    render: 'idle',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  // Generate all content in parallel
  const generateContent = async (topic: string, plan?: string) => {
    // Reset states
    setStates({
      explanation: 'loading',
      example: 'loading',
      manim: 'loading',
      render: 'idle',
    });
    setErrors({});

    try {
      // Start all three requests in parallel
      const [lessonResult, exampleResult, manimResult] = await Promise.allSettled([
        apiClient.generateLesson(topic, plan),
        // Note: For true parallel execution, you'd need to pass mock data
        // or handle dependencies differently. This is sequential for data dependency.
        apiClient.generateLesson(topic, plan).then(lesson => 
          apiClient.generateExample(topic, lesson.explanation)
        ),
        apiClient.generateLesson(topic, plan)
          .then(lesson => apiClient.generateExample(topic, lesson.explanation))
          .then(example => apiClient.generateManim(topic, example.example))
      ]);

      // Handle lesson result
      if (lessonResult.status === 'fulfilled') {
        setResults(prev => ({ ...prev, explanation: lessonResult.value.explanation }));
        setStates(prev => ({ ...prev, explanation: 'success' }));
      } else {
        setStates(prev => ({ ...prev, explanation: 'error' }));
        setErrors(prev => ({ ...prev, explanation: lessonResult.reason.message }));
      }

      // Handle example result
      if (exampleResult.status === 'fulfilled') {
        setResults(prev => ({ ...prev, example: exampleResult.value.example }));
        setStates(prev => ({ ...prev, example: 'success' }));
      } else {
        setStates(prev => ({ ...prev, example: 'error' }));
        setErrors(prev => ({ ...prev, example: exampleResult.reason.message }));
      }

      // Handle manim result
      if (manimResult.status === 'fulfilled') {
        setResults(prev => ({ ...prev, manim: manimResult.value.manim }));
        setStates(prev => ({ ...prev, manim: 'success' }));
      } else {
        setStates(prev => ({ ...prev, manim: 'error' }));
        setErrors(prev => ({ ...prev, manim: manimResult.reason.message }));
      }

    } catch (error) {
      console.error('Content generation failed:', error);
    }
  };

  return {
    results,
    states,
    errors,
    generateContent,
    setResults,
    setStates,
    setErrors,
  };
};
```

### 4. Render Polling Hook

```typescript
// hooks/useRenderPolling.ts
export const useRenderPolling = () => {
  const [renderJob, setRenderJob] = useState<RenderJob | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startRender = async (filename: string, code: string) => {
    try {
      setError(null);
      const job = await apiClient.startRender(filename, code);
      setRenderJob(job);
      
      // Start polling
      startPolling(job.jobId);
    } catch (err) {
      setError(err instanceof APIError ? err.message : 'Render failed to start');
    }
  };

  const startPolling = (jobId: string) => {
    setIsPolling(true);
    
    const poll = async () => {
      try {
        const status = await apiClient.getRenderStatus(jobId);
        setRenderJob(status);

        if (status.status === 'ready' || status.status === 'error') {
          setIsPolling(false);
          if (status.status === 'error') {
            setError(status.error || 'Rendering failed');
          }
          return;
        }

        // Continue polling
        setTimeout(poll, 2000);
      } catch (err) {
        setIsPolling(false);
        setError(err instanceof APIError ? err.message : 'Failed to check render status');
      }
    };

    poll();
  };

  const stopPolling = () => {
    setIsPolling(false);
  };

  return {
    renderJob,
    isPolling,
    error,
    startRender,
    stopPolling,
  };
};
```

## 🔄 UI Integration Points

### Tab Display Logic

```typescript
// components/ResultTabs.tsx
export const ResultTabs = () => {
  const { results, states, errors } = useTabResults();

  return (
    <Tabs>
      <TabList>
        <Tab>
          Explanation 
          {states.explanation === 'loading' && <Spinner />}
          {states.explanation === 'success' && <CheckIcon />}
          {states.explanation === 'error' && <ErrorIcon />}
        </Tab>
        <Tab>
          Example
          {states.example === 'loading' && <Spinner />}
          {states.example === 'success' && <CheckIcon />}
          {states.example === 'error' && <ErrorIcon />}
        </Tab>
        <Tab>
          Code
          {states.manim === 'loading' && <Spinner />}
          {states.manim === 'success' && <CheckIcon />}
          {states.manim === 'error' && <ErrorIcon />}
        </Tab>
        <Tab>Video</Tab>
      </TabList>

      <TabPanels>
        <TabPanel>
          {states.explanation === 'loading' && <LoadingSpinner />}
          {states.explanation === 'error' && (
            <ErrorDisplay 
              message={errors.explanation} 
              onRetry={() => retryExplanation()} 
            />
          )}
          {results.explanation && (
            <ExplanationDisplay data={results.explanation} />
          )}
        </TabPanel>

        <TabPanel>
          {states.example === 'loading' && <LoadingSpinner />}
          {states.example === 'error' && (
            <ErrorDisplay 
              message={errors.example} 
              onRetry={() => retryExample()} 
            />
          )}
          {results.example && (
            <ExampleDisplay data={results.example} />
          )}
        </TabPanel>

        <TabPanel>
          {states.manim === 'loading' && <LoadingSpinner />}
          {states.manim === 'error' && (
            <ErrorDisplay 
              message={errors.manim} 
              onRetry={() => retryManim()} 
            />
          )}
          {results.manim && (
            <ManimCodeDisplay data={results.manim} />
          )}
        </TabPanel>

        <TabPanel>
          <RenderPanel />
        </TabPanel>
      </TabPanels>
    </Tabs>
  );
};
```

### Render Panel

```typescript
// components/RenderPanel.tsx
export const RenderPanel = () => {
  const { results } = useTabResults();
  const { renderJob, isPolling, error, startRender } = useRenderPolling();

  const handleRenderClick = () => {
    if (results.manim) {
      startRender(results.manim.filename, results.manim.code);
    }
  };

  if (!results.manim) {
    return <div>Generate animation code first</div>;
  }

  return (
    <div>
      <button 
        onClick={handleRenderClick}
        disabled={isPolling || !results.manim}
      >
        {isPolling ? 'Rendering...' : 'Render Animation'}
      </button>

      {renderJob && (
        <div>
          <p>Status: {renderJob.status}</p>
          {renderJob.status === 'queued' && <p>Waiting in queue...</p>}
          {renderJob.status === 'rendering' && <p>Creating animation...</p>}
          {renderJob.status === 'ready' && renderJob.videoUrl && (
            <video controls src={renderJob.videoUrl} />
          )}
          {renderJob.status === 'error' && (
            <ErrorDisplay message={renderJob.error || 'Rendering failed'} />
          )}
        </div>
      )}

      {error && <ErrorDisplay message={error} />}
    </div>
  );
};
```

## 🧪 Integration Testing Checklist

### Pre-Integration Checks

- [ ] Backend server running on `http://localhost:8000`
- [ ] Backend health check responds: `curl http://localhost:8000/health`
- [ ] Frontend environment variable set: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
- [ ] CORS configured: `ALLOWED_ORIGINS=http://localhost:3000` in backend `.env`
- [ ] Gemini API key configured in backend

### Basic Connectivity

- [ ] Frontend can reach backend health endpoint
- [ ] No CORS errors in browser console
- [ ] API requests include proper headers
- [ ] Request/response logging works (check browser Network tab)

### API Endpoint Testing

- [ ] **Lesson Generation**: 
  - [ ] Successful generation with valid topic
  - [ ] Error handling for invalid topic (too short/long)
  - [ ] Response matches `LessonResponse` schema
  - [ ] Tab shows loading → success states

- [ ] **Example Generation**:
  - [ ] Successful generation with lesson context
  - [ ] Error handling for validation failures
  - [ ] Response matches `ExampleResponse` schema
  - [ ] Depends on lesson completion

- [ ] **Manim Generation**:
  - [ ] Successful code generation with example context
  - [ ] Generated code contains valid Python/Manim syntax
  - [ ] Response matches `ManimResponse` schema
  - [ ] Code display with syntax highlighting

- [ ] **Render Pipeline**:
  - [ ] Render job creation returns valid job ID
  - [ ] Polling updates job status correctly
  - [ ] Video displays when render completes
  - [ ] Error handling for render failures

### Error Scenarios

- [ ] **Rate Limiting**: Proper handling of 429 responses
- [ ] **Validation Errors**: User-friendly error messages for 400 responses
- [ ] **Server Errors**: Graceful handling of 500 responses
- [ ] **Network Errors**: Timeout and connectivity error handling
- [ ] **Individual Tab Retry**: Failed tabs can be retried independently

### User Experience

- [ ] **Partial Results**: Show results as they arrive
- [ ] **Loading States**: Clear loading indicators per tab
- [ ] **Error States**: Specific error messages with retry options
- [ ] **Progress Feedback**: Render progress updates
- [ ] **Responsive Design**: Works on different screen sizes

## 🐛 Troubleshooting

### Common Integration Issues

#### 1. CORS Errors
```
Access to fetch at 'http://localhost:8000/api/lesson' from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Solutions:**
- Check `ALLOWED_ORIGINS=http://localhost:3000` in backend `.env`
- Restart backend after changing CORS settings
- Verify frontend is running on port 3000

#### 2. API Base URL Issues
```
TypeError: Failed to fetch
```

**Solutions:**
- Verify `NEXT_PUBLIC_API_BASE_URL` is set correctly
- Check backend server is running: `curl http://localhost:8000/health`
- Ensure no trailing slash in API base URL

#### 3. Schema Validation Errors
```
Property 'bullets' is missing in type...
```

**Solutions:**
- Update frontend types to match backend response schemas
- Check API response format in browser Network tab
- Verify backend is returning correct data structure

#### 4. Render Polling Issues
```
Job status stuck in 'rendering'
```

**Solutions:**
- Check backend logs for Manim errors
- Verify FFmpeg is installed and accessible
- Test Manim installation: `manim --version`
- Check render timeout settings

#### 5. Environment Variable Issues
```
NEXT_PUBLIC_API_BASE_URL is undefined
```

**Solutions:**
- Restart Next.js dev server after adding environment variables
- Verify `.env.local` file location (in project root)
- Check variable name has `NEXT_PUBLIC_` prefix

### Debug Tools

#### 1. Browser Developer Tools
- **Network Tab**: Inspect API requests/responses
- **Console**: Check for errors and warnings
- **Application Tab**: Verify environment variables

#### 2. Backend Logs
```bash
# Check backend logs for request tracing
tail -f backend_logs.log | grep "X-Request-ID"
```

#### 3. API Testing
```bash
# Test API endpoints directly
curl -X POST http://localhost:8000/api/lesson \
  -H "Content-Type: application/json" \
  -d '{"topic": "test"}'
```

### Performance Optimization

#### 1. Request Batching
Consider implementing request batching for better performance:

```typescript
// Batch multiple API calls
const generateAllContent = async (topic: string) => {
  const lesson = await apiClient.generateLesson(topic);
  
  // Start example and manim generation in parallel once lesson is ready
  const [example, manim] = await Promise.all([
    apiClient.generateExample(topic, lesson.explanation),
    // You could start manim with lesson data, then update when example is ready
    apiClient.generateLesson(topic).then(l => 
      apiClient.generateExample(topic, l.explanation).then(e =>
        apiClient.generateManim(topic, e.example)
      )
    )
  ]);
  
  return { lesson, example, manim };
};
```

#### 2. Caching Strategy
```typescript
// Cache results to avoid re-generation
const cache = new Map<string, any>();

const getCachedOrGenerate = async (key: string, generator: () => Promise<any>) => {
  if (cache.has(key)) {
    return cache.get(key);
  }
  
  const result = await generator();
  cache.set(key, result);
  return result;
};
```

## ✅ Success Criteria

Your frontend integration is successful when:

- [ ] All API endpoints work without CORS errors
- [ ] Complete pipeline works: topic → lesson → example → manim → video
- [ ] Individual tab failures don't break other tabs
- [ ] Error messages are user-friendly and actionable
- [ ] Loading states provide clear feedback
- [ ] Render polling works reliably
- [ ] Performance is acceptable (< 5s for content generation)
- [ ] No console errors or warnings
- [ ] Mobile/responsive design works correctly

Once all criteria are met, your frontend is seamlessly integrated with the backend API! 🎉


