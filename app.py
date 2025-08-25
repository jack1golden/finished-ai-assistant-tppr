# app.py
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote

import streamlit as st

# ---------- paths / imports ----------
HERE = Path(__file__).parent.resolve()
IMAGES = HERE / "images"
IMAGES.mkdir(parents=True, exist_ok=True)

UTILS_DIR = HERE / "utils"
if str(UTILS_DIR) not in sys.path:
    sys.path.insert(0, str(UTILS_DIR))

from utils import facility  # utils/facility.py

st.set_page_config(page_title="Pharma Safety HMI — AI First", layout="wide")

# ---------- session defaults ----------
def _d(k, v):
    if k not in st.session_state:
        st.session_state[k] = v

_d("current_room", None)
_d("selected_detector", None)
_d("simulate_by_room", {})  # {room: bool}

# ---------- query params → session sync ----------
qp = st.query_params
if "room" in qp and qp["room"]:
    st.session_state["current_room"] = unquote(qp["room"])
if "det" in qp and qp["det"]:
    st.session_state["selected_detector"] = unquote(qp["det"])

# ---------- header: tabs + logo ----------
cols = st.columns([5, 1])
with cols[0]:
    tab_overview, tab_r1, tab_r2, tab_r3, tab_p1, tab_p2, tab_r1217, tab_settings, tab_ai = st.tabs([
        "Overview",
        "Room 1", "Room 2", "Room 3",
        "Room Production", "Room Production 2", "Room 12 17",
        "Settings", "AI",
    ])
with cols[1]:
    logo = IMAGES / "logo.png"
    if logo.exists():
        st.image(str(logo), caption="", use_container_width=True)

# ---------- Overview ----------
with tab_overview:
    st.title("🏭 Facility Overview (2.5D)")
    facility.render_overview(IMAGES)

    # Native backup buttons under the image
    st.markdown("#### Quick open")
    bcols = st.columns(6)
    labels = ["Room 1", "Room 2", "Room 3", "Room Production", "Room Production 2", "Room 12 17"]
    for i, rn in enumerate(labels):
        if bcols[i].button(rn, key=f"open_{rn}"):
            st.session_state["current_room"] = rn
            st.query_params.update({"room": rn})
            st.rerun()

# Helper to render each room tab
def _room_tab(container, room_name: str, sim_key: str):
    with container:
        st.title(f"🚪 {room_name}")
        c1, c2, c3 = st.columns([1, 1, 2])
        if c1.button("💨 Simulate Gas Leak", key=f"sim_{sim_key}"):
            st.session_state["simulate_by_room"][room_name] = True
            st.query_params.update({"room": room_name})
            st.rerun()
        if c2.button("⏹ Reset", key=f"reset_{sim_key}"):
            st.session_state["simulate_by_room"][room_name] = False
            st.query_params.update({"room": room_name})
            st.rerun()
        if c3.button("⬅️ Back to Overview", key=f"back_{sim_key}"):
            st.session_state["current_room"] = None
            st.session_state["selected_detector"] = None
            st.query_params.clear()
            st.rerun()

        facility.render_room(
            images_dir=IMAGES,
            room=room_name,
            simulate=st.session_state["simulate_by_room"].get(room_name, False),
            selected_detector=st.session_state["selected_detector"],
        )

# ---------- Rooms (tabs now render unconditionally—no extra clicking needed) ----------
_room_tab(tab_r1, "Room 1", "room1")
_room_tab(tab_r2, "Room 2", "room2")
_room_tab(tab_r3, "Room 3", "room3")
_room_tab(tab_p1, "Room Production", "prod1")
_room_tab(tab_p2, "Room Production 2", "prod2")
_room_tab(tab_r1217, "Room 12 17", "r1217")

# ---------- Settings ----------
with tab_settings:
    st.title("⚙️ Settings")
    facility.render_settings()

# ---------- AI ----------
with tab_ai:
    st.title("🤖 AI Safety Assistant")
    facility.render_ai_chat()
