15-Step Checklist for Frontend MVP (Next.js App Router - Dummy UI)

[x] Step 1: Project Setup & Styling Foundation
Action: Install and configure Tailwind CSS in your Next.js project.
Details: Follow the Next.js + Tailwind guide. Create tailwind.config.js and postcss.config.js. Update globals.css with Tailwind directives.
Goal: Tailwind working → rapid class-based styling.

[x] Step 2: Global Layout & Navigation Shell
Action: Modify app/layout.tsx and create a Navbar component.
Details:

In app/layout.tsx, set up <html> and <body>.

Create components/Navbar.tsx with dummy links: “AI Tutor MVP” (home), “Dashboard”, “About”.

Render <Navbar /> above {children} in layout.
Goal: Persistent navigation bar across all pages.

[x] Step 3: Landing Page with Topic Input (UI Only)
Action: Create the homepage for entering a topic.
Details:

File: app/page.tsx.

Input field for “Enter a topic” and a “Generate” button.

Use useState to track the topic string.

Button just logs topic to console for now.
Goal: Simple input flow to start the tutor.

[x] Step 4: API Response Tabs (Dummy Data)
Action: Build a tabbed view for displaying results.
Details:

Create components/Tabs.tsx with 4 tabs: Explanation, Example, Manim Code, Raw JSON.

For now, render dummy static content inside each tab.
Goal: Tab structure ready for integration.

[x] Step 5: Explanation View (UI Only)
Action: Create a component to show explanation text.
Details:

File: components/ExplanationView.tsx.

Accepts props like title and bullets: string[].

For MVP, show hardcoded dummy explanation.
Goal: Visual structure for explanation section.

[x] Step 6: Example View (UI Only)
Action: Build a component to render examples.
Details:

File: components/ExampleView.tsx.

Show prompt, walkthrough (as steps), and answer.

Render with dummy example data.
Goal: Placeholder for example walkthroughs.

[x] Step 7: Manim Code View (UI Only)
Action: Create a code block viewer for Manim snippets.
Details:

File: components/ManimCodeView.tsx.

Render syntax-highlighted Python code.

Add “Copy” and “Download” buttons (dummy actions).
Goal: UI to present animation code cleanly.

[x] Step 8: Raw JSON Viewer
Action: Provide a collapsible JSON inspector.
Details:

File: components/JSONViewer.tsx.

Pretty-print JSON object (dummy placeholder initially).

Add a “Copy JSON” button.
Goal: Debug-friendly raw output display.

[x] Step 9: Hook Up Dummy API Calls
Action: Mock the 3 API calls (explanation/example/manim).
Details:

Create lib/api.ts with async functions returning dummy JSON after setTimeout.

On submit, call these functions in parallel (Promise.all).

Show combined result in tabs.
Goal: End-to-end flow working with fake data.

[x] Step 10: Loading & Error States
Action: Add skeletons and error handling.
Details:

Show skeleton loaders in tabs while fetching.

If any API fails, show inline error in that tab.

If all fail, show global error card.
Goal: Resilient UI for all states.

[x] Step 11: Dashboard Page (UI Only)
Action: Create a dummy dashboard page for users.
Details:

File: app/dashboard/page.tsx.

Show “Recent Topics” list (static dummy data).

Each item links back to home with prefilled topic.
Goal: Basic navigation to saved lessons.

[x] Step 12: Auth Placeholder (UI Only)
Action: Add dummy login/logout flow.
Details:

Create app/login/page.tsx with email + password fields.

Add a dummy AuthContext with isAuthenticated.

Navbar shows “Login” or “Logout” based on state.
Goal: Fake login state toggling.

[x] Step 13: Responsiveness & Dark Mode
Action: Ensure mobile usability.
Details:

Tailwind responsive prefixes for stacking inputs, tabs, and cards.

Add dark mode toggle using class="dark".
Goal: App usable on mobile + dark mode works.

[x] Step 14: JSON Schema Validation (UI Only)
Action: Add client-side schema guards.
Details:

Define Zod schema for TutorResponse.

Validate dummy API responses before rendering.

If invalid, show “Invalid Data” in Raw JSON tab.
Goal: Safety net for bad responses.

[x] Step 15: Final Cleanup & Review
Action: Organize and polish.
Details:

Move components into folders (components/tabs, components/views).

Remove stray console.logs.

Verify all dummy actions clearly marked.

Click through every flow: Topic → Generate → Tabs → Dashboard.
Goal: A clean, working dummy MVP ready for API wiring.

[x] Step 16: Configure Backend Base URL & Contracts
Action: Add environment variables and align the JSON contract.
Details:

Create .env.local in frontend with:

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000


Replace any VITE_* refs with NEXT_PUBLIC_API_BASE_URL.

Centralize types in types/tutor.ts and export the exact schema used by the UI.
Goal: Frontend can point to local backend without code changes elsewhere.

[x] Step 17: Replace Mock Calls with Real Endpoints
Action: Update the API layer to hit the backend.
Details:

In lib/api.ts, point to:

POST /api/lesson → returns { explanation }

POST /api/example → returns { example }

POST /api/manim → returns { manim }

(Later) POST /api/render → returns { jobId } and GET /api/render/:jobId → { status, videoUrl? }

Keep the same return shapes you already render.
Goal: Same UI, now talking to real backend.

[x] Step 18: Add Video Preview Panel with Polling
Action: Allow the Manim video preview when available.
Details:

In components/ManimCodeView.tsx, beneath the code block add:

“Render Animation” button → calls POST /api/render with { filename, code }.

Start polling GET /api/render/:jobId every 2–3s for status.

When status === "ready", show <video controls src={videoUrl} />.

Add a small inline status chip: Rendering…, Queued, Error.
Goal: Users can trigger render and see the video when done.

[x] Step 19: Add Topic Suggestions and Search
Action: Improve resilience across the three calls.
Details:

If one of the three calls fails, show a tab-level error chip and a Retry button only for that tab.

Keep and display successful tabs immediately; don’t block on the failing tab.
Goal: Smooth partial-success experience.

[x] Step 20: Partial Success & Retry UX
Action: Add event logging (console for now).
Details:

Log: topic_submitted, explanation_ok|fail, example_ok|fail, manim_ok|fail, render_job_created, render_status_update, render_ready, render_error.

Include durations to measure backend latency.
Goal: Quick visibility into bottlenecks and failures.# AI_tutor
