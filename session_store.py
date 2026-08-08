"""
session_store.py - In-memory session management for AI Interview Agent

Stores active interview sessions keyed by sessionId.
Tracks candidate profile, ranked weak spots, questions asked counter,
and distinct curriculum days covered set.
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

    session_data = {
        "sessionId": session_id,
        "candidate": c_dict,
        "ranked_weak_spots": ranked_weak_spots,
        "questions_asked": 0,
        "days_covered": set(),  # Set of integer day numbers
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


def delete_session(session_id: str) -> bool:
    """Deletes a session from memory."""
    if session_id in _SESSIONS:
        del _SESSIONS[session_id]
        return True
    return False


def clear_sessions() -> None:
    """Clears all sessions from memory (used for testing)."""
    _SESSIONS.clear()
