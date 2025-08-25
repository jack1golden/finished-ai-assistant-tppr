# utils/facility.py
from __future__ import annotations

import base64
from pathlib import Path
from urllib.parse import quote

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

# ---------- helpers ----------
def _b64_of(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _img64(path: Path) -> str:
    return f"data:image/{path.suffix.lstrip('.').lower()};base64,{_b64_of(path)}"

def _exists(p: Path) -> bool:
    return p.exists() and p.is_file()

# ---------- file candidates ----------
OVERVIEW_CANDS = ["Overview.png", "Overview (1).png", "overview.png"]
ROOM_FILES = {
    "Room 1": ["Room 1.png"],
    "Room 2": ["Room 2 (1).png", "Room 2.png"],
    "Room 3": ["Room 3 (1).png", "Room 3.png"],
    "Room Production": ["Room Production.png"],
    "Room Production 2": ["Room Production 2.png", "Room Production2.png"],
    "Room 12 17": ["Room 12 17.png", "Room 12.png", "Room 17.png"],
}

def _find_first(images_dir: Path, names: list[str]) -> Path | None:
    for n in names:
        p = images_dir / n
        if _exists(p):
            return p
    return None

# ---------- overview hotspots (your latest + size adjust where asked) ----------
HOTSPOTS = {
    "Room 1": dict(left=63, top=2, width=14, height=16),
    "Room 2": dict(left=67, top=43, width=14, height=16),
    "Room 3": dict(left=60, top=19, width=14, height=16),
    "Room 12 17": dict(left=38, top=-5, width=13, height=15),
    "Room Production": dict(left=24, top=28, width=23, height=21),
    "Room Production 2": dict(left=23, top=3, width=23, height=21),
}

# ---------- detectors ----------
GAS_RANGES = {
    "NH₃": "0–50 ppm",
    "CO": "0–200 ppm",
    "O₂": "19–23 %",
    "CH₄": "0–100 %LEL",
    "H₂S": "0–100 ppm",
    "Ethanol": "0–1000 ppm",
}

DETECTORS = {
    "Room 1": [dict(label="NH₃", x=35, y=35, units="ppm")],
    "Room 2": [dict(label="CO", x=93, y=33, units="ppm")],
    "Room 3": [dict(label="O₂", x=28, y=72, units="%")],
    "Room 12 17": [dict(label="Ethanol", x=58, y=36, units="ppm")],
    "Room Production": [
        dict(label="O₂", x=78, y=72, units="%"),
        dict(label="NH₃", x=30, y=28, units="ppm"),
    ],
    "Room Production 2": [
        dict(label="O₂", x=70, y=45, units="%"),
        dict(label="H₂S", x=70, y=65, units="ppm"),
    ],
}

# ---------- live series sim ----------
def _sim_key(room: str, label: str) -> str:
    return f"{room}::{label}"

def _next_value(room: str, label: str) -> float:
    key = _sim_key(room, label)
    state = st.session_state.setdefault("det_sim", {})
    v = state.get(key, 10.0)
    v += np.random.uniform(-0.5, 0.9)
    v = max(0.0, v)
    state[key] = v
    return v

def _series(room: str, label: str, n: int = 60):
    key = _sim_key(room, label)
    buf = st.session_state.setdefault("det_buf", {}).setdefault(key, [])
    buf.append(_next_value(room, label))
    if len(buf) > n:
        buf[:] = buf[-n:]
    return buf

# ======================================================
# Overview
# ======================================================
def render_overview(images_dir: Path):
    ov_path = _find_first(images_dir, OVERVIEW_CANDS)
    if not ov_path:
        st.error("Overview image not found in /images.")
        return

    available = {}
    for room, cands in ROOM_FILES.items():
        p = _find_first(images_dir, cands)
        if p:
            available[room] = p

    hotspots_html = []
    for room, box in HOTSPOTS.items():
        if room not in available:
            continue
        # write both room and nav in the URL for robustness with tabs
        href = f"?room={quote(room)}&nav={quote(room)}"
        hotspots_html.append(
            f"""
            <a class="hotspot" data-room="{room}" href="{href}" target="_top"
               style="left:{box['left']}%;top:{box['top']}%;width:{box['width']}%;height:{box['height']}%;">
              <span>{room}</span>
            </a>
            """
        )
    tags = "\n".join(hotspots_html)

    html = f"""
    <style>
      .wrap {{
        position:relative; width:min(1280px,96%); margin:8px auto;
        border:1px solid #1f2a44; border-radius:12px; overflow:hidden;
        box-shadow:0 18px 60px rgba(0,0,0,.35);
      }}
      .wrap img {{ display:block; width:100%; height:auto; }}
      .hotspot {{
        position:absolute; border:2px solid rgba(34,197,94,.9); border-radius:10px;
        background:rgba(16,185,129,.18); color:#e2e8f0; font-weight:800; font-size:12px;
        display:flex; align-items:flex-start; justify-content:flex-start; padding:4px 6px; z-index:20;
        text-decoration:none;
      }}
      .hotspot:hover {{ background:rgba(16,185,129,.28); }}
      .hotspot span {{
        background:rgba(2,6,23,.55); border:1px solid rgba(103,232,249,.5); padding:2px 6px; border-radius:8px;
      }}
    </style>
    <div class="wrap">
      <img src="{_img64(ov_path)}" alt="overview"/>
      {tags}
    </div>
    """
    components.html(html, height=780, scrolling=False)

# ======================================================
# Room
# ======================================================
def render_room(images_dir: Path, room: str, simulate: bool = False, selected_detector: str | None = None):
    """
    simulate: currently reserved (future gas-cloud animation). Safe to pass; ignored for now.
    """
    room_path = _find_first(images_dir, ROOM_FILES.get(room, []))
    if not room_path:
        st.error(f"No image found for {room} in /images.")
        return

    dets = DETECTORS.get(room, [])

    colL, colR = st.columns([2, 1], gap="large")

    # LEFT: image + detector buttons
    pins_html = []
    for d in dets:
        lbl = d["label"]
        href = f"?room={quote(room)}&det={quote(lbl)}&nav={quote(room)}"
        pins_html.append(
            f"""
            <a class="detector" href="{href}" target="_top" style="left:{d['x']}%;top:{d['y']}%;">
              <div class="lbl">{lbl}</div>
            </a>
            """
        )
    pins = "\n".join(pins_html)

    room_html = f"""
    <style>
      .roomwrap {{
        position:relative; width:100%; max-width:1200px; margin:6px 0;
        border:1px solid #1f2a44; border-radius:12px; overflow:hidden;
        box-shadow:0 18px 60px rgba(0,0,0,.30);
      }}
      .roomwrap img {{ display:block; width:100%; height:auto; }}
      .detector {{
        position:absolute; transform:translate(-50%,-50%);
        border:2px solid #22c55e; border-radius:10px; background:#fff;
        padding:6px 10px; min-width:72px; text-align:center; z-index:20;
        box-shadow:0 0 10px rgba(34,197,94,.35); font-weight:800; color:#0f172a; text-decoration:none;
      }}
      .detector:hover {{ background:#eaffea; }}
      .detector .lbl {{ font-size:14px; line-height:1.1; }}
    </style>
    <div class="roomwrap">
      <img src="{_img64(room_path)}" alt="{room}"/>
      {pins}
    </div>
    """
    with colL:
        components.html(room_html, height=720, scrolling=False)

    # RIGHT: chart + AI
    with colR:
        if selected_detector:
            st.subheader(f"📈 {selected_detector} — Live trend")
            series = _series(room, selected_detector, n=90)
            st.line_chart({"reading": series})
            st.caption(f"Range: {GAS_RANGES.get(selected_detector, '—')}")
        else:
            st.info("Click a detector badge on the image to view its live trend.")
        st.divider()
        st.subheader("🤖 AI Safety Assistant")
        if p := st.chat_input("Ask about leaks, thresholds or actions…"):
            st.chat_message("user").write(p)
            st.chat_message("ai").write(
                "Recommendation: close shutters; increase extraction; verify detector calibrations; "
                "evacuate if O₂ < 19.5%."
            )

# ---------- simple pages ----------
def render_settings():
    st.write("Thresholds, units, and integrations will live here. Positions are hardcoded in this file.")

def render_ai_chat():
    st.chat_message("ai").write("Hi, I’m your safety AI. Ask me about leaks, thresholds, or actions.")
    if p := st.chat_input("Ask the AI Safety Assistant…"):
        st.chat_message("user").write(p)
        st.chat_message("ai").write(
            "Recommendation: close shutters in all affected rooms; increase extraction in Production areas; "
            "verify detector calibrations and evacuate if O₂ < 19.5%."
        )







        



