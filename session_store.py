"""
session_store.py - In-memory session management for AI Interview Agent

Stores active interview sessions keyed by sessionId.
Tracks candidate profile, ranked weak spots, current probed day index,
questions asked counter, distinct curriculum days covered set, and transcript.
"""

import time
from typing import Dict, Any, Optional, Set, List

# Global in-memory session store dictionary keyed by sessionId
_SESSIONS: Dict[str, Dict[str, Any]] = {}


def create_session(
    session_id: str,
    candidate: Any,
    ranked_weak_spots: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Initializes and stores a new interview session in memory.
    """
    # Convert candidate pydantic model to dict if needed
    if hasattr(candidate, "model_dump"):
        c_dict = candidate.model_dump()
    elif isinstance(candidate, dict):
        c_dict = candidate
    else:
        c_dict = dict(candidate)

    days_covered: Set[int] = set()
    current_day_index = 0
    if ranked_weak_spots:
        initial_day = ranked_weak_spots[0].get("day")
        if initial_day is not None:
            days_covered.add(int(initial_day))

    session_data = {
        "sessionId": session_id,
        "candidate": c_dict,
        "ranked_weak_spots": ranked_weak_spots,
        "current_day_index": current_day_index,
        "questions_asked": 0,
        "days_covered": days_covered,  # Set of integer day numbers that have received a question
        "transcript": [],
        "created_at": time.time(),
    }
    _SESSIONS[session_id] = session_data
    return session_data


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an existing interview session by sessionId."""
    return _SESSIONS.get(session_id)


def update_session(session_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates fields of an existing interview session."""
    session = _SESSIONS.get(session_id)
    if session:
        session.update(updates)
        return session
    return None


def get_current_day_info(session: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieves current weak spot dictionary for the session."""
    ranked = session.get("ranked_weak_spots", [])
    idx = session.get("current_day_index", 0)
    if 0 <= idx < len(ranked):
        return ranked[idx]
    elif ranked:
        return ranked[0]
    return {"day": 1, "title": "AI Fundamentals", "tools": [], "objectives": []}


def advance_day_pointer(session: Dict[str, Any], suggested_next_day: Optional[int] = None) -> None:
    """
    Advances session day pointer to the next weak spot.
    Code is authoritative: checks if suggested_next_day exists in ranked_weak_spots and is unprobed.
    Otherwise advances to the next unprobed day in ranked_weak_spots order.
    
    NOTE: Does NOT automatically add the new day to days_covered here.
    Days are added to days_covered ONLY when a question is actually generated and returned for that day.
    """
    ranked = session.get("ranked_weak_spots", [])
    days_covered: Set[int] = session.get("days_covered", set())

    # Try suggested_next_day if provided
    if suggested_next_day is not None:
        for idx, spot in enumerate(ranked):
            spot_day = int(spot.get("day"))
            if spot_day == int(suggested_next_day) and spot_day not in days_covered:
                session["current_day_index"] = idx
                return

    # Fallback to next unprobed day in ranked list
    for idx, spot in enumerate(ranked):
        spot_day = int(spot.get("day"))
        if spot_day not in days_covered:
            session["current_day_index"] = idx
            return

    # If all ranked spots have been covered, move to next index if possible
    next_idx = session.get("current_day_index", 0) + 1
    if next_idx < len(ranked):
        session["current_day_index"] = next_idx


def delete_session(session_id: str) -> bool:
    """Deletes a session from memory."""
    if session_id in _SESSIONS:
        del _SESSIONS[session_id]
        return True
    return False


def clear_sessions() -> None:
    """Clears all sessions from memory (used for testing)."""
    _SESSIONS.clear()
