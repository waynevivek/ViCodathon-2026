"""
llm.py - Groq LLM integration and dynamic action parser for AI Technical Interview Agent.

Model: llama-3.3-70b-versatile
API Key: Read strictly from GROQ_API_KEY environment variable (.env).
Enforces structured JSON actions:
- {"action": "followup", "question": "..."}
- {"action": "advance", "question": "...", "next_day": <int>}

Includes retry-once-then-fallback mechanism for resilience against malformed LLM responses.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)

# Primary model name per specification
MODEL_NAME = "llama-3.3-70b-versatile"


def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is missing.")
    return Groq(api_key=api_key)


def parse_and_validate_action(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Parses and validates raw LLM output into structured action dictionary.
    Expected structure:
    {"action": "followup" | "advance", "question": "non-empty string", "next_day": Optional[int]}
    """
    if not raw_text:
        return None

    cleaned = raw_text.strip()
    # Remove markdown backticks if present
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    action = data.get("action")
    question = data.get("question")

    if action not in ["followup", "advance"]:
        return None

    if not isinstance(question, str) or not question.strip():
        return None

    next_day = data.get("next_day")
    if next_day is not None:
        try:
            next_day = int(next_day)
        except (ValueError, TypeError):
            next_day = None

    return {
        "action": action,
        "question": question.strip(),
        "next_day": next_day
    }


def construct_prompt_messages(
    candidate_summary: str,
    current_day_info: Dict[str, Any],
    transcript: List[Dict[str, str]],
    candidate_message: str,
    strict_retry: bool = False
) -> List[Dict[str, str]]:
    """
    Constructs the system and user prompt messages for evaluating candidate's latest answer.
    """
    system_content = (
        "You are an expert AI Technical Interviewer conducting a dynamic interview based on a 31-day AI curriculum.\n"
        "Your goal is to probe the candidate's understanding of key technical concepts, focusing on their weak-spot days.\n\n"
        "You MUST respond ONLY with a raw JSON object (no markdown code blocks, no ```json formatting, no conversational text).\n"
        "The JSON MUST match one of the following schemas:\n\n"
        '1. {"action": "followup", "question": "<your technical follow-up question>"}\n'
        '   Use "followup" if the candidate\'s latest answer was shallow, vague, incomplete, or incorrect on the current topic.\n\n'
        '2. {"action": "advance", "question": "Advancing to next topic", "next_day": <integer_day_number_or_null>}\n'
        '   Use "advance" if the candidate demonstrated clear understanding or if follow-ups on the current topic are finished.\n\n'
        "Rules for questions:\n"
        "- Base follow-up questions directly on what the candidate just said in their latest message.\n"
        "- Ensure questions are technical, precise, and relevant to the day's objectives and tools.\n"
    )

    if strict_retry:
        system_content += (
            "\nCRITICAL: Your previous response failed to parse as valid JSON. "
            "Respond ONLY with valid JSON in the exact schema above. Do NOT include markdown fences or preamble."
        )

    # Format current day info
    day_num = current_day_info.get("day", "N/A")
    day_title = current_day_info.get("title", "N/A")
    tools = ", ".join(current_day_info.get("tools", []))
    objectives = "\n".join(f"- {obj}" for obj in current_day_info.get("objectives", []))

    user_content = (
        f"CANDIDATE PROFILE:\n{candidate_summary}\n\n"
        f"CURRENT PROBED TOPIC:\n"
        f"Day {day_num}: {day_title}\n"
        f"Tools: {tools}\n"
        f"Objectives:\n{objectives}\n\n"
        f"CONVERSATION TRANSCRIPT:\n"
    )

    for turn in transcript:
        role = "Interviewer" if turn.get("role") == "assistant" else "Candidate"
        user_content += f"{role}: {turn.get('content', '')}\n"

    user_content += f"\nLATEST CANDIDATE ANSWER:\n{candidate_message}\n\n"
    user_content += "Provide your structured JSON action now:"

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content}
    ]


