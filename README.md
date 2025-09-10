[x] Step 1: Environment & Tooling Setup
Action: Prepare a clean Python env.
Details:

Use Python 3.10–3.12. Create & activate a virtualenv.

Ensure FFmpeg is installed and on PATH (required by Manim/moviepy).

Windows note: if Manim complains, install VC++ build tools and update GPU drivers.
Goal: Reproducible, isolated runtime for the API and renderer.

[x] Step 2: Dependency Install (No App Code Yet)
Action: Install core libs.
Details: FastAPI, Uvicorn, Pydantic v2, python-dotenv, google-generativeai, manim, moviepy.
Goal: All runtime deps present for Gemini calls + video render.

[x] Step 3: Project Structure (Folders Only)
Action: Create folders (no files yet).
Details:

backend/
  app/
    services/          # gemini client, manim runner, job store
    storage/
      code/            # temp .py files generated for manim
      videos/          # rendered .mp4 files served to frontend
  .env.example
  requirements.txt
  README.md


Goal: Clear separation of API logic, services, and storage.

[x] Step 4: Configuration & Secrets
Action: Set environment variables.
Details: Add .env with:

GEMINI_API_KEY= your key

ALLOWED_ORIGINS=http://localhost:3000 (frontend)

MANIM_QUALITY=L (L/M/H), RENDER_TIMEOUT_SEC=180

(Optional) DATA_DIR if you want explicit absolute paths
Goal: Centralized config for Gemini, CORS, and rendering.

[x] Step 5: CORS & Server Boot
Action: Enable CORS and run the server.
Details:

Allow origin http://localhost:3000.

Health check endpoint (e.g., /health) to verify boot.
Goal: Frontend can reach backend locally without CORS errors.

[x] Step 6: API Contract – Mirror Frontend
Action: Define your request/response shapes (no code).
Details (names & types):

LessonResponse → explanation: { title: string; bullets: string[] }

ExampleResponse → example: { prompt: string; walkthrough: string[]; answer?: string }

ManimResponse → manim: { language: "python"; filename: string; code: string; notes?: string[] }

RenderJob → { jobId: string; status: "queued"|"rendering"|"ready"|"error"; videoUrl?: string; error?: string }
Goal: Exact 1:1 shape with your UI’s Zod types.

[x] Step 7: Gemini Prompting Strategy
Action: Design three prompts (no code).
Details:

Lesson plan: “Return JSON ONLY with explanation{title, bullets[]}… concise 4–7 bullets, no markdown fences.”

Example: “Return JSON ONLY with example{prompt, walkthrough[], answer?}… 3–7 clear steps.”

Manim code: “Return code only (no prose). One Scene subclass, ~40–80 lines, prefer Text() to avoid LaTeX.”

Require strict JSON for 1 & 2; strip fences if the model adds them.
Goal: Deterministic, parseable outputs that pass schema validation.

[x] Step 8: Request Validation & Safety
Action: Decide validation rules (enforced server-side).
Details:

Topic length: 3–120 chars; strip control chars.

For filename, allow only safe [a-zA-Z0-9_-].

Reject code that includes imports outside Manim stdlib (simple scan).

Rate-limit per IP (simple in-memory counter) to prevent abuse.
Goal: Prevent malicious inputs and safeguard the renderer.

[x] Step 9: Endpoints & Flow (Design Only)
Action: Finalize endpoint behaviors.
Details:

POST /api/lesson → body { topic, plan? } → returns { explanation } (from Gemini).

POST /api/example → body { topic, explanation } → returns { example } (Gemini).

POST /api/manim → body { topic, example } → returns { manim } (Gemini code string).

POST /api/render → body { filename, code } → returns { jobId, status:"queued" }.

GET /api/render/:jobId → returns { status, videoUrl? }.
Goal: Clear, minimal surface area the frontend can call.

[x] Step 10: Render Pipeline (Operational Plan)
Action: Define how a render runs.
Details:

Create a job with jobId, status queued.

Save {filename}.py under storage/code/.

Launch manim CLI with chosen quality (L/M/H), output to storage/videos/{filename}.mp4.

Update job status: rendering → ready (or error).

Serve /static/videos/{filename}.mp4 so frontend can play it.
Goal: Deterministic, observable path from code → mp4.

[x] Step 11: Job Store & Polling Model
Action: Choose simple in-memory job tracking for MVP.
Details:

Job fields: id, status, videoUrl, error.

Background worker/process to execute queued jobs.

Frontend polls every 2–3s until ready|error.
Goal: Reliable UX without introducing external queues yet.

[x] Step 12: Logging & Observability
Action: Define logs and metrics (console/file).
Details:

Log each request: topic hash, durations for Gemini & render.

Log job lifecycle: created → rendering → ready/error.

Add a request X-Request-ID for traceability.
Goal: Fast diagnosis of latency, failures, and bad inputs.

[x] Step 13: Local Testing Plan
Action: Smoke-test each endpoint.
Details:

/api/lesson with a simple topic (e.g., “Pythagorean theorem”) → expect JSON explanation.

Chain into /api/example → expect steps + answer.

/api/manim → ensure code string returns (no prose).

/api/render then poll → verify videoUrl serves an mp4 that plays.
Goal: Confirm the full pipeline before wiring to UI.

[x] Step 14: Frontend Integration Checklist
Action: Point the UI to this backend.
Details:

In ai-tutor-mvp/.env.local, set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000.

Map calls 1:1:

Generate → POST /api/lesson, POST /api/example, POST /api/manim (parallel).

“Render Animation” → POST /api/render then poll GET /api/render/:jobId.

Tabs show partial results immediately; retry failing tab individually.
Goal: Seamless swap from mocks to real API with zero UI change.

[x] Step 15: Deployment & Hardening Plan
Action: Prep for moving beyond local.
Details:

Process model: Uvicorn with multiple workers for concurrency; separate render worker if heavy.

File storage: Persist storage/videos (volume or object storage) and secure /static.

Security: Set strict CORS, sanitize filenames, enforce rate limits, cap topic length, cap code size.

Reliability: Timeouts for Gemini/render, retries for transient errors, cleanup old jobs/files.

Docs: “How to run locally”, “How to configure keys”, “Known limitations” (e.g., no sandboxed Python).
Goal: Stable, secure MVP ready for demos and iterative productionization.