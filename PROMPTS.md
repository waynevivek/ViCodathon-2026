# Prompt History & Log

## Phase 1: Walking Skeleton (2026-08-08)

### Prompt
> Read AGENTS.md fully before doing anything — it has the locked API contract, schemas, and constraints for this project.
> 
> Goal for this phase: a walking skeleton. Real FastAPI service, correct response shapes, deployed to Render. No LLM calls yet, no real interview logic yet — just prove the pipeline works end to end.
> 
> Build:
> 1. main.py (FastAPI app, GET /health -> {"status": "ok"}, POST /api/interview stub, static/index.html at /, CORS middleware)
> 2. models.py (Pydantic models for Turn 1 request, Turn 2+ request, reply response, final feedback response)
> 3. requirements.txt (fastapi, uvicorn, python-dotenv, groq, pydantic)
> 4. Confirm .env in .gitignore
> 5. Test locally (uvicorn, curl /health, curl POST /api/interview Turn 1 & Turn 2)
> 6. Deploy setup (render.yaml / README instructions)
> 7. Verify endpoints

## Phase 2: Candidate Intake & Weak-Spot Ranking Engine (2026-08-08)

### Prompt
> Read AGENTS.md again before starting — confirm the candidate schema, curriculum schema, and the struggle-signal rules (attempts >= 3, skipped: true, passed: false) before writing any logic.
> 
> Goal for this phase: real Turn 1 handling. When a request arrives with {sessionId, candidate}, the service should:
> 1. Create and store a new session (in-memory, keyed by sessionId) via session_store.py.
> 2. Load curriculum.json and join it to the candidate's missions using the "day" integer field ONLY — never match on title strings, since day titles can mismatch between the two files for the same day number.
> 3. Compute a deterministic, ranked list of "weak-spot" days to probe during the interview, based on struggle signals in the candidate's missions:
>    - attempts >= 3
>    - skipped: true
>    - passed: false
>    Rank days by severity of struggle (e.g. a day that is both skipped AND has passed:false ranks higher than a day with just attempts >= 3 — use your judgement on a simple, explainable scoring scheme, and document the exact scoring rule as a comment in the code).
> 4. Store the ranked weak-spot day list, the candidate object, and initialized counters (questions_asked = 0, days_covered = empty set) in the session state.
> 5. Return reply referencing the actual top weak-spot day's title (pulled from curriculum.json via day-number join).
> 6. Handle unknown sessionId in Turn 2+ gracefully with friendly error reply.

## Phase 3: Groq LLM Turn 2+ Conversation Loop & Counter Rules (2026-08-08)

### Prompt
> Read AGENTS.md fully before starting — confirm the LLM action loop design, the counter rules (8-question minimum, 4-distinct-day minimum), and the retry-once-then-fallback requirement.
> 
> Goal for this phase: real Turn 2+ conversation logic driven by Groq, using the session state (weak-spot ranking, candidate, counters) already built in Phase 2. Turn 1 stays as-is from Phase 2 — do not modify it except if strictly required to pass data forward correctly.
> 
> Build:
> 1. llm.py
>    - Groq API call (model: llama-3.3-70b-versatile) using GROQ_API_KEY from .env.
>    - Prompt sent to LLM per turn includes candidate profile summary, current weak-spot day, running transcript, latest candidate message.
>    - Structured JSON action returned: {"action": "followup", "question": "..."} or {"action": "advance", "question": "...", "next_day": <int>}.
>    - Enforced via prompting and code-side JSON parsing.
>    - Retry-once-then-fallback strategy implemented.
> 2. main.py — wire Turn 2+ to append messages, call llm.py, update counters (questions_asked and days_covered), append question to transcript, check termination condition.
> 3. Update session_store.py for transcript, current day pointer, and state helpers.
> 4. Test locally with simulated multi-turn conversation and LLM fallback tests.
> 5. Confirm GROQ_API_KEY is read from .env locally and never hardcoded or logged.

## Phase 3 Bug Fix: New Topic Context on Advance (2026-08-08)

### Prompt
> Bug found in Phase 3: when the action is "advance", the interviewer's generated question is not actually about the new current day's topic — it keeps referencing the previous day's objectives even after days_covered and the day pointer have moved.
> 
> Investigate and fix: confirm that when building the prompt sent to Groq for question generation after an "advance" action, the code is passing the NEW current day's title/objectives/tools (from curriculum.json, via the day-number join) — not stale data from the previous day.
> 
> Re-run test_interview_flow.py after the fix and confirm each interviewer question, once advance happens, is actually about the correct new day's curriculum content.
> 
> Clarify: does the LLM's own returned "question" text get used directly, or does the code regenerate/re-prompt after updating the pointer?

## Phase 4: Dedicated Feedback Generation via Final LLM Call (2026-08-08)

### Prompt
> Read AGENTS.md fully before starting — confirm the feedback response shape: {summary, strengths[], gaps[], next[]}, and the design decision that feedback is generated via a DEDICATED final LLM call over the full transcript, not reused from the last chat turn.
> 
> Goal for this phase: when the interview terminates (questions_asked >= 8 AND 4 distinct days covered), generate real, honest, specific feedback instead of the current null placeholder.
> 
> Build:
> 1. llm.py — add a new function (generate_interview_feedback) that takes the full transcript, candidate profile, and probed days, sends ONE dedicated Groq call to synthesize honest feedback grounded in specific candidate statements. Includes retry-once-then-fallback pattern matching the per-turn action calls.
> 2. main.py — wire feedback generation into termination path, returning real Feedback model instead of null.
> 3. Test locally — full simulated interview through to real feedback, fallback path validation, and Phase 1-3 regression checks.

## Phase 5: Minimal Chat UI (2026-08-08)

### Prompt
> We're on Phase 5 of the build plan in AGENTS.md. Phases 1-4 (walking skeleton, candidate intake + ranking, LLM followup/advance loop, feedback generation) are complete and tested. Do not modify any backend logic in main.py, session_store.py, ranking.py, or llm.py in this phase - this is UI-only.
> 
> Goal: Build a minimal, functional chat UI in static/index.html (single file - inline CSS and JS, no build step, no external framework) that lets someone conduct a full interview through the browser against the existing /api/interview endpoint.
> 
> Required behavior:
> 1. Candidate selection (Turn 1 setup): On load, read available candidates from GET /api/candidates. Show a dropdown of candidate names. On selecting one and clicking "Start Interview", generate a sessionId (client-side UUID) and send {sessionId, candidate} to POST /api/interview per the Turn 1 contract in AGENTS.md.
> 2. Chat loop (Turn 2+): Render assistant reply in chat bubble. Text input + send button. On send, POST {sessionId, message} and render new reply. Loop until done: true.
> 3. Final feedback: When done: true, render feedback object clearly (summary, strengths[], gaps[], next[]). Disable further input once done.
> 4. Error handling: Network error or timeout retry handling with 60s timeout for Render cold start.
> 5. Styling: Clean, simple dark slate UI, legible chat bubbles, typing indicator.