def get_deterministic_fallback(
    current_day_info: Dict[str, Any],
    action_type: str = "advance"
) -> Dict[str, Any]:
    """
    Returns a safe, deterministic fallback action if LLM API calls fail twice.
    Prevents the interview from crashing or hanging on bad LLM responses.
    """
    day_num = current_day_info.get("day", 1)
    day_title = current_day_info.get("title", "AI Concepts")

    if action_type == "advance":
        return {
            "action": "advance",
            "question": f"Let's move forward to Day {day_num}: {day_title}. Could you explain your hands-on experience and core approach with this topic?",
            "next_day": None
        }
    else:
        return {
            "action": "followup",
            "question": f"Could you elaborate further on how you applied {day_title} in your project, specifically regarding the technical implementation details?",
            "next_day": None
        }


def generate_interview_action(
    candidate_summary: str,
    current_day_info: Dict[str, Any],
    transcript: List[Dict[str, str]],
    candidate_message: str
) -> Dict[str, Any]:
    """
    Calls Groq API to decide the next interview action (followup vs advance).
    Implements retry-once-then-fallback strategy.
    """
    client = get_groq_client()

    # --- ATTEMPT 1 ---
    try:
        messages = construct_prompt_messages(
            candidate_summary, current_day_info, transcript, candidate_message, strict_retry=False
        )
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        raw_output = response.choices[0].message.content
        parsed = parse_and_validate_action(raw_output)
        if parsed is not None:
            return parsed
    except Exception as e:
        logger.warning(f"Groq API call attempt 1 failed: {type(e).__name__}")

    # --- ATTEMPT 2 (RETRY ONCE WITH STRICT PROMPT REMINDER) ---
    try:
        messages = construct_prompt_messages(
            candidate_summary, current_day_info, transcript, candidate_message, strict_retry=True
        )
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        raw_output = response.choices[0].message.content
        parsed = parse_and_validate_action(raw_output)
        if parsed is not None:
            return parsed
    except Exception as e:
        logger.warning(f"Groq API call attempt 2 (retry) failed: {type(e).__name__}")

    # --- FALLBACK ---
    logger.warning("Using deterministic fallback action after failed LLM attempts.")
    return get_deterministic_fallback(current_day_info, action_type="advance")


def generate_opening_question(
    candidate_summary: str,
    new_day_info: Dict[str, Any],
    transcript: List[Dict[str, str]],
    candidate_message: str
) -> str:
    """
    Generates an opening technical question specifically tailored to a newly advanced curriculum day.
    Uses new_day_info (day number, title, tools, objectives) so the interviewer's question is ALWAYS
    about the new current day's topic, not stale data from the previous day.
    """
    client = get_groq_client()

    day_num = new_day_info.get("day", "N/A")
    day_title = new_day_info.get("title", "N/A")
    tools_list = new_day_info.get("tools", [])
    tools = ", ".join(tools_list) if tools_list else "core concepts"
    objectives_list = new_day_info.get("objectives", [])
    objectives = "\n".join(f"- {obj}" for obj in objectives_list)

    system_content = (
        "You are an expert AI Technical Interviewer.\n"
        "You are moving the candidate to a NEW topic in their 31-day AI curriculum.\n"
        "Your task is to generate a single, engaging, technical opening question for this NEW topic.\n\n"
        "CRITICAL RULES:\n"
        "- The question MUST be strictly about the NEW topic, its specific tools, and its curriculum objectives.\n"
        "- Do NOT ask about previous topics.\n"
        "- State the transition clearly (e.g., 'Now let's move to Day X: Title. ...').\n"
        "- You MUST respond ONLY with a raw JSON object: {\"question\": \"<your opening question>\"}.\n"
        "- Do NOT output markdown code blocks or preamble.\n"
    )

    user_content = (
        f"CANDIDATE PROFILE:\n{candidate_summary}\n\n"
        f"NEW TOPIC TO PROBE:\n"
        f"Day {day_num}: {day_title}\n"
        f"Tools: {tools}\n"
        f"Objectives:\n{objectives}\n\n"
        f"LAST CANDIDATE MESSAGE:\n{candidate_message}\n\n"
        f"Generate the opening question for Day {day_num}: {day_title} in JSON format now:"
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content}
    ]

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.3,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        raw_output = response.choices[0].message.content
        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        data = json.loads(cleaned.strip())
        q = data.get("question")
        if q and isinstance(q, str) and q.strip():
            return q.strip()
    except Exception as e:
        logger.warning(f"Groq API call for opening question failed: {type(e).__name__}")

    # Safe deterministic fallback for new day opening question
    return (
        f"Now let's move on to Day {day_num}: {day_title}. "
        f"Could you explain your practical experience and technical approach using {tools}?"
    )


