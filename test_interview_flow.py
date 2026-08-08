"""
test_interview_flow.py - Full multi-turn test simulating candidate interview
"""

import json
from fastapi.testclient import TestClient
from main import app
import session_store

client = TestClient(app)

# Candidate payload with multiple weak spots:
# Day 7: Embeddings Explained (attempts: 3 -> score 5)
# Day 29: Monitoring, Logging & Observability (skipped: true -> score 10)
# Day 15: Fine-Tuning LLMs (passed: false -> score 10)
# Day 3: Python & PyTorch (attempts: 4 -> score 6)
CANDIDATE_PAYLOAD = {
    "member": {
        "id": "CAND-001",
        "name": "Sarah Johnson",
        "jobRole": "Senior Data Engineer",
        "yearsExperience": 9,
        "education": "MS Computer Science",
        "status": "COMPLETED"
    },
    "missions": [
        {"day": 7, "title": "Embeddings Explained", "passed": True, "attempts": 3},
        {"day": 29, "title": "Monitoring, Logging & Observability", "skipped": True},
        {"day": 15, "title": "Fine-Tuning LLMs", "passed": False, "attempts": 1},
        {"day": 3, "title": "Python & PyTorch Basics", "passed": True, "attempts": 4}
    ],
    "signals": {"commitDays": 28, "missionsCompleted": 30, "missionsFirstTry": 20}
}


def test_full_simulated_interview():
    session_store.clear_sessions()
    session_id = "test-session-multi-turn"

    print("\n========================================================")
    print("STARTING MULTI-TURN SIMULATED INTERVIEW TEST")
    print("========================================================\n")

    # --- TURN 1 ---
    print("--- TURN 1: Candidate Initialization ---")
    t1_payload = {
        "sessionId": session_id,
        "candidate": CANDIDATE_PAYLOAD
    }
    res1 = client.post("/api/interview", json=t1_payload)
    assert res1.status_code == 200
    data1 = res1.json()
    print(f"Reply: {data1['reply']}")
    print(f"Done: {data1['done']}\n")
    assert data1["done"] is False
    assert "Embeddings Explained" in data1["reply"] or "Monitoring" in data1["reply"] or "Welcome" in data1["reply"]

    session = session_store.get_session(session_id)
    assert session is not None
    print(f"Initial Session State:")
    print(f"  Questions asked: {session['questions_asked']}")
    print(f"  Days covered: {session['days_covered']}")
    print(f"  Ranked weak spots top 4: {[w['day'] for w in session['ranked_weak_spots'][:4]]}\n")

    # --- SIMULATED CANDIDATE MESSAGES ---
    # We alternate between weak/shallow answers (should trigger followup) and strong answers (should trigger advance)
    answers = [
        # Turn 2 (Answer to Turn 1 intro - vague answer on embeddings)
        "I just used default cosine similarity functions from scikit-learn without tuning.",
        
        # Turn 3 (Strong answer on embeddings -> should advance)
        "We generated 1536-dim vector embeddings using OpenAI text-embedding-3-small, indexed them in Qdrant HNSW index, and optimized cosine distance for RAG retrieval with sub-50ms latency.",
        
        # Turn 4 (Vague answer on observability)
        "I logged errors to console using print statements.",
        
        # Turn 5 (Strong answer on observability -> should advance)
        "We set up OpenTelemetry collectors to trace API requests across microservices, pushed Prometheus metrics for latency p99, and created Grafana dashboards with alert thresholds.",
        
        # Turn 6 (Weak answer on fine-tuning)
        "I tried fine-tuning once with HuggingFace default script but it ran out of memory.",
        
        # Turn 7 (Strong answer on fine-tuning -> should advance)
        "We used LoRA with QLoRA 4-bit quantization on Llama-3, using PEFT and Unsloth, keeping rank r=16 and alpha=32, training on 8x A100 GPUs with gradient accumulation.",
        
        # Turn 8 (Strong answer on PyTorch -> should advance to 4th day)
        "In PyTorch, I write custom torch.nn.Module classes, use DataLoader with num_workers, implementation custom loss functions, and use torch.cuda.amp for mixed precision training.",

        # Turn 9 (Final answer -> completes 8 questions & 4 distinct days)
        "We optimized gradient memory by zeroing gradients efficiently and using gradient checkpointing."
    ]

    for turn_idx, answer in enumerate(answers, start=2):
        print(f"--- TURN {turn_idx}: Candidate Message ---")
        print(f"Candidate: \"{answer}\"")

        res = client.post("/api/interview", json={"sessionId": session_id, "message": answer})
        assert res.status_code == 200
        data = res.json()

        session = session_store.get_session(session_id)
        q_asked = session['questions_asked']
        days_cov = session['days_covered']
        cur_day_info = session_store.get_current_day_info(session)

        print(f"Interviewer Reply: \"{data['reply']}\"")
        print(f"Status: done={data['done']}")
        print(f"Session State -> questions_asked: {q_asked}, days_covered: {list(days_cov)}, current_day: Day {cur_day_info.get('day')}\n")

        if data["done"]:
            print("========================================================")
            print("INTERVIEW TERMINATED SUCCESSFULLY!")
            print(f"Final questions_asked: {q_asked}")
            print(f"Final days_covered count: {len(days_cov)} ({days_cov})")
            print(f"Final Reply: {data['reply']}")
            print("========================================================")
            assert q_asked >= 8
            assert len(days_cov) >= 4
            assert data["reply"] == "Interview complete. Generating feedback..."
            assert data["feedback"] is None
            break

if __name__ == "__main__":
    test_full_simulated_interview()
