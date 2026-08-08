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
