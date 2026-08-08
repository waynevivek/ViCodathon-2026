"""
test_llm_fallback.py - Unit test for llm.py structured output parsing, retry logic, and fallback.
"""

from unittest.mock import patch, MagicMock
import llm


def test_parse_and_validate_action_valid():
    raw_json = '{"action": "followup", "question": "Can you elaborate on attention mechanisms?"}'
    parsed = llm.parse_and_validate_action(raw_json)
    assert parsed is not None
    assert parsed["action"] == "followup"
    assert parsed["question"] == "Can you elaborate on attention mechanisms?"
    assert parsed["next_day"] is None


def test_parse_and_validate_action_with_markdown_fences():
    raw_json = '```json\n{"action": "advance", "question": "What is PyTorch DataLoader?", "next_day": 3}\n```'
    parsed = llm.parse_and_validate_action(raw_json)
    assert parsed is not None
    assert parsed["action"] == "advance"
    assert parsed["question"] == "What is PyTorch DataLoader?"
    assert parsed["next_day"] == 3


def test_parse_and_validate_action_malformed_json():
    raw_json = '{"action": "followup", "question": "Unclosed quote...}'
    parsed = llm.parse_and_validate_action(raw_json)
    assert parsed is None


def test_parse_and_validate_action_invalid_action():
    raw_json = '{"action": "invalid_action_type", "question": "Some question?"}'
    parsed = llm.parse_and_validate_action(raw_json)
    assert parsed is None


def test_parse_and_validate_action_missing_question():
    raw_json = '{"action": "followup", "question": ""}'
    parsed = llm.parse_and_validate_action(raw_json)
    assert parsed is None


def test_generate_interview_action_fallback_on_double_failure():
    """
    Tests that if both Attempt 1 and Attempt 2 fail (e.g. malformed responses or API errors),
    generate_interview_action cleanly returns the deterministic fallback action.
    """
    mock_choice = MagicMock()
    mock_choice.message.content = "INVALID NON-JSON RESPONSE FROM LLM"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("llm.get_groq_client", return_value=mock_client):
        current_day = {"day": 7, "title": "Embeddings Explained"}
        result = llm.generate_interview_action(
            candidate_summary="Sarah Johnson",
            current_day_info=current_day,
            transcript=[],
            candidate_message="I used embeddings."
        )

        assert result is not None
        assert result["action"] in ["advance", "followup"]
        assert "Embeddings Explained" in result["question"] or "Day 7" in result["question"]
        print("\nFallback test passed: successfully returned deterministic fallback on double failure.")


if __name__ == "__main__":
    test_parse_and_validate_action_valid()
    test_parse_and_validate_action_with_markdown_fences()
    test_parse_and_validate_action_malformed_json()
    test_parse_and_validate_action_invalid_action()
    test_parse_and_validate_action_missing_question()
    test_generate_interview_action_fallback_on_double_failure()
    print("All llm.py fallback unit tests passed!")
