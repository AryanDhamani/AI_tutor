# AI Tutor Backend - Setup and Testing Guide

This guide walks you through setting up and testing the AI Tutor backend to ensure everything works correctly before frontend integration.

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
.\venv\Scripts\Activate.ps1    # Windows PowerShell
# source venv/bin/activate     # Linux/Mac

# Verify dependencies are installed
pip list | grep -E "(fastapi|manim|google-generativeai)"
```

### 2. Configuration

```bash
# Copy environment template
cp env.example .env

# Edit .env file with your settings
# Required: Set your Gemini API key
GEMINI_API_KEY=your_actual_api_key_here

# Optional: Adjust other settings
MANIM_QUALITY=L              # L (low), M (medium), H (high)
RENDER_TIMEOUT_SEC=180       # Timeout for rendering
ALLOWED_ORIGINS=http://localhost:3000
```

**Get Gemini API Key:**
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create or select a project
3. Generate an API key
4. Copy the key to your `.env` file

### 3. Start the Server

```bash
# Method 1: Using the run script
python run_server.py

# Method 2: Direct uvicorn
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Method 3: Using the module
python -m app.main
```

**Expected Output:**
```
🚀 AI Tutor Backend starting up...
📍 Server will run on 127.0.0.1:8000
🌐 CORS allowed origins: http://localhost:3000
🎥 Manim quality: L
⏱️  Render timeout: 180s
🔧 Debug mode: True
🧹 Background cleanup task started
INFO:     Started server process [1234]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

## 🧪 Testing

### Automated Test Suite

Run the comprehensive test suite to verify all functionality:

```bash
# Make sure server is running first!
python test_backend.py
```

**What it tests:**
- ✅ Health check endpoint
- ✅ Lesson generation (Gemini AI)
- ✅ Example generation (Gemini AI)
- ✅ Manim code generation (Gemini AI)
- ✅ Render job creation
- ✅ Render status polling
- ✅ Input validation
- ✅ Error handling
- ✅ Rate limiting
- ✅ Monitoring endpoints

**Expected Output:**
```
🚀 AI Tutor Backend Test Suite
============================================================
[12:34:56] INFO: Testing server connectivity...
✅ Connected to server at http://localhost:8000
============================================================
RUNNING FULL PIPELINE TEST
============================================================
[12:34:57] INFO: Testing health check endpoint...
✅ Health check passed
[12:34:58] INFO: Testing lesson generation...
✅ Lesson generation passed
...
🎉 ALL TESTS PASSED! Backend is ready for frontend integration.
```

### Performance Testing

Test system performance and limits:

```bash
# Install aiohttp for async testing
pip install aiohttp

# Run performance tests
python performance_test.py
```

### Manual Testing

#### 1. Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000",
  "version": "1.0.0",
  "service": "ai-tutor-backend"
}
```

#### 2. API Documentation
Visit: http://127.0.0.1:8000/docs

#### 3. Lesson Generation
```bash
curl -X POST http://localhost:8000/api/lesson \
  -H "Content-Type: application/json" \
  -d '{"topic": "Pythagorean theorem"}'
```

#### 4. Complete Pipeline Test
```bash
# 1. Generate lesson
LESSON=$(curl -s -X POST http://localhost:8000/api/lesson \
  -H "Content-Type: application/json" \
  -d '{"topic": "Pythagorean theorem"}')

echo $LESSON | jq .

# 2. Generate example (use lesson result)
EXAMPLE=$(curl -s -X POST http://localhost:8000/api/example \
  -H "Content-Type: application/json" \
  -d "{
    \"topic\": \"Pythagorean theorem\",
    \"explanation\": $(echo $LESSON | jq .explanation)
  }")

echo $EXAMPLE | jq .

# 3. Generate Manim code (use example result)
MANIM=$(curl -s -X POST http://localhost:8000/api/manim \
  -H "Content-Type: application/json" \
  -d "{
    \"topic\": \"Pythagorean theorem\",
    \"example\": $(echo $EXAMPLE | jq .example)
  }")

echo $MANIM | jq .

# 4. Start render job
RENDER=$(curl -s -X POST http://localhost:8000/api/render \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": $(echo $MANIM | jq -r .manim.filename),
    \"code\": $(echo $MANIM | jq -r .manim.code)
  }")

