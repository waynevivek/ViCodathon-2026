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

