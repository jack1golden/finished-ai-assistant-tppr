# utils/ai.py
from __future__ import annotations
import os
from typing import Dict, Any

import streamlit as st  # to read st.secrets

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

MODEL = os.getenv("SAFETY_AI_MODEL", "gpt-4o-mini")

def _get_api_key() -> str | None:
    k = os.getenv("OPENAI_API_KEY")
    if k:
        return k
    try:
        return st.secrets.get("OPENAI_API_KEY")  # type: ignore[attr-defined]
    except Exception:
        return None

def is_available() -> bool:
    return bool(_get_api_key() and OpenAI is not None)

def backend_name(force_rule: bool = False) -> str:
    if force_rule:
        return "Rule-based (forced)"
    return "OpenAI" if is_available() else "Rule-based"

def _rule_based(prompt: str, context: Dict[str, Any]) -> str:
    room = context.get("room", "Unknown room")
    gas = context.get("gas", "Unknown gas")
    value = context.get("value")
    status = context.get("status", "OK")
    thr = context.get("thresholds", {})
    simulate = context.get("simulate", False)
    mean = context.get("mean")
    std = context.get("std")
    proj = context.get("projection_minutes")

    advice = []
    advice.append(f"Room: **{room}** • Gas: **{gas}** • Status: **{status}**")
    if mean is not None and std is not None:
        advice.append(f"Baseline (24h): μ={mean:.2f}, σ={std:.2f}")
    if value is not None and thr:
        advice.append(f"Latest: **{value:.2f}{thr.get('units','')}**  •  Warn: {thr.get('warn')}  •  Alarm: {thr.get('alarm')}")
    if proj:
        advice.append(f"Projected threshold crossing in ~{proj} min (estimate).")

    if status == "ALARM":
        advice.append("**Do now:** Close shutters, isolate source, stop work, evacuate to muster, notify ERT.")
    elif status == "WARN":
        advice.append("**Mitigate:** Increase extraction, check for leaks/consumption, prepare shutdown if trend continues.")
    else:
        advice.append("Normal conditions. Maintain ventilation and routine checks.")

    if simulate:
        advice.append("_(Simulation mode active.)_")

    if prompt.strip():
        advice.append(f"**Reply:** {prompt.strip()} → prioritize isolation, ventilation control, and continuous monitoring.")

    return "\n\n".join(advice)

def ask_ai(prompt: str, context: Dict[str, Any], force_rule: bool = False) -> str:
    key = _get_api_key()
    if force_rule or not key or OpenAI is None:
        return _rule_based(prompt, context)
    try:
        client = OpenAI(api_key=key)
        sys_prompt = (
            "You are an industrial safety assistant for a pharmaceutical facility. "
            "Use the provided context (room, gas, latest value, thresholds, baseline stats, trend slope, etc.). "
            "If status=ALARM, prioritize life safety and isolation. If status=WARN, recommend immediate mitigations. "
            "Be concise, with short paragraphs and bullets when helpful."
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