def parse_and_validate_feedback(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Parses and validates raw LLM output into feedback dictionary.
    Expected structure:
    {"summary": "non-empty string", "strengths": ["...", ...], "gaps": ["...", ...], "next": ["...", ...]}
    All four keys must be present; summary must be non-empty; strengths/gaps/next must be lists of strings.
    """
    if not raw_text:
        return None

    cleaned = raw_text.strip()
    # Remove markdown backticks if present
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    summary = data.get("summary")
    strengths = data.get("strengths")
    gaps = data.get("gaps")
    next_steps = data.get("next")

    # Validate: summary must be non-empty string
    if not isinstance(summary, str) or not summary.strip():
        return None

    # Validate: strengths, gaps, next must be lists of strings
    for field_name, field_val in [("strengths", strengths), ("gaps", gaps), ("next", next_steps)]:
        if not isinstance(field_val, list):
            return None
        if not all(isinstance(item, str) for item in field_val):
            return None

    return {
        "summary": summary.strip(),
        "strengths": [s.strip() for s in strengths if s.strip()],
        "gaps": [g.strip() for g in gaps if g.strip()],
        "next": [n.strip() for n in next_steps if n.strip()],
    }


def get_feedback_fallback() -> Dict[str, Any]:
    """
    Returns a clearly-labeled generic feedback object when the LLM feedback call fails twice.
    This fallback is intentionally identifiable as degraded output — it uses a distinctive
    summary prefix "[Auto-generated]" so that internal logging/flagging can detect it if needed.
    The contract shape is fully valid, so the candidate-facing response is not broken.
    """
    return {
        "summary": "[Auto-generated] Interview completed. Detailed AI-generated feedback was unavailable for this session.",
        "strengths": ["Completed the full technical interview process."],
        "gaps": ["Detailed gap analysis was not generated for this session."],
        "next": ["Review the curriculum topics covered during the interview for further study."],
    }


def generate_interview_feedback(
    transcript: List[Dict[str, str]],
    candidate_profile: Dict[str, Any],
    probed_days: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    DEDICATED final LLM call to synthesize honest interview feedback over the FULL transcript.
    This is separate from the per-turn followup/advance function — per AGENTS.md requirement:
    "Feedback at the end must be generated by a dedicated final LLM call over the full transcript,
     not just the model's last reply reformatted."

    Args:
        transcript: Full session transcript (all Q&A turns across all probed days).
        candidate_profile: The candidate dict (member, missions, signals).
        probed_days: List of curriculum day dicts actually probed (with day, title, objectives, tools).

    Returns:
        Dict matching {"summary": str, "strengths": [str], "gaps": [str], "next": [str]}
    """
    client = get_groq_client()

    # Build candidate summary
    member = candidate_profile.get("member", {})
    cand_summary = (
        f"Name: {member.get('name', 'Candidate')}, "
        f"Role: {member.get('jobRole', 'N/A')}, "
        f"Experience: {member.get('yearsExperience', 'N/A')} years, "
        f"Education: {member.get('education', 'N/A')}"
    )

    # Build probed days summary
    days_summary_lines = []
    for day_info in probed_days:
        day_num = day_info.get("day", "?")
        title = day_info.get("title", "Unknown")
        objectives = day_info.get("objectives", [])
        obj_str = "; ".join(objectives) if objectives else "N/A"
        days_summary_lines.append(f"  Day {day_num}: {title} — Objectives: {obj_str}")
    days_summary = "\n".join(days_summary_lines)

    # Build full transcript text
    transcript_lines = []
    for turn in transcript:
        role = "Interviewer" if turn.get("role") == "assistant" else "Candidate"
        transcript_lines.append(f"{role}: {turn.get('content', '')}")
    transcript_text = "\n".join(transcript_lines)

    system_content = (
        "You are an expert AI Technical Interview evaluator.\n"
        "You have just observed a complete technical interview. Your task is to synthesize honest, specific feedback.\n\n"
        "CRITICAL RULES:\n"
        "- Ground EVERY claim in specific things the candidate actually said in the transcript.\n"
        "- Do NOT use generic filler like 'good communication skills' unless the transcript actually supports it.\n"
        "- If the candidate gave vague, off-topic, or shallow answers on a topic, state that explicitly in gaps.\n"
        "- Reference specific days, topics, and candidate statements when possible.\n"
        "- Be honest and constructive — do not inflate strengths or downplay weaknesses.\n\n"
        "You MUST respond ONLY with a raw JSON object (no markdown code blocks, no ```json, no preamble).\n"
        "The JSON MUST match this EXACT schema:\n"
        '{"summary": "<2-4 sentence overall assessment>", '
        '"strengths": ["<specific strength 1>", "<specific strength 2>", ...], '
        '"gaps": ["<specific gap 1>", "<specific gap 2>", ...], '
        '"next": ["<specific recommendation 1>", "<specific recommendation 2>", ...]}\n\n'
        "Each array must have at least 1 entry and at most 5 entries.\n"
        "Every entry must reference specific topics, days, or candidate statements from the interview.\n"
    )

    user_content = (
        f"CANDIDATE PROFILE:\n{cand_summary}\n\n"
        f"CURRICULUM DAYS PROBED:\n{days_summary}\n\n"
        f"FULL INTERVIEW TRANSCRIPT:\n{transcript_text}\n\n"
        "Based on the ENTIRE transcript above, generate your structured feedback JSON now:"
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    # --- ATTEMPT 1 ---
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        raw_output = response.choices[0].message.content
        parsed = parse_and_validate_feedback(raw_output)
        if parsed is not None:
            return parsed
        logger.warning("Feedback attempt 1: valid JSON but failed shape validation.")
    except Exception as e:
        logger.warning(f"Feedback Groq API call attempt 1 failed: {type(e).__name__}")

    # --- ATTEMPT 2 (RETRY WITH STRICT REMINDER) ---
    strict_system = system_content + (
        "\nCRITICAL: Your previous response failed validation. "
        "Respond ONLY with valid JSON matching EXACTLY: "
        '{"summary": "string", "strengths": ["string", ...], "gaps": ["string", ...], "next": ["string", ...]}. '
        "Do NOT include markdown fences, preamble, or extra keys."
    )
    strict_messages = [
        {"role": "system", "content": strict_system},
        {"role": "user", "content": user_content},
    ]

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=strict_messages,
            temperature=0.1,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        raw_output = response.choices[0].message.content
        parsed = parse_and_validate_feedback(raw_output)
        if parsed is not None:
            return parsed
        logger.warning("Feedback attempt 2: valid JSON but failed shape validation.")
    except Exception as e:
        logger.warning(f"Feedback Groq API call attempt 2 (retry) failed: {type(e).__name__}")

    # --- FALLBACK ---
    # Degraded output — clearly identifiable via "[Auto-generated]" prefix in summary.
    # This ensures the contract shape is always valid even if the LLM is unreachable.
    logger.warning("Using generic fallback feedback after failed LLM attempts.")
    return get_feedback_fallback()
