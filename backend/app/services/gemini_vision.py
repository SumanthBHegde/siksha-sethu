"""Gemini Vision register extraction service.

Converts register images (attendance / pm-poshan / stock / audit) into structured JSON.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import google.generativeai as genai
from PIL import Image

from app.core.config import get_settings

settings = get_settings()

if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)


DETERMINISTIC_GENERATION_CONFIG = {
    "temperature": 0,
    "top_p": 1,
    "top_k": 1,
    "candidate_count": 1,
}


# ------------------------------------------------------------------
# PASS 1: CLASSIFICATION PROMPT
# ------------------------------------------------------------------
CLASSIFICATION_PROMPT = """You are an expert at analyzing handwritten Indian government school registers and documents.

Analyze this image and determine exactly what type of document it is. Pay close attention to whether a PM Poshan/Akshara Dasoha register is tracking a single day's summary, or tracking a whole month row-by-row.

Return STRICT JSON in this exact shape:
{
  "register_type": "attendance" | "daily_pm_poshan" | "monthly_pm_poshan" | "stock" | "audit" | "unknown",
  "confidence": "high" | "medium" | "low",
  "reasoning": "A brief, 1-sentence explanation of why you chose this classification."
}

Definitions to help you choose:
- "attendance": Lists student names and marks present/absent/late.
- "daily_pm_poshan": A mid-day meal summary for a SINGLE day, showing total beneficiaries and total ingredients used.
- "monthly_pm_poshan": A mid-day meal ledger where each ROW represents a different DAY of the month (1, 2, 3...) tracking opening balance, consumption, and closing balance.
- "stock": A general stock register tracking items received and consumed (not necessarily daily meal data).
- "audit": Text-heavy summaries, compliance certificates, or overall reports.
- "unknown": If it doesn't match any of the above.

Return ONLY the JSON object. No prose, no markdown fences."""


# ------------------------------------------------------------------
# PASS 2: SPECIALIST EXTRACTION PROMPTS
# ------------------------------------------------------------------
SPECIFIC_PROMPTS: dict[str, str] = {
    "attendance": """You are an expert at reading handwritten Indian government school attendance registers, especially Kannada-medium.

Extract the data and return STRICT JSON with this shape:
{
  "register_type": "attendance",
  "date": "YYYY-MM-DD or null if not visible",
  "class": "grade/class if visible or null",
  "section": "section if visible or null",
  "entries": [
    {"roll_no": "string", "name": "string", "status": "present|absent|late"}
  ],
  "summary": {"total": int, "present": int, "absent": int, "late": int},
  "notes": "any anomalies, illegible rows, or remarks"
}

Rules:
- Keep student names exactly as written, including Kannada script. Do not translate.
- Map ticks/P/ಹಾಜರು to 'present', crosses/A/ಗೈರು to 'absent', L/ಲೇಟ್ to 'late'.
- Convert Kannada/Indian numerals to standard numbers.
- Return ONLY the JSON object. No prose, no markdown fences.""",

    "daily_pm_poshan": """You are an expert at reading single-day PM POSHAN (mid-day meal) summaries.

Extract the data and return STRICT JSON with this shape:
{
  "register_type": "daily_pm_poshan",
  "date": "YYYY-MM-DD or null",
  "meal_type": "lunch|breakfast",
  "beneficiaries": int,
  "meals_served": int,
  "ingredients": {
     "rice_kg": float, "dal_kg": float, "vegetables_kg": float, "oil_l": float
  },
  "notes": "any anomalies or remarks"
}

Rules:
- Map ಅಕ್ಕಿ/rice to rice_kg, ಬೇಳೆ/dal to dal_kg, ತರಕಾರಿ/vegetables to vegetables_kg, ಎಣ್ಣೆ/oil to oil_l.
- Convert Kannada/Indian numerals to standard numbers.
- Return ONLY the JSON object. No prose, no markdown fences.""",

    "monthly_pm_poshan": """You are an expert at reading handwritten PM POSHAN monthly stock and consumption ledgers.

