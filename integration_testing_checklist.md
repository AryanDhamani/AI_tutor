# Frontend-Backend Integration Testing Checklist

Complete checklist to verify seamless integration between AI Tutor frontend and backend.

## 🔧 Pre-Integration Setup

### Backend Configuration
- [ ] Backend server running on `http://localhost:8000`
- [ ] Health endpoint responds: `GET http://localhost:8000/health`
- [ ] Environment variables configured:
  - [ ] `GEMINI_API_KEY` set with valid API key
  - [ ] `ALLOWED_ORIGINS=http://localhost:3000`
  - [ ] `DEBUG=true` for detailed logging
- [ ] All dependencies installed and working:
  - [ ] Manim: `manim --version`
  - [ ] FFmpeg: `ffmpeg -version`
- [ ] Backend test suite passes: `python test_backend.py`

### Frontend Configuration
- [ ] Frontend running on `http://localhost:3000`
- [ ] Environment variable set: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
- [ ] No build errors or console warnings
- [ ] API client properly configured

## 🌐 Basic Connectivity

### CORS and Network
- [ ] **No CORS errors** in browser console
- [ ] **Health check works** from frontend to backend
- [ ] **Request headers** include `Content-Type: application/json`
- [ ] **Response headers** include `X-Request-ID` from backend
- [ ] **Network tab** shows successful API calls with proper status codes

### Error Handling Foundation
- [ ] **Network failures** handled gracefully (disconnect backend and test)
- [ ] **Timeout errors** handled properly
- [ ] **404 errors** for invalid endpoints handled
- [ ] **500 errors** display user-friendly messages

## 📝 API Endpoint Testing

### 1. Lesson Generation (`POST /api/lesson`)

#### Happy Path
- [ ] **Valid topic** (e.g., "Pythagorean theorem") generates lesson
- [ ] **Response structure** matches schema:
  ```json
  {
    "explanation": {
      "title": "string",
      "bullets": ["string", "string", ...]  // 4-7 items
    }
  }
  ```
- [ ] **Loading state** shows during API call
- [ ] **Success state** displays lesson content
- [ ] **Tab indicator** shows success (checkmark/green)

#### Error Cases
- [ ] **Topic too short** (< 3 chars) shows validation error
- [ ] **Topic too long** (> 120 chars) shows validation error
- [ ] **Empty topic** shows validation error
- [ ] **Malicious content** (e.g., `<script>`) rejected
- [ ] **Rate limiting** (after 5 requests) shows appropriate message
- [ ] **Server error** shows generic error message
- [ ] **Network error** shows connectivity error

#### UI Behavior
- [ ] **Explanation tab** populates with generated content
- [ ] **Retry button** works after errors
- [ ] **Content format** properly displays title and bullets
- [ ] **Loading spinner** shows during generation

### 2. Example Generation (`POST /api/example`)

#### Happy Path
- [ ] **Valid request** with lesson context generates example
- [ ] **Response structure** matches schema:
  ```json
  {
    "example": {
      "prompt": "string",
      "walkthrough": ["step1", "step2", ...],  // 3-7 steps
      "answer": "string"  // optional
    }
  }
  ```
- [ ] **Contextual generation** uses lesson data appropriately
- [ ] **Loading and success states** work correctly

#### Error Cases
- [ ] **Missing lesson context** handled gracefully
- [ ] **Invalid lesson data** shows appropriate error
- [ ] **All lesson error scenarios** apply here too

#### UI Behavior
- [ ] **Example tab** populates with problem and solution
- [ ] **Walkthrough steps** display as numbered list
- [ ] **Answer section** shows when available

### 3. Manim Code Generation (`POST /api/manim`)

#### Happy Path
- [ ] **Valid request** with example context generates code
- [ ] **Response structure** matches schema:
  ```json
  {
    "manim": {
      "language": "python",
      "filename": "string",
      "code": "string",
      "notes": ["note1", "note2"]  // optional
    }
  }
  ```
- [ ] **Generated code** contains `from manim import *`
- [ ] **Generated code** contains class definition
- [ ] **Generated code** contains `def construct(self):`

