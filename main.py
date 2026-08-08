import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from models import InterviewRequest, InterviewResponse
import ranking
import session_store

app = FastAPI(title="AI Technical Interview Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Load curriculum reference data once at startup
curriculum_data = ranking.load_curriculum("curriculum.json")


@app.get("/")
async def serve_index():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "AI Technical Interview Agent API"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/interview", response_model=InterviewResponse)
async def interview_endpoint(req: InterviewRequest):
    # Turn 1: Initial candidate submission
    if req.candidate is not None:
        # 1. Calculate weak-spot day ranking (pure Python logic, joined strictly by day integer)
        ranked_weak_spots = ranking.rank_weak_spots(req.candidate, curriculum_data)

        # 2. Store new session in session_store with counters & ranked weak spots
        session_store.create_session(
            session_id=req.sessionId,
            candidate=req.candidate,
            ranked_weak_spots=ranked_weak_spots
        )

        # 3. Construct Turn 1 reply referencing top weak spot's curriculum title
        if ranked_weak_spots and ranked_weak_spots[0]["score"] > 0:
            top_spot = ranked_weak_spots[0]
            reply_text = (
                f"Hi! I see we should focus on Day {top_spot['day']}: {top_spot['title']} first. "
                "(Placeholder — real question generation comes next phase.)"
            )
        else:
            cand_name = req.candidate.member.name if req.candidate.member else "Candidate"
            reply_text = (
                f"Welcome {cand_name}. Let's begin your interview. "
                "(Placeholder — real question generation comes next phase.)"
            )

        return InterviewResponse(
            reply=reply_text,
            done=False,
        )

    # Turn 2+: Follow-up messaging
    elif req.message is not None:
        # Check if session exists in memory
        session = session_store.get_session(req.sessionId)
        if session is None:
            return InterviewResponse(
                reply="Session not found, please start a new interview.",
                done=True
            )

        return InterviewResponse(
            reply="Placeholder follow-up.",
            done=False,
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Request payload must include either 'candidate' or 'message'.",
        )