This document is a monthly ledger. Rows correspond to individual days of the month.

Extract the data and return STRICT JSON with this shape:
{
  "register_type": "monthly_pm_poshan",
  "month_year": "YYYY-MM or null if not visible",
  "district": "string or null",
  "taluk": "string or null",
  "daily_entries": [
    {
      "day_of_month": int,
      "is_holiday": boolean,
      "attendance_primary": int,
      "attendance_higher_primary": int,
      "items": {
        "rice_primary": { "opening_kg": float, "consumed_kg": float, "closing_kg": float },
        "rice_higher_primary": { "opening_kg": float, "consumed_kg": float, "closing_kg": float },
        "wheat_ragi": { "opening_kg": float, "consumed_kg": float, "closing_kg": float },
        "dal": { "opening_kg": float, "consumed_kg": float, "closing_kg": float }
      }
    }
  ],
  "notes": "any anomalies, illegible rows, or remarks"
}

Rules:
- Process every single row visible. The left-most column indicates the day of the month (1, 2, 3, etc.).
- If a row is marked with text spanning across columns (e.g., "ರವಿವಾರ" indicating Sunday), set "is_holiday": true and use 0 for numbers.
- Ensure decimal points in weights (e.g., 507.5) are captured accurately.
- Return ONLY the JSON object. No prose, no markdown fences.""",

    "stock": """You are an expert at reading handwritten Indian government school stock registers.

Extract the data and return STRICT JSON:
{
  "register_type": "stock",
  "date": "YYYY-MM-DD or null",
  "items": [
    {"item": "string", "opening_kg": float, "received_kg": float, "consumed_kg": float, "closing_kg": float}
  ],
  "notes": "any anomalies"
}

Rules:
- Convert Kannada/Indian numerals to standard numbers.
- Return ONLY the JSON object. No prose, no markdown fences.""",

    "audit": """You are reading a government school audit-related document.

Extract the data and return STRICT JSON:
{
  "register_type": "audit",
  "doc_type": "best guess: attendance_summary | stock_summary | compliance_certificate | other",
  "title": "title or heading of the document",
  "key_fields": {"<field name>": "<value>"},
  "date_range": "YYYY-MM-DD to YYYY-MM-DD or null",
  "notes": "any anomalies"
}

