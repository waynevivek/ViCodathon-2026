"""
test_ranking.py - Unit tests for ranking engine and curriculum day join
"""

import json
from ranking import load_curriculum, rank_weak_spots, calculate_mission_score


def test_calculate_mission_score():
    # Skipped + passed False -> 20 pts
    assert calculate_mission_score({"day": 29, "skipped": True, "passed": False}) == 20
    # Failed + 4 attempts -> 10 + 5 + 1 = 16 pts
    assert calculate_mission_score({"day": 15, "passed": False, "attempts": 4}) == 16
    # Passed + 3 attempts -> 5 pts
    assert calculate_mission_score({"day": 22, "passed": True, "attempts": 3}) == 5
    # Passed 1st try -> 0 pts
    assert calculate_mission_score({"day": 7, "passed": True, "attempts": 1}) == 0


def test_rank_weak_spots_day_integer_join():
    curriculum = load_curriculum("curriculum.json")

    sarah = {
        "member": {"id": "CAND-001", "name": "Sarah Johnson"},
        "missions": [
            {"day": 7, "title": "Embeddings 101 (Mismatch String)", "passed": True, "attempts": 1},
            {"day": 15, "title": "RNNs & Sequence Data", "passed": False, "attempts": 4},
            {"day": 22, "title": "Structured JSON Generation", "passed": True, "attempts": 3},
            {"day": 29, "title": "Monitoring & Observability", "skipped": True, "passed": False}
        ]
    }

    weak_spots = rank_weak_spots(sarah, curriculum)

    assert len(weak_spots) == 4

    # 1. Top weak spot must be Day 29 (score 20)
    top = weak_spots[0]
    assert top["day"] == 29
    assert top["score"] == 20
    assert top["title"] == "Monitoring, Logging & Observability"  # Matches curriculum.json title

    # 2. Second weak spot must be Day 15 (score 16)
    second = weak_spots[1]
    assert second["day"] == 15
    assert second["score"] == 16
    assert second["title"] == "Recurrent Neural Networks & LSTMs"  # Matches curriculum.json title

    # 3. Third weak spot must be Day 22 (score 5)
    third = weak_spots[2]
    assert third["day"] == 22
    assert third["score"] == 5

    # 4. Day 7 title must match curriculum.json ("Embeddings Explained"), ignoring candidate's "Embeddings 101"
    fourth = weak_spots[3]
    assert fourth["day"] == 7
    assert fourth["title"] == "Embeddings Explained"

    print("All ranking and integer-day join tests passed successfully!")


if __name__ == "__main__":
    test_calculate_mission_score()
    test_rank_weak_spots_day_integer_join()
