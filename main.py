import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from models import InterviewRequest, InterviewResponse
import ranking
import session_store
import llm

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


@app.get("/api/candidates")
async def get_candidates():
    if os.path.exists("candidates.json"):
        with open("candidates.json", "r") as f:
            return json.load(f)
    return []


@app.post("/api/interview", response_model=InterviewResponse)
async def interview_endpoint(req: InterviewRequest):
    # Turn 1: Initial candidate submission
    if req.candidate is not None:
        # 1. Calculate weak-spot day ranking (pure Python logic, joined strictly by day integer)
        ranked_weak_spots = ranking.rank_weak_spots(req.candidate, curriculum_data)

        # 2. Store new session in session_store with counters & ranked weak spots
        session = session_store.create_session(
            session_id=req.sessionId,
            candidate=req.candidate,
            ranked_weak_spots=ranked_weak_spots
        )

        # 3. Construct Turn 1 welcome message referencing top weak spot
        if ranked_weak_spots:
            top_spot = ranked_weak_spots[0]
            reply_text = (
                f"Welcome! Let's begin your technical interview. "
                f"We'll start by focusing on Day {top_spot['day']}: {top_spot['title']}. "
                f"Could you give me a brief overview of how you approached this topic?"
            )
        else:
            cand_name = req.candidate.member.name if req.candidate.member else "Candidate"
            reply_text = f"Welcome {cand_name}. Let's begin your interview with core AI concepts."

        session["transcript"].append({"role": "assistant", "content": reply_text})

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

        # 1. Append candidate's message to transcript
        session["transcript"].append({"role": "user", "content": req.message})

        # 2. Extract candidate summary & current probed day info
        cand = session.get("candidate", {})
        member = cand.get("member", {}) if isinstance(cand, dict) else {}
        cand_summary = (
            f"Name: {member.get('name', 'Candidate')}, "
            f"Role: {member.get('jobRole', 'N/A')}, "
            f"Experience: {member.get('yearsExperience', 'N/A')} years, "
            f"Education: {member.get('education', 'N/A')}"
        )
        current_day_info = session_store.get_current_day_info(session)

        # 3. Call LLM to evaluate candidate's answer on current topic (followup vs advance)
        action_dict = llm.generate_interview_action(
            cand_summary, current_day_info, session["transcript"], req.message
        )

        # 4. Increment question counter regardless of action
        session["questions_asked"] += 1

        # Safeguard: If remaining allowed questions to reach 8 are needed to reach 4 distinct days, force advance
        questions_remaining = max(0, 8 - session["questions_asked"])
        days_remaining = max(0, 4 - len(session["days_covered"]))
        if action_dict["action"] == "followup" and questions_remaining < days_remaining:
            action_dict["action"] = "advance"

        # 5. Execute action logic
        if action_dict["action"] == "advance":
            # Add previous day to days_covered set (since candidate just answered question on previous day)
            prev_day = current_day_info.get("day")
            if prev_day is not None:
                session["days_covered"].add(int(prev_day))

            # Move current day pointer to next_day (pointer change ONLY)
            session_store.advance_day_pointer(session, suggested_next_day=action_dict.get("next_day"))

            # Retrieve NEW current day info AFTER updating pointer
            new_day_info = session_store.get_current_day_info(session)

            # Generate opening question specifically using NEW day's curriculum context (title, tools, objectives)
            llm_question = llm.generate_opening_question(
                cand_summary, new_day_info, session["transcript"], req.message
            )

            # Add NEW day to days_covered because a question for it is being delivered to the candidate
            new_day = new_day_info.get("day")
            if new_day is not None:
                session["days_covered"].add(int(new_day))

            # An advance delivers a brand-new opening question for the new day to the candidate,
            # so the interview MUST NOT terminate on this turn before the candidate answers it.
            is_done = False
        else:
            # Follow-up: Stay on current day, ensure current day is in days_covered
            cur_day = current_day_info.get("day")
            if cur_day is not None:
                session["days_covered"].add(int(cur_day))
            llm_question = action_dict["question"]

            # Evaluate termination condition: ONLY terminate if 8+ questions asked AND 4+ distinct days covered
            is_done = (
                session["questions_asked"] >= 8 and
                len(session["days_covered"]) >= 4
            )

        # 6. Append LLM's question to transcript as assistant turn
        session["transcript"].append({"role": "assistant", "content": llm_question})

        if is_done:
            # Build list of curriculum day dicts actually probed (for the feedback LLM call)
            probed_days = []
            for spot in session["ranked_weak_spots"]:
                if int(spot.get("day", -1)) in session["days_covered"]:
                    probed_days.append(spot)

            # DEDICATED final LLM call over the full transcript — per AGENTS.md requirement
            feedback_dict = llm.generate_interview_feedback(
                transcript=session["transcript"],
                candidate_profile=session["candidate"],
                probed_days=probed_days,
            )

            from models import Feedback
            return InterviewResponse(
                reply="Interview complete. Thank you for your time — here's your feedback.",
                done=True,
                feedback=Feedback(**feedback_dict),
            )
        else:
            return InterviewResponse(
                reply=llm_question,
                done=False
            )

    else:
        raise HTTPException(
            status_code=400,
            detail="Request payload must include either 'candidate' or 'message'.",
        )
