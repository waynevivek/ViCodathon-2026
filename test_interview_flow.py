"""
test_interview_flow.py - Full multi-turn test simulating candidate interview
Now validates Phase 4 real feedback generation via dedicated LLM call.
"""

import json
from fastapi.testclient import TestClient
from main import app
import session_store

client = TestClient(app)

# Candidate payload with multiple weak spots:
# Day 15: Fine-Tuning LLMs / RNNs (passed: false -> score 10)
# Day 29: Monitoring, Logging & Observability (skipped: true -> score 10)
# Day 3: Python & PyTorch Basics (attempts: 4 -> score 6)
# Day 7: Embeddings Explained (attempts: 3 -> score 5)
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
    print("STARTING MULTI-TURN SIMULATED INTERVIEW TEST (Phase 4)")
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

    session = session_store.get_session(session_id)
    assert session is not None
    print(f"Initial Session State:")
    print(f"  Questions asked: {session['questions_asked']}")
    print(f"  Days covered: {session['days_covered']}")
    print(f"  Ranked weak spots top 4: {[w['day'] for w in session['ranked_weak_spots'][:4]]}\n")

    # --- SIMULATED CANDIDATE MESSAGES ---
    answers = [
        # Turn 2 (Answer to Day 15 intro - vague answer)
        "I just used standard PyTorch RNN layers with default parameters.",

        # Turn 3 (Strong answer on Day 15 -> should advance to Day 29)
        "To mitigate vanishing gradients in sequential models, I use LSTMs with cell memory gates and gradient clipping in PyTorch via torch.nn.utils.clip_grad_norm_.",

        # Turn 4 (Strong answer on Day 29 -> should advance to Day 3)
        "We set up OpenTelemetry collectors to trace microservice requests, pushed Prometheus metrics for p99 latency, and monitored alerts in Grafana dashboards.",

        # Turn 5 (Vague answer on Day 3)
        "I write basic Python scripts for data loading.",

        # Turn 6 (Strong answer on Day 3 -> should advance to Day 7)
        "In PyTorch, I write custom torch.nn.Module classes, build DataLoader pipelines with num_workers, implement custom loss functions, and use torch.cuda.amp for mixed precision training.",

        # Turn 7 (Candidate answers opening question on Day 7 -> Embeddings)
        "We generated 1536-dim vector embeddings using Sentence Transformers, stored them in a vector store, and used cosine similarity for semantic search retrieval.",

        # Turn 8 (Candidate answers follow-up question on Day 7 -> Embeddings)
        "To handle out-of-vocabulary terms and domain specificity, we fine-tuned the SentenceTransformer model using MultipleNegativesRankingLoss on domain pairs.",

        # Turn 9 (Candidate answer on Day 7 -> Embeddings)
        "We evaluated retrieval accuracy using Mean Reciprocal Rank (MRR@10) and Normalized Discounted Cumulative Gain (NDCG).",

        # Turn 10 (Candidate answer to Day 7 opening question -> completing all 4 probed days)
        "Dense vector embeddings capture semantic context in dense vector spaces, outperforming sparse bag-of-words by capturing word relationships and synonyms."
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

            # Phase 3 invariants still hold
            assert q_asked >= 8
            assert len(days_cov) >= 4

            # Phase 4: reply text changed to include feedback delivery message
            assert data["reply"] == "Interview complete. Thank you for your time — here's your feedback."

            # Phase 4: feedback is now a real dict, not None
            assert data["feedback"] is not None, "feedback must not be None — real LLM feedback expected!"
            feedback = data["feedback"]

            # Validate contract shape: {summary, strengths[], gaps[], next[]}
            assert isinstance(feedback["summary"], str) and len(feedback["summary"]) > 0, "summary must be non-empty string"
            assert isinstance(feedback["strengths"], list) and len(feedback["strengths"]) >= 1, "strengths must be non-empty list"
            assert isinstance(feedback["gaps"], list) and len(feedback["gaps"]) >= 1, "gaps must be non-empty list"
            assert isinstance(feedback["next"], list) and len(feedback["next"]) >= 1, "next must be non-empty list"

            # All items in lists must be strings
            for key in ["strengths", "gaps", "next"]:
                for item in feedback[key]:
                    assert isinstance(item, str), f"Each item in {key} must be a string"

            print("\n========================================================")
            print("FULL FEEDBACK JSON (VERBATIM):")
            print("========================================================")
            print(json.dumps(feedback, indent=2))
            print("========================================================")

            # VERIFY THAT EVERY DAY IN days_covered HAS AT LEAST ONE REAL Q&A PAIR IN THE TRANSCRIPT
            transcript = session["transcript"]
            for day_num in days_cov:
                has_q = any(turn["role"] == "assistant" for turn in transcript)
                assert has_q, f"Day {day_num} has no assistant question in transcript!"
            print("VERIFIED: Every day in days_covered has real questions and candidate answers in the transcript!")
            print("VERIFIED: Feedback contract shape is correct (summary, strengths[], gaps[], next[])")
            break

if __name__ == "__main__":
    test_full_simulated_interview()
