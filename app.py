# app.py
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

# ─────────────────────────────────────────────
# Make sure we can import from ./utils
# ─────────────────────────────────────────────
HERE = Path(__file__).parent.resolve()
UTILS_DIR = HERE / "utils"
if str(UTILS_DIR) not in sys.path:
    sys.path.insert(0, str(UTILS_DIR))

# Prefer package import if utils is a package; otherwise fallback to module
try:
    from utils import facility  # type: ignore
except Exception:
    import facility  # type: ignore

# ─────────────────────────────────────────────
# Page config & session defaults
# ─────────────────────────────────────────────
st.set_page_config(page_title="Pharma Safety HMI — AI First", layout="wide")

st.session_state.setdefault("nav_tab", "Home")
st.session_state.setdefault("current_room", None)
st.session_state.setdefault("selected_detector", None)
st.session_state.setdefault("simulate_by_room", {})
st.session_state.setdefault("cal_overview", False)
st.session_state.setdefault("cal_room", False)
st.session_state.setdefault("cal_overview_room", "Room 1")

IMAGES = HERE / "images"
IMAGES.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# Sidebar navigation
# ─────────────────────────────────────────────
tabs = [
    "Home", "Overview",
    "Room 1", "Room 2", "Room 3", "Room 12 17", "Room Production", "Room Production 2",
    "Settings", "AI Safety Assistant",
]
st.session_state["nav_tab"] = st.sidebar.radio(
    "🔎 Navigation",
    tabs,
    index=tabs.index(st.session_state["nav_tab"]) if st.session_state["nav_tab"] in tabs else 0,
)

with st.sidebar:
    st.markdown("### 🧭 Calibration")
    st.session_state["cal_overview"] = st.checkbox("Calibrate Overview", value=st.session_state["cal_overview"])
    st.session_state["cal_room"] = st.checkbox("Calibrate Room", value=st.session_state["cal_room"])

    if st.session_state["cal_overview"]:
        st.session_state["cal_overview_room"] = st.selectbox(
            "Room to place on Overview",
            ["Room 1", "Room 2", "Room 3", "Room 12 17", "Room Production", "Room Production 2"],
            index=["Room 1", "Room 2", "Room 3", "Room 12 17", "Room Production", "Room Production 2"]
            .index(st.session_state["cal_overview_room"]),
        )

# ─────────────────────────────────────────────
# Routing
# ─────────────────────────────────────────────
tab = st.session_state["nav_tab"]

if tab == "Home":
    colL, colR = st.columns([2, 1], gap="large")
    with colL:
        facility.render_logo(IMAGES)
        st.markdown("### Facility Simulation & AI Safety Assistant")
        st.write(
            "2.5D facility HMI demo with on-image room buttons, detector controls, "
            "animated gas clouds and shutters, live trends, and an AI Safety Assistant panel."
        )
        if st.button("Enter Simulation → Overview", key="enter_overview"):
            st.session_state["nav_tab"] = "Overview"
            st.rerun()
    with colR:
        if not (IMAGES / "logo.png").exists():
            st.info("Using a temporary logo. Add **images/logo.png** to replace it.")

elif tab == "Overview":
    st.title("🏭 Facility Overview")
    facility.render_overview(
        images_dir=IMAGES,
        calibrate=st.session_state["cal_overview"],
        cal_room=st.session_state["cal_overview_room"],
    )

elif tab in ("Room 1", "Room 2", "Room 3", "Room 12 17", "Room Production", "Room Production 2"):
    room = tab
    st.title(f"🚪 {room}")

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("💨 Simulate Gas Leak", key=f"sim_{room}"):
            st.session_state["simulate_by_room"][room] = True
            st.rerun()
    with c2:
        if st.button("⏹ Reset Simulation", key=f"reset_{room}"):
            st.session_state["simulate_by_room"][room] = False
            st.rerun()
    with c3:
        if st.button("⬅️ Back to Overview", key=f"back_{room}"):
            st.session_state["nav_tab"] = "Overview"
            st.session_state["selected_detector"] = None
            st.rerun()

    facility.render_room(
        images_dir=IMAGES,
        room=room,
        simulate=st.session_state["simulate_by_room"].get(room, False),
        calibrate=st.session_state["cal_room"],
    )

elif tab == "Settings":
    st.title("⚙️ Settings")
    facility.render_settings()

elif tab == "AI Safety Assistant":
    st.title("🤖 AI Safety Assistant")
    facility.render_ai_chat()

else:
    st.title("❓ Unknown")
    st.write("Pick a tab in the sidebar.")

