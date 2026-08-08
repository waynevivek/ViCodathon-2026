"""
test_app.py - Integration tests for FastAPI endpoint Turn 1 intake & Turn 2+ session validation
"""

from fastapi.testclient import TestClient
from main import app
import session_store

client = TestClient(app)


def test_turn1_and_turn2_flow():
    session_store.clear_sessions()

    # Turn 1 payload with candidate Sarah Johnson
    turn1_payload = {
        "sessionId": "test-session-123",
        "candidate": {
            "member": {
                "id": "CAND-001",
                "name": "Sarah Johnson",
                "jobRole": "Senior Data Engineer",
                "yearsExperience": 9,
                "education": "MS Computer Science",
                "status": "COMPLETED"
            },
            "missions": [
                { "day": 7, "title": "Embeddings 101", "passed": True, "attempts": 1 },
                { "day": 15, "title": "RNNs & Sequence Data", "passed": False, "attempts": 4 },
                { "day": 22, "title": "Structured JSON Generation", "passed": True, "attempts": 3 },
                { "day": 29, "title": "Monitoring & Observability", "skipped": True, "passed": False }
            ],
            "signals": { "commitDays": 28, "missionsCompleted": 30, "missionsFirstTry": 20 }
        }
    }

    # 1. Turn 1 test
    res1 = client.post("/api/interview", json=turn1_payload)
    assert res1.status_code == 200, f"Turn 1 failed: {res1.text}"
    body1 = res1.json()
    assert body1["done"] is False
    assert "Day 29: Monitoring, Logging & Observability" in body1["reply"], f"Unexpected reply: {body1['reply']}"

    # Verify session store state
    session = session_store.get_session("test-session-123")
    assert session is not None
    assert session["questions_asked"] == 0
    assert session["days_covered"] == {29}
    assert len(session["ranked_weak_spots"]) == 4
    assert session["ranked_weak_spots"][0]["day"] == 29

    # 2. Turn 2+ test with EXISTING session
    turn2_valid_payload = {
        "sessionId": "test-session-123",
        "message": "I set up Prometheus metrics and Grafana dashboards for monitoring."
    }
    res2 = client.post("/api/interview", json=turn2_valid_payload)
    assert res2.status_code == 200
    body2 = res2.json()
    assert body2["done"] is False
    assert isinstance(body2["reply"], str) and len(body2["reply"]) > 0

    # 3. Turn 2+ test with UNKNOWN session
    turn2_unknown_payload = {
        "sessionId": "non-existent-session-999",
        "message": "Hello?"
    }
    res3 = client.post("/api/interview", json=turn2_unknown_payload)
    assert res3.status_code == 200
    body3 = res3.json()
    assert body3["done"] is True
    assert body3["reply"] == "Session not found, please start a new interview."

    print("All integration tests passed successfully!")


if __name__ == "__main__":
    test_turn1_and_turn2_flow()