#### Code Quality
- [ ] **Syntax highlighting** works in code display
- [ ] **Code is readable** and properly formatted
- [ ] **No dangerous imports** (os, sys, subprocess, etc.)
- [ ] **Reasonable length** (40-80 lines typical)

#### Error Cases
- [ ] **Invalid example context** handled
- [ ] **Code generation failures** show helpful errors
- [ ] **Safety violations** properly rejected

### 4. Render Pipeline (`POST /api/render` + polling)

#### Render Job Creation
- [ ] **Valid render request** creates job successfully
- [ ] **Response structure** matches schema:
  ```json
  {
    "jobId": "string",
    "status": "queued",
    "videoUrl": null,
    "error": null
  }
  ```
- [ ] **Job ID** is valid UUID format
- [ ] **Initial status** is "queued"

#### Status Polling (`GET /api/render/{jobId}`)
- [ ] **Polling starts** immediately after job creation
- [ ] **Status updates** show progression: queued → rendering → ready
- [ ] **Polling interval** is reasonable (2-3 seconds)
- [ ] **Polling stops** when status is "ready" or "error"
- [ ] **Video URL** provided when status is "ready"

#### Video Display
- [ ] **Video player** shows when render completes
- [ ] **Video URL** works and serves actual video file
- [ ] **Video content** matches the generated animation
- [ ] **Video controls** (play, pause, volume) work

#### Error Scenarios
- [ ] **Invalid filename** rejected with validation error
- [ ] **Invalid code** (dangerous imports) rejected
- [ ] **Render failures** show in job status with error message
- [ ] **Missing job ID** shows 404 error
- [ ] **Polling errors** handled gracefully

## 🎯 Complete User Workflows

### Full Pipeline Test
1. [ ] **Enter topic**: "Pythagorean theorem"
2. [ ] **Click Generate**: All 3 tabs start loading
3. [ ] **Partial results**: Tabs show results as they complete
4. [ ] **All tabs complete**: Explanation, Example, and Code tabs populated
5. [ ] **Click Render**: Video tab shows render progress
6. [ ] **Video ready**: Video displays and plays correctly

### Error Recovery Test
1. [ ] **Trigger error**: Use invalid topic or disconnect backend
2. [ ] **Error display**: Appropriate error message shown
3. [ ] **Individual retry**: Failed tab can be retried independently
4. [ ] **Success after retry**: Tab recovers and shows content

### Rate Limiting Test
1. [ ] **Multiple requests**: Click Generate multiple times quickly
2. [ ] **Rate limit hit**: Appropriate message shown
3. [ ] **Wait and retry**: Works after rate limit window
4. [ ] **User guidance**: Clear instruction on when to retry

## 📱 UI/UX Integration

### Tab States and Indicators
- [ ] **Loading states**: Spinners/progress indicators during API calls
- [ ] **Success states**: Check marks or green indicators
- [ ] **Error states**: Error icons or red indicators
- [ ] **Idle states**: Clear when no action has been taken

### Content Display
- [ ] **Explanation content**: Title and bullets properly formatted
- [ ] **Example content**: Problem statement and walkthrough steps clear
- [ ] **Code content**: Syntax highlighted and readable
- [ ] **Video content**: Proper video player with controls

### Responsive Design
- [ ] **Mobile view**: All functionality works on mobile
- [ ] **Tablet view**: Layout adapts properly
- [ ] **Desktop view**: Optimal use of screen space
- [ ] **Tab switching**: Smooth transitions between tabs

### Accessibility
- [ ] **Keyboard navigation**: Can navigate with keyboard only
- [ ] **Screen reader**: Content properly labeled
- [ ] **Color contrast**: Sufficient contrast for all text
- [ ] **Focus indicators**: Clear focus states for interactive elements

## ⚡ Performance Integration

### Response Times
- [ ] **Health check**: < 100ms
- [ ] **Lesson generation**: 2-10 seconds acceptable
- [ ] **Example generation**: 3-15 seconds acceptable
- [ ] **Manim generation**: 5-30 seconds acceptable
- [ ] **Render completion**: 30-300 seconds acceptable

