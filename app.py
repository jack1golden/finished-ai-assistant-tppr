# app.py
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote

import streamlit as st

# ─────────────────────────────────────────────
# Force-import utils module from ./utils
# ─────────────────────────────────────────────
HERE = Path(__file__).parent.resolve()
IMAGES = HERE / "images"
IMAGES.mkdir(parents=True, exist_ok=True)

UTILS_DIR = HERE / "utils"
UTILS_DIR.mkdir(parents=True, exist_ok=True)
if str(UTILS_DIR) not in sys.path:
    sys.path.insert(0, str(UTILS_DIR))

# Import rendering module
from utils import facility_module as facility

# ─────────────────────────────────────────────
# Page config & session defaults
# ─────────────────────────────────────────────
st.set_page_config(page_title="Pharma Safety HMI — AI First", layout="wide")

def _ss_set_default(k, v):
    if k not in st.session_state:
        st.session_state[k] = v

_ss_set_default("nav_tab", "Home")
_ss_set_default("current_room", None)
_ss_set_default("selected_detector", None)
_ss_set_default("simulate_by_room", {})  # {room: bool}

# ─────────────────────────────────────────────
# Query params → session sync (supports ?room=...&det=...)
# ─────────────────────────────────────────────
qp = st.query_params
if "room" in qp and qp["room"]:
    room_val = unquote(qp["room"])
    st.session_state["current_room"] = room_val
    st.session_state["nav_tab"] = room_val
if "det" in qp and qp["det"]:
    st.session_state["selected_detector"] = unquote(qp["det"])

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
    st.image(str(IMAGES / "logo.png"), width=180) if (IMAGES / "logo.png").exists() else None
    st.markdown("---")
    if st.button("🏠 Home", key="nav_home_btn"):
        st.session_state["nav_tab"] = "Home"
        st.session_state["current_room"] = None
        st.session_state["selected_detector"] = None
        st.query_params.clear()
        st.rerun()

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
            st.info("Add **images/logo.png** to replace the placeholder logo.")

elif tab == "Overview":
    st.title("🏭 Facility Overview")
    facility.render_overview(IMAGES)

elif tab in ("Room 1", "Room 2", "Room 3", "Room 12 17", "Room Production", "Room Production 2"):
    room = tab
    st.title(f"🚪 {room}")

    # Top controls
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("💨 Simulate Gas Leak", key=f"sim_{room}"):
            st.session_state["simulate_by_room"][room] = True
            st.rerun()
    with c2:
        if st.button("⏹ Reset", key=f"reset_{room}"):
            st.session_state["simulate_by_room"][room] = False
            st.rerun()
    with c3:
        if st.button("⬅️ Back to Overview", key=f"back_{room}"):
            st.session_state["nav_tab"] = "Overview"
            st.session_state["current_room"] = None
            st.session_state["selected_detector"] = None
            st.query_params.clear()
            st.rerun()

    # Render room (image+detectors left, chart+AI right)
    facility.render_room(
        images_dir=IMAGES,
        room=room,
        simulate=st.session_state["simulate_by_room"].get(room, False),
        selected_detector=st.session_state["selected_detector"],
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


