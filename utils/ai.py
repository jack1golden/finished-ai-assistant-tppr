# utils/ai.py
from __future__ import annotations
import os
from typing import Dict, Any

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # library not installed yet / not available

MODEL = os.getenv("SAFETY_AI_MODEL", "gpt-4o-mini")

def is_available() -> bool:
    """Returns True if an OpenAI key + library are available."""
    return bool(os.getenv("OPENAI_API_KEY") and OpenAI is not None)

def _rule_based(prompt: str, context: Dict[str, Any]) -> str:
    room = context.get("room", "Unknown room")
    gas = context.get("gas", "Unknown gas")
    value = context.get("value")
    status = context.get("status", "OK")
    thr = context.get("thresholds", {})
    simulate = context.get("simulate", False)

    advice = []
    advice.append(f"Room: **{room}** • Gas: **{gas}** • Status: **{status}**")
    if value is not None and thr:
        advice.append(f"Latest reading: **{value:.2f}{thr.get('units','')}**")
        if thr["mode"] == "low":
            advice.append(f"Low‑warn: {thr['warn']}{thr['units']} • Low‑alarm: {thr['alarm']}{thr['units']}")
        else:
            advice.append(f"Warn: {thr['warn']}{thr['units']} • Alarm: {thr['alarm']}{thr['units']}")

    if status == "ALARM":
        advice.append("**Actions now:** Close shutters, isolate source, stop work, evacuate to muster, and call ERT.")
        if gas in ("H₂S", "CO"):
            advice.append("Use gas monitors; SCBA required for re‑entry if concentrations are unknown.")
        if gas in ("O₂",):
            advice.append("Low O₂: treat as IDLH; ventilate and prevent confined‑space entry.")
    elif status == "WARN":
        advice.append("**Actions:** Increase extraction/ventilation, check for leaks/consumption, prepare shutdown if trend continues.")
    else:
        advice.append("No abnormal conditions. Keep ventilation and routine checks in place.")

    if simulate:
        advice.append("_(Simulation mode active.)_")

    if prompt.strip():
        advice.append(f"**Reply:** {prompt.strip()} → Prioritize isolation, ventilation control, and continuous monitoring.")

    return "\n\n".join(advice)

def ask_ai(prompt: str, context: Dict[str, Any], force_rule: bool = False) -> str:
    """
    Returns an answer as markdown. Uses OpenAI if key/library present and force_rule=False,
    else rule-based.
    context keys: room, gas, value, status, thresholds, simulate, recent_series
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if force_rule or not api_key or OpenAI is None:
        return _rule_based(prompt, context)

    try:
        client = OpenAI(api_key=api_key)
        sys_prompt = (
            "You are an industrial safety assistant for a pharmaceutical facility. "
            "Give concise, actionable guidance using standards-informed best practice. "
            "If status=ALARM, prioritize life safety and isolation. If status=WARN, "
            "recommend immediate mitigations and verification. Avoid speculation. "
            "Output in short paragraphs and bullets."
        )
        msgs = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"Context: {context}\n\nQuestion: {prompt}"},
        ]
        resp = client.chat.completions.create(
            model=MODEL,
            messages=msgs,
            temperature=0.3,
            max_tokens=350,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return _rule_based(prompt, context)