echo $RENDER | jq .
JOB_ID=$(echo $RENDER | jq -r .jobId)

# 5. Poll render status
while true; do
  STATUS=$(curl -s http://localhost:8000/api/render/$JOB_ID)
  echo $STATUS | jq .
  
  STATUS_VALUE=$(echo $STATUS | jq -r .status)
  if [ "$STATUS_VALUE" = "ready" ] || [ "$STATUS_VALUE" = "error" ]; then
    break
  fi
  
  sleep 3
done
```

### Monitoring & Observability

Check system health and metrics:

```bash
# System health
curl http://localhost:8000/monitoring/system/health | jq .

# Job metrics
curl http://localhost:8000/monitoring/jobs/metrics | jq .

# Performance metrics
curl http://localhost:8000/monitoring/performance/metrics | jq .

# Current job queue
curl http://localhost:8000/monitoring/jobs/queue | jq .
```

## 🐛 Troubleshooting

### Common Issues

#### 1. "Configuration error: GEMINI_API_KEY is required"
- **Problem:** Missing or invalid Gemini API key
- **Solution:** Set `GEMINI_API_KEY` in your `.env` file
- **Get API key:** https://aistudio.google.com/app/apikey

#### 2. "ModuleNotFoundError: No module named 'manim'"
- **Problem:** Dependencies not installed
- **Solution:** 
  ```bash
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```

#### 3. "ffmpeg: command not found"
- **Problem:** FFmpeg not installed
- **Solution:** Install FFmpeg and ensure it's in PATH
- **Windows:** Download from https://ffmpeg.org/download.html
- **Mac:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`

#### 4. Server won't start on port 8000
- **Problem:** Port already in use
- **Solution:** 
  ```bash
  # Check what's using port 8000
  netstat -ano | findstr 8000
  
  # Use different port
  uvicorn app.main:app --port 8001
  ```

#### 5. Tests fail with "Cannot connect to server"
- **Problem:** Server not running
- **Solution:** Start the server first: `python run_server.py`

#### 6. Render jobs fail with "Manim rendering failed"
- **Problem:** Manim installation or code issues
- **Solution:** 
  - Check Manim installation: `manim --version`
  - Test simple Manim scene manually
  - Check logs for detailed error messages

### Debugging

#### Enable Debug Logging
Set in `.env`:
```
DEBUG=true
LOG_LEVEL=DEBUG
```

#### View Request Logs
All requests include X-Request-ID for tracing:
```bash
curl -H "X-Request-ID: test123" http://localhost:8000/health
```

Check logs for "test123" to trace the request.

#### Test Individual Components

**Test Gemini connection:**
```python
import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content("Hello, world!")
print(response.text)
```

**Test Manim installation:**
```bash
manim --version
manim -qm -v WARNING manim_test.py TestScene
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | *(required)* | Google Gemini API key |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allowed origins |
| `MANIM_QUALITY` | `L` | Render quality: L/M/H |
| `RENDER_TIMEOUT_SEC` | `180` | Render timeout in seconds |
| `HOST` | `127.0.0.1` | Server host |
| `PORT` | `8000` | Server port |
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |

### Rate Limits

| Endpoint | Limit | Window |
|----------|--------|--------|
| `/api/lesson` | 5 requests | 5 minutes |
| `/api/example` | 5 requests | 5 minutes |
| `/api/manim` | 3 requests | 5 minutes |
| `/api/render` | 2 requests | 10 minutes |

## 📊 Performance Expectations

### Response Times (typical)
- Health check: < 50ms
- Lesson generation: 2-5 seconds
- Example generation: 3-6 seconds
- Manim code generation: 4-8 seconds
- Render job creation: < 1 second
- Video rendering: 30-180 seconds

### Throughput
- Health endpoint: 100+ req/s
- API endpoints: Limited by Gemini API rate limits
- Concurrent renders: 1-2 simultaneous jobs

## 🚀 Ready for Frontend Integration

Once all tests pass, your backend is ready! The frontend should:

1. Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
2. Use the polling pattern for render jobs
3. Handle rate limiting (429 responses)
4. Display partial results as they arrive

See `app/frontend_polling_guide.py` for detailed frontend integration examples.


