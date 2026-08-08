import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from models import InterviewRequest, InterviewResponse

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
    if req.candidate is not None:
        return InterviewResponse(
            reply="Hi! This is a placeholder response. Skeleton is working.",
            done=False,
        )
    elif req.message is not None:
        return InterviewResponse(
            reply="Placeholder follow-up.",
            done=False,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Request payload must include either 'candidate' or 'message'.",
        )
