"""Supervisor agent — intent detection and routing."""
from __future__ import annotations

import re
from app.agents.state import AgentState
from app.services.gemini_vision import chat_with_gemini
from app.core.config import get_settings

settings = get_settings()

INTENT_KEYWORDS = {
    "attendance": [
        "attendance", "absent", "present", "student", "students",
        "anomaly", "anomalies", "monthly summary", "register", "roll",
    ],
    "pm_poshan": [
        "poshan", "meal", "meals", "lunch", "breakfast", "stock",
        "rice", "dal", "oil", "vegetables", "beneficiary", "beneficiaries",
        "consumption", "mid-day",
    ],
    "audit": [
        "audit", "compliance", "readiness", "missing", "document",
        "documents", "verify", "report",
    ],
}


def detect_intent_rule_based(message: str) -> str:
    msg = message.lower()
    scores = {k: 0 for k in INTENT_KEYWORDS}
    for intent, kws in INTENT_KEYWORDS.items():
        for kw in kws:
            if re.search(rf"\b{re.escape(kw)}\b", msg):
                scores[intent] += 1
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "general"
    return best


def detect_intent_llm(message: str) -> str:
    """LLM-assisted fallback when rule-based matching is ambiguous."""
    if not settings.GOOGLE_API_KEY:
        return "general"
    prompt = (
        f"Classify the following teacher's question into ONE of these labels: "
        f"attendance, pm_poshan, audit, general.\n\n"
        f"Question: {message!r}\n\n"
        f"Reply with only the label, nothing else."
    )
    out = chat_with_gemini(prompt).strip().lower()
    if out in {"attendance", "pm_poshan", "audit", "general"}:
        return out
    return "general"


def supervisor_node(state: AgentState) -> AgentState:
    msg = state.get("user_message", "")
    intent = detect_intent_rule_based(msg)
    if intent == "general":
        # Try LLM fallback
        intent = detect_intent_llm(msg)
    return {**state, "intent": intent, "agent": "supervisor"}
