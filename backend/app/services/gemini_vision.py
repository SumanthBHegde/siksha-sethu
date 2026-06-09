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


PROMPTS: dict[str, str] = {
    "attendance": """You are an expert at reading handwritten Indian government school attendance registers, especially Kannada-medium school registers.

Extract the data from this register image and return STRICT JSON with this shape:
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
- The image may be primarily in Kannada. Understand Kannada labels, names, dates, numerals, and attendance marks.
- Keep student names exactly as written, including Kannada script. Do not translate names.
- Convert Kannada/Indian numerals and dates into the requested JSON values.
- Use 'present' for ticks, P, ಹಾಜರು, ಹಾ, present-like marks; 'absent' for crosses, A, ಗೈರು, ಗೈ, absent-like marks; 'late' for L or late remarks.
- If a row is unreadable, still include it with status='absent' and add a note.
- Return ONLY the JSON object. No prose, no markdown fences.""",

    "pm_poshan": """You are an expert at reading handwritten Indian government school PM POSHAN (mid-day meal) registers, especially Kannada registers.

Extract the data and return STRICT JSON with this shape:
{
  "register_type": "pm_poshan",
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
- The image may be primarily in Kannada. Understand Kannada labels, dates, quantities, and item names.
- Convert Kannada/Indian numerals and units into plain numbers.
- Map ಅಕ್ಕಿ/rice to rice_kg, ಬೇಳೆ/dal to dal_kg, ತರಕಾರಿ/vegetables to vegetables_kg, ಎಣ್ಣೆ/oil to oil_l.
- Return ONLY the JSON object. No prose, no markdown fences.""",

    "stock": """You are an expert at reading handwritten Indian government school stock registers (PM POSHAN supplies), especially Kannada registers.

Extract the data and return STRICT JSON:
{
  "register_type": "stock",
  "date": "YYYY-MM-DD or null",
  "items": [
    {"item": "rice|dal|oil|vegetables|...", "opening_kg": float, "received_kg": float, "consumed_kg": float, "closing_kg": float}
  ],
  "notes": "any anomalies"
}

Rules:
- The image may be primarily in Kannada. Understand Kannada item names, labels, dates, and quantities.
- Keep item names readable, but normalize common supplies when obvious: ಅಕ್ಕಿ/rice, ಬೇಳೆ/dal, ಎಣ್ಣೆ/oil, ತರಕಾರಿ/vegetables.
- Convert Kannada/Indian numerals and units into plain numbers.
- Return ONLY the JSON object. No prose, no markdown fences.""",

    "audit": """You are reading a government school audit-related document, often in Kannada.

Extract the data and return STRICT JSON:
{
  "register_type": "audit",
  "doc_type": "best guess: attendance_summary | stock_summary | meal_summary | compliance_certificate | other",
  "title": "title or heading of the document",
  "key_fields": {"<field name>": "<value>"},
  "date_range": "YYYY-MM-DD to YYYY-MM-DD or null",
  "notes": "any anomalies"
}

Rules:
- The image may be primarily in Kannada. Preserve Kannada titles and field values when present.
- Convert dates into YYYY-MM-DD when possible.
- Return ONLY the JSON object."""
}


AUTO_PROMPT = """You are an expert at reading Kannada and English government school register images.

Read this image, summarize what kind of register/document it is, then label it as exactly one of:
- attendance
- pm_poshan
- stock
- audit

After labeling, extract the useful database fields for that type.

Return STRICT JSON in this shape:
{
  "register_type": "attendance|pm_poshan|stock|audit",
  "classification_summary": "short reason for the chosen type",
  "date": "YYYY-MM-DD or null",
  "class": "grade/class if visible or null",
  "section": "section if visible or null",
  "entries": [
    {"roll_no": "string", "name": "string", "status": "present|absent|late"}
  ],
  "meal_type": "lunch|breakfast",
  "beneficiaries": 0,
  "meals_served": 0,
  "ingredients": {
    "rice_kg": 0, "dal_kg": 0, "vegetables_kg": 0, "oil_l": 0
  },
  "items": [
    {"item": "rice|dal|oil|vegetables|...", "opening_kg": 0, "received_kg": 0, "consumed_kg": 0, "closing_kg": 0}
  ],
  "doc_type": "attendance_summary | stock_summary | meal_summary | compliance_certificate | other",
  "title": "title or heading",
  "key_fields": {"<field name>": "<value>"},
  "notes": "any anomalies, unreadable data, or remarks"
}

Rules:
- The image may be primarily in Kannada. Understand Kannada labels, names, item names, dates, numerals, and attendance marks.
- Keep student names and document titles exactly as written, including Kannada script.
- Fill only fields relevant to the chosen register_type; use empty lists/objects or 0 for irrelevant fields.
- Convert Kannada/Indian numerals and units into plain JSON numbers.
- Return ONLY the JSON object. No prose, no markdown fences."""


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
    """Extract structured data from a register image.

    register_type in {"attendance", "pm_poshan", "stock", "audit"}
    """
    register_type = register_type.lower().replace("-", "_")
    prompt = PROMPTS.get(register_type)
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


def extract_auto_register(image_path: str | Path) -> dict[str, Any]:
    """Classify a register image and extract database-ready structured data."""
    if not settings.GOOGLE_API_KEY:
        parsed = {
            "register_type": "unknown",
            "classification_summary": "GOOGLE_API_KEY not configured",
            "error": "GOOGLE_API_KEY not configured",
            "mock": True,
        }
        _log_ai_response(
            register_type="auto",
            image_path=image_path,
            raw_text="",
            parsed=parsed,
        )
        return parsed

    image = Image.open(image_path)
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(
        [AUTO_PROMPT, image],
        generation_config=DETERMINISTIC_GENERATION_CONFIG,
    )

    raw_text = response.text or ""
    text = _extract_json_object(raw_text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        parsed = {
            "register_type": "unknown",
            "error": f"JSON parse failed: {e}",
            "raw_text": text,
        }
    _log_ai_response(
        register_type="auto",
        image_path=image_path,
        raw_text=raw_text,
        parsed=parsed,
    )
    return parsed


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
