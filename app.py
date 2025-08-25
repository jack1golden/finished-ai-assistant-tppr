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

_d("nav", "Overview")
_d("current_room", None)
_d("selected_detector", None)
_d("simulate_by_room", {})  # {room: bool}

# ---------- query params → session sync ----------
qp = st.query_params
if "room" in qp and qp["room"]:
    room_val = unquote(qp["room"])
    st.session_state["current_room"] = room_val
    st.session_state["nav"] = room_val
if "det" in qp and qp["det"]:
    st.session_state["selected_detector"] = unquote(qp["det"])
if "nav" in qp and qp["nav"]:
    st.session_state["nav"] = unquote(qp["nav"])
    if st.session_state["nav"] == "Overview":
        st.session_state["current_room"] = None
        st.session_state["selected_detector"] = None

ROOM_TABS = {"Room 1", "Room 2", "Room 3", "Room Production", "Room Production 2", "Room 12 17"}
if st.session_state["nav"] in ROOM_TABS and st.session_state.get("current_room") != st.session_state["nav"]:
    st.session_state["current_room"] = st.session_state["nav"]

# ---------- header: tabs + logo ----------
cols = st.columns([5, 1])
with cols[0]:
    tabs = st.tabs([
        "Overview",
        "Room 1", "Room 2", "Room 3",
        "Room Production", "Room Production 2", "Room 12 17",
        "Settings", "AI",
    ])
with cols[1]:
    logo = IMAGES / "logo.png"
    if logo.exists():
        st.image(str(logo), caption="", use_container_width=True)

def _activate(name: str):
    st.session_state["nav"] = name
    st.session_state["current_room"] = None if name == "Overview" else name
    st.session_state["selected_detector"] = None
    if name == "Overview":
        st.query_params.clear()
    else:
        st.query_params.update({"room": name, "nav": name})

active = st.session_state["nav"]

# ---------- Overview tab ----------
with tabs[0]:
    if active == "Overview":
        st.title("🏭 Facility Overview (2.5D)")
        facility.render_overview(IMAGES)
        st.markdown("#### Quick open")
        bcols = st.columns(6)
        labels = ["Room 1", "Room 2", "Room 3", "Room Production", "Room Production 2", "Room 12 17"]
        for i, rn in enumerate(labels):
            if bcols[i].button(rn, key=f"open_{rn}"):
                _activate(rn)
                st.rerun()

# ---------- Room tabs ----------
def _room_tab(tab_container, room_name: str, sim_key: str):
    with tab_container:
        if active == room_name:
            st.session_state["current_room"] = room_name
            st.title(f"🚪 {room_name}")
            c1, c2, c3 = st.columns([1, 1, 2])
            if c1.button("💨 Simulate Gas Leak", key=f"sim_{sim_key}"):
                st.session_state["simulate_by_room"][room_name] = True
                st.rerun()
            if c2.button("⏹ Reset", key=f"reset_{sim_key}"):
                st.session_state["simulate_by_room"][room_name] = False
                st.rerun()
            if c3.button("⬅️ Back to Overview", key=f"back_{sim_key}"):
                _activate("Overview")
                st.rerun()
            facility.render_room(
                images_dir=IMAGES,
                room=room_name,
                simulate=st.session_state["simulate_by_room"].get(room_name, False),
                selected_detector=st.session_state["selected_detector"],
            )

_room_tab(tabs[1], "Room 1", "room1")
_room_tab(tabs[2], "Room 2", "room2")
_room_tab(tabs[3], "Room 3", "room3")
_room_tab(tabs[4], "Room Production", "prod1")
_room_tab(tabs[5], "Room Production 2", "prod2")
_room_tab(tabs[6], "Room 12 17", "r1217")

# ---------- Settings ----------
with tabs[7]:
    if active == "Settings":
        st.title("⚙️ Settings")
        facility.render_settings()

# ---------- AI ----------
with tabs[8]:
    if active == "AI":
        st.title("🤖 AI Safety Assistant")
        facility.render_ai_chat()