### Loading Experience
- [ ] **Immediate feedback**: Loading states appear instantly
- [ ] **Partial results**: Show content as it becomes available
- [ ] **Progress indication**: Users understand what's happening
- [ ] **Timeout handling**: Long operations don't hang indefinitely

### Resource Management
- [ ] **Memory usage**: No memory leaks during extended use
- [ ] **API calls**: No unnecessary duplicate requests
- [ ] **Polling efficiency**: Polling stops when not needed
- [ ] **Cleanup**: Proper cleanup when navigating away

## 🔒 Security Integration

### Input Validation
- [ ] **Client-side validation**: Basic validation before API calls
- [ ] **Server-side validation**: Backend properly validates all inputs
- [ ] **XSS prevention**: Malicious input properly sanitized
- [ ] **Injection prevention**: No code injection vulnerabilities

### API Security
- [ ] **Rate limiting**: Proper rate limiting enforced
- [ ] **CORS policy**: Only allowed origins can access API
- [ ] **Headers security**: Proper security headers in responses
- [ ] **Error information**: Error messages don't leak sensitive info

## 📊 Monitoring Integration

### Request Tracing
- [ ] **Request IDs**: All requests include tracing IDs
- [ ] **Error correlation**: Frontend and backend errors can be correlated
- [ ] **Performance tracking**: Request timing data available
- [ ] **User actions**: User interactions properly logged

### Health Monitoring
- [ ] **System health**: Can check backend health from frontend
- [ ] **Service status**: Can detect when backend is down
- [ ] **Graceful degradation**: Frontend handles backend outages
- [ ] **Recovery notification**: Users notified when service recovers

## 🚀 Production Readiness

### Environment Handling
- [ ] **Development**: Works in local development environment
- [ ] **Staging**: Works with staging backend deployment
- [ ] **Production**: Ready for production deployment
- [ ] **Environment switching**: Easy to switch between environments

### Error Boundary
- [ ] **Global error handling**: Unhandled errors caught gracefully
- [ ] **Error reporting**: Errors properly logged/reported
- [ ] **Fallback UI**: Graceful fallback when components fail
- [ ] **Recovery guidance**: Users get actionable error messages

### Documentation
- [ ] **Integration guide**: Clear documentation for future developers
- [ ] **API contracts**: Frontend expectations documented
- [ ] **Error scenarios**: Known issues and solutions documented
- [ ] **Troubleshooting**: Common problems and fixes documented

## ✅ Sign-off Criteria

### Functional Requirements
- [ ] All API endpoints work correctly
- [ ] Complete user workflow functional (topic → video)
- [ ] Error handling comprehensive and user-friendly
- [ ] Performance within acceptable limits

### Quality Requirements
- [ ] No console errors or warnings
- [ ] Responsive design works on all screen sizes
- [ ] Accessibility standards met
- [ ] Code quality standards met

### Integration Requirements
- [ ] Zero UI changes needed when swapping from mocks
- [ ] Backend API changes don't break frontend
- [ ] Frontend changes don't require backend modifications
- [ ] Independent deployment possible

## 📋 Final Verification

### End-to-End Test
1. [ ] Fresh browser session (clear cache/storage)
2. [ ] Complete user journey: topic input → video output
3. [ ] Test error scenarios and recovery
4. [ ] Test on different browsers (Chrome, Firefox, Safari)
5. [ ] Test on different devices (desktop, tablet, mobile)

### Integration Stability
- [ ] **10 successful pipeline runs** without errors
- [ ] **Error recovery** works consistently
- [ ] **Performance** remains stable over time
- [ ] **No regressions** in existing functionality

### Documentation Complete
- [ ] Integration guide reviewed and approved
- [ ] Troubleshooting guide tested and verified
- [ ] API documentation matches implementation
- [ ] Setup instructions work for new developers

---

## 🎉 Integration Success!

When all checklist items are complete, your frontend is successfully integrated with the backend API! 

The integration should be:
- ✅ **Seamless**: No UI changes when switching from mocks
- ✅ **Robust**: Handles all error scenarios gracefully  
- ✅ **Performant**: Meets response time requirements
- ✅ **Reliable**: Works consistently across environments
- ✅ **Maintainable**: Clear documentation and troubleshooting guides