Rules:
- Preserve Kannada titles and field values.
- Return ONLY the JSON object. No prose, no markdown fences.""",
}


def _strip_fences(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _extract_json_object(s: str) -> str:
    """Return the first complete JSON object from a model response."""
    s = _strip_fences(s)
    start = s.find("{")
    if start == -1:
        return s

    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(s[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]

    return s[start:]


def _log_ai_response(
    *,
    register_type: str,
    image_path: str | Path,
    raw_text: str,
    parsed: dict[str, Any],
) -> None:
    log_dir = Path(settings.AI_RESPONSE_LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "vision_responses.jsonl"
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "register_type": register_type,
        "image_path": str(image_path),
        "raw_text": raw_text,
        "parsed": parsed,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def extract_register(image_path: str | Path, register_type: str) -> dict[str, Any]:
    """Extract structured data from a register image using direct specialist.
    
    Skips classification and directly uses the specialist prompt for register_type.
    register_type in {"attendance", "daily_pm_poshan", "monthly_pm_poshan", "stock", "audit"}
    """
    register_type = register_type.lower().replace("-", "_")
    prompt = SPECIFIC_PROMPTS.get(register_type)
    if not prompt:
        raise ValueError(f"Unknown register_type: {register_type}")

    if not settings.GOOGLE_API_KEY:
        parsed = {
            "register_type": register_type,
            "error": "GOOGLE_API_KEY not configured",
            "mock": True,
            "entries": [],
        }
        _log_ai_response(
            register_type=register_type,
            image_path=image_path,
            raw_text="",
            parsed=parsed,
        )
        return parsed

    image = Image.open(image_path)
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(
        [prompt, image],
        generation_config=DETERMINISTIC_GENERATION_CONFIG,
    )

    raw_text = response.text or ""
    text = _extract_json_object(raw_text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        parsed = {
            "register_type": register_type,
            "error": f"JSON parse failed: {e}",
            "raw_text": text,
        }
    _log_ai_response(
        register_type=register_type,
        image_path=image_path,
        raw_text=raw_text,
        parsed=parsed,
    )
    return parsed


def _classify_register(image_path: str | Path) -> dict[str, Any]:
    """PASS 1: Classify the register type from an image.
    
    Returns a dict with keys: register_type, confidence, reasoning
    """
    if not settings.GOOGLE_API_KEY:
        return {
            "register_type": "unknown",
            "confidence": "low",
            "reasoning": "GOOGLE_API_KEY not configured",
            "error": "GOOGLE_API_KEY not configured",
        }

    image = Image.open(image_path)
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(
        [CLASSIFICATION_PROMPT, image],
        generation_config=DETERMINISTIC_GENERATION_CONFIG,
    )

    raw_text = response.text or ""
    text = _extract_json_object(raw_text)
    try:
        classification = json.loads(text)
    except json.JSONDecodeError as e:
        classification = {
            "register_type": "unknown",
            "confidence": "low",
            "reasoning": f"Classification JSON parse failed: {e}",
            "raw_text": text,
        }
    return classification


def _extract_with_specialist(
    image_path: str | Path, register_type: str
) -> dict[str, Any]:
    """PASS 2: Extract data using type-specific specialist prompt."""
    register_type = register_type.lower().replace("-", "_")
    
    # Map old 'pm_poshan' to new types if encountered
    if register_type == "pm_poshan":
        register_type = "daily_pm_poshan"
    
    prompt = SPECIFIC_PROMPTS.get(register_type)
    if not prompt:
        return {
            "register_type": register_type,
            "error": f"Unknown register_type: {register_type}",
        }

    if not settings.GOOGLE_API_KEY:
        return {
            "register_type": register_type,
            "error": "GOOGLE_API_KEY not configured",
            "mock": True,
        }

    image = Image.open(image_path)
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(
        [prompt, image],
        generation_config=DETERMINISTIC_GENERATION_CONFIG,
    )

    raw_text = response.text or ""
    text = _extract_json_object(raw_text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        parsed = {
            "register_type": register_type,
            "error": f"JSON parse failed: {e}",
            "raw_text": text,
        }

    _log_ai_response(
        register_type=register_type,
        image_path=image_path,
        raw_text=raw_text,
        parsed=parsed,
    )
    return parsed


def extract_auto_register(image_path: str | Path) -> dict[str, Any]:
    """Two-pass extraction: PASS 1 classifies, PASS 2 extracts specialist data.
    
    Returns enriched extraction dict with classification metadata.
    """
    # PASS 1: Classify
    classification = _classify_register(image_path)
    register_type = classification.get("register_type", "unknown")
    
    if register_type == "unknown":
        # Classification failed, return the error as-is
        _log_ai_response(
            register_type="auto",
            image_path=image_path,
            raw_text=json.dumps(classification),
            parsed=classification,
        )
        return classification
    
    # PASS 2: Extract using specialist
    extraction = _extract_with_specialist(image_path, register_type)
    
    # Enrich extraction with classification metadata
    extraction["classification_confidence"] = classification.get("confidence")
    extraction["classification_reasoning"] = classification.get("reasoning")
    
    return extraction


def chat_with_gemini(prompt: str, system: str | None = None) -> str:
    """Plain text completion via Gemini, used as fallback when no agent matches."""
    if not settings.GOOGLE_API_KEY:
        return "[Gemini not configured. Set GOOGLE_API_KEY in backend/.env]"
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=system or "You are ShikshaSetu, a helpful AI administrative assistant for Indian government school teachers.",
    )
    response = model.generate_content(
        prompt,
        generation_config=DETERMINISTIC_GENERATION_CONFIG,
    )
    return (response.text or "").strip()
