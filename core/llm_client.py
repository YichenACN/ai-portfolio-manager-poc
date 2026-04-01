import json
import os
import time
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _get_model(system_instruction: str = None) -> genai.GenerativeModel:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not set in environment")
    genai.configure(api_key=api_key)
    if system_instruction:
        return genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=system_instruction,
        )
    return genai.GenerativeModel(model_name=MODEL_NAME)


def _safe_response_text(response) -> str:
    """Extract text from a Gemini response, raising RuntimeError if invalid."""
    if response is None:
        raise RuntimeError("API returned no response")
    text = getattr(response, "text", None)
    if not text or not text.strip():
        raise RuntimeError("API returned an empty response")
    return text


def load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text()


def chat_intake(conversation_history: list[dict], system_prompt: str) -> str:
    """
    Send the full conversation history and return the next assistant response.
    conversation_history: list of {"role": "user"/"assistant", "content": "..."}
    """
    model = _get_model(system_instruction=system_prompt)

    gemini_contents = []
    for msg in conversation_history:
        role = "model" if msg["role"] == "assistant" else "user"
        gemini_contents.append({"role": role, "parts": [msg["content"]]})

    try:
        response = model.generate_content(gemini_contents)
        return _safe_response_text(response)
    except (ValueError, RuntimeError):
        raise
    except Exception as e:
        raise RuntimeError(f"AI service error during intake: {e}") from e


def structure_use_case(chat_history: list[dict], prompt_template: str) -> dict:
    """
    Given a completed intake conversation, extract structured fields as a dict.
    """
    model = _get_model()

    conversation_text = "\n".join(
        f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history
    )
    prompt = prompt_template.replace("{{CONVERSATION}}", conversation_text)

    try:
        response = model.generate_content(prompt)
        return _parse_json_response(_safe_response_text(response))
    except (ValueError, RuntimeError):
        raise
    except Exception as e:
        raise RuntimeError(f"AI service error during structuring: {e}") from e


def generate_summary(chat_history: list[dict]) -> str:
    """Generate a short plain-text summary of the intake conversation."""
    model = _get_model()
    conversation_text = "\n".join(
        f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history
    )
    prompt = (
        "Summarize the following AI use case intake conversation in 2-3 concise paragraphs. "
        "Focus on: the business problem, who is impacted, available data, and expected benefits.\n\n"
        f"{conversation_text}"
    )
    try:
        response = model.generate_content(prompt)
        return _safe_response_text(response)
    except (ValueError, RuntimeError):
        raise
    except Exception as e:
        raise RuntimeError(f"AI service error during summary generation: {e}") from e


def generate_documents(use_case_dict: dict, doc_type: str, prompt_template: str) -> str:
    """
    Generate a document (prd, tech_spec, or jira_ticket) as a markdown string.
    """
    model = _get_model()
    prompt = (
        prompt_template
        .replace("{{USE_CASE_JSON}}", json.dumps(use_case_dict, indent=2))
        .replace("{{DOC_TYPE}}", doc_type)
    )
    try:
        response = model.generate_content(prompt)
        return _safe_response_text(response)
    except (ValueError, RuntimeError):
        raise
    except Exception as e:
        raise RuntimeError(f"AI service error during document generation: {e}") from e


def _parse_json_response(raw: str) -> dict:
    """Strip markdown code fences and parse JSON. Retries once on failure."""
    text = raw.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Drop first line (```json or ```) and last line (```)
        text = "\n".join(lines[1:-1]).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Second attempt: wait briefly then ask the model to fix it
        time.sleep(1)
        model = _get_model()
        try:
            retry_response = model.generate_content(
                f"The following text should be valid JSON but has formatting issues. "
                f"Return ONLY the corrected JSON object with no other text:\n\n{raw}"
            )
            cleaned = _safe_response_text(retry_response).strip()
        except Exception as e:
            raise RuntimeError(f"AI service error during JSON retry: {e}") from e
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse JSON response after retry. Raw text: {raw!r}") from e
