"""
ranking.py - Candidate Weak-Spot Ranking Engine

SCORING RULE FOR WEAK-SPOT DAYS:
Each candidate mission is joined with curriculum data strictly by integer `day` number.
Missions are evaluated for struggle signals using the following scoring rule:
- passed == False : +10 points (candidate failed or did not pass the mission)
- skipped == True : +10 points (candidate skipped the mission entirely)
- attempts >= 3   : +5 points + max(0, attempts - 3) points (high attempt count penalty)

A day's total struggle score is the sum of these points.
Days with score > 0 are classified as weak spots.
All days are ranked by:
1. Struggle score (descending)
2. Attempt count (descending, as primary tie-breaker)
3. Day integer (ascending, for deterministic ordering)

CRITICAL: Joins between candidate missions and curriculum data MUST use integer `day` field ONLY.
Never match or compare on title strings.
"""

import json
from typing import Dict, List, Any, Union, Optional


def load_curriculum(filepath: str = "curriculum.json") -> Dict[str, Any]:
    """Loads curriculum reference data from JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_mission_score(mission: Dict[str, Any]) -> int:
    """
    Computes struggle score for a single candidate mission.
    Struggle signals:
    - passed: False (+10)
    - skipped: True (+10)
    - attempts >= 3 (+5 + (attempts - 3))
    """
    score = 0
    passed = mission.get("passed")
    skipped = mission.get("skipped", False)
    attempts = mission.get("attempts") or 0

    if passed is False:
        score += 10

    if skipped is True:
        score += 10

    if attempts >= 3:
        score += 5 + max(0, attempts - 3)

    return score


def rank_weak_spots(
    candidate_data: Union[Dict[str, Any], Any],
    curriculum_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Joins candidate missions with curriculum days strictly by integer `day` field,
    calculates struggle scores, and returns a sorted list of weak-spot days.
    """
    # Convert candidate pydantic model to dict if needed
    if hasattr(candidate_data, "model_dump"):
        c_dict = candidate_data.model_dump()
    elif isinstance(candidate_data, dict):
        c_dict = candidate_data
    else:
        c_dict = dict(candidate_data)

    # Index curriculum days strictly by integer day number
    curriculum_days: Dict[int, Dict[str, Any]] = {
        int(d["day"]): d for d in curriculum_data.get("days", [])
    }

    candidate_missions = c_dict.get("missions", [])

    weak_spots: List[Dict[str, Any]] = []

    for mission in candidate_missions:
        day_num = int(mission.get("day"))
        curriculum_info = curriculum_days.get(day_num)

        if not curriculum_info:
            continue

        score = calculate_mission_score(mission)
        attempts = mission.get("attempts") or 0

        weak_spots.append({
            "day": day_num,
            "title": curriculum_info["title"],  # Official title from curriculum.json
            "type": curriculum_info.get("type", "UNKNOWN"),
            "tools": curriculum_info.get("tools", []),
            "objectives": curriculum_info.get("objectives", []),
            "score": score,
            "attempts": attempts,
            "passed": mission.get("passed"),
            "skipped": mission.get("skipped", False),
            "candidate_title": mission.get("title")  # kept for audit, not used for matching
        })

    # Sort weak spots by score (descending), attempts (descending), day (ascending)
    weak_spots.sort(key=lambda x: (-x["score"], -x["attempts"], x["day"]))

    return weak_spots
