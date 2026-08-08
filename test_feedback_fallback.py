"""
test_feedback_fallback.py - Tests feedback generation fallback path.
Verifies that when the LLM returns malformed feedback JSON (both attempts),
the system gracefully falls back to a valid, contract-shaped generic feedback object.
"""

from unittest.mock import patch, MagicMock
import llm


def test_parse_and_validate_feedback_valid():
    """Valid feedback JSON parses correctly."""
    raw = '{"summary": "Good interview.", "strengths": ["Strong on embeddings"], "gaps": ["Weak on RNNs"], "next": ["Study LSTMs"]}'
    parsed = llm.parse_and_validate_feedback(raw)
    assert parsed is not None
    assert parsed["summary"] == "Good interview."
    assert parsed["strengths"] == ["Strong on embeddings"]
    assert parsed["gaps"] == ["Weak on RNNs"]
    assert parsed["next"] == ["Study LSTMs"]
    print("PASS: Valid feedback JSON parsed correctly.")


def test_parse_and_validate_feedback_with_markdown_fences():
    """Feedback wrapped in markdown fences still parses."""
    raw = '```json\n{"summary": "OK.", "strengths": ["A"], "gaps": ["B"], "next": ["C"]}\n```'
    parsed = llm.parse_and_validate_feedback(raw)
    assert parsed is not None
    assert parsed["summary"] == "OK."
    print("PASS: Feedback with markdown fences parsed correctly.")


def test_parse_and_validate_feedback_missing_key():
    """Missing 'next' key causes validation failure."""
    raw = '{"summary": "Test", "strengths": ["A"], "gaps": ["B"]}'
    parsed = llm.parse_and_validate_feedback(raw)
    assert parsed is None
    print("PASS: Missing key correctly rejected.")


def test_parse_and_validate_feedback_empty_summary():
    """Empty summary causes validation failure."""
    raw = '{"summary": "", "strengths": ["A"], "gaps": ["B"], "next": ["C"]}'
    parsed = llm.parse_and_validate_feedback(raw)
    assert parsed is None
    print("PASS: Empty summary correctly rejected.")


def test_parse_and_validate_feedback_non_string_list():
    """Non-string items in list cause validation failure."""
    raw = '{"summary": "OK", "strengths": [1, 2], "gaps": ["B"], "next": ["C"]}'
    parsed = llm.parse_and_validate_feedback(raw)
    assert parsed is None
    print("PASS: Non-string list items correctly rejected.")


def test_parse_and_validate_feedback_malformed_json():
    """Malformed JSON returns None."""
    raw = 'This is not valid JSON at all!!!'
    parsed = llm.parse_and_validate_feedback(raw)
    assert parsed is None
    print("PASS: Malformed JSON correctly rejected.")


def test_generate_interview_feedback_fallback_on_double_failure():
    """
    Tests that if both Attempt 1 and Attempt 2 return malformed feedback,
    generate_interview_feedback cleanly returns the generic fallback with correct shape.
    """
    mock_choice = MagicMock()
    mock_choice.message.content = "INVALID NON-JSON GARBAGE RESPONSE"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("llm.get_groq_client", return_value=mock_client):
        result = llm.generate_interview_feedback(
            transcript=[
                {"role": "assistant", "content": "Tell me about embeddings."},
                {"role": "user", "content": "I used Word2Vec."},
            ],
            candidate_profile={
                "member": {"name": "Test User", "jobRole": "Engineer"},
                "missions": [],
                "signals": {},
            },
            probed_days=[
                {"day": 7, "title": "Embeddings Explained", "objectives": ["Understand embeddings"]},
            ],
        )

        # Must return valid contract shape
        assert result is not None
        assert isinstance(result["summary"], str) and len(result["summary"]) > 0
        assert isinstance(result["strengths"], list) and len(result["strengths"]) >= 1
        assert isinstance(result["gaps"], list) and len(result["gaps"]) >= 1
        assert isinstance(result["next"], list) and len(result["next"]) >= 1

        # Must be identifiable as degraded output via [Auto-generated] prefix
        assert "[Auto-generated]" in result["summary"], \
            "Fallback summary must contain '[Auto-generated]' for internal identification"

        print(f"\nFallback test PASSED. Returned shape:")
        import json
        print(json.dumps(result, indent=2))


def test_generate_interview_feedback_fallback_on_api_exception():
    """
    Tests that if the Groq API raises exceptions on both attempts,
    the fallback is still returned cleanly.
    """
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API connection failed")

    with patch("llm.get_groq_client", return_value=mock_client):
        result = llm.generate_interview_feedback(
            transcript=[{"role": "assistant", "content": "Q?"}, {"role": "user", "content": "A."}],
            candidate_profile={"member": {"name": "Test"}, "missions": [], "signals": {}},
            probed_days=[{"day": 1, "title": "Test Day", "objectives": []}],
        )

        assert result is not None
        assert "[Auto-generated]" in result["summary"]
        assert isinstance(result["strengths"], list)
        assert isinstance(result["gaps"], list)
        assert isinstance(result["next"], list)
        print("PASS: API exception fallback returned valid contract shape.")


if __name__ == "__main__":
    test_parse_and_validate_feedback_valid()
    test_parse_and_validate_feedback_with_markdown_fences()
    test_parse_and_validate_feedback_missing_key()
    test_parse_and_validate_feedback_empty_summary()
    test_parse_and_validate_feedback_non_string_list()
    test_parse_and_validate_feedback_malformed_json()
    test_generate_interview_feedback_fallback_on_double_failure()
    test_generate_interview_feedback_fallback_on_api_exception()
    print("\n========================================================")
    print("All feedback fallback tests passed!")
    print("========================================================")
