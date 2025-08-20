from pathlib import Path
from urllib.parse import unquote

import streamlit as st
from utils import facility

# ─────────────────────────────
# App config & paths
# ─────────────────────────────
st.set_page_config(page_title="Pharma Safety HMI — AI First", layout="wide")
HERE = Path(__file__).parent
IMAGES = HERE / "images"
IMAGES.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────
# Session defaults
# ─────────────────────────────
st.session_state.setdefault("nav_tab", "Home")
st.session_state.setdefault("current_room", None)
st.session_state.setdefault("selected_detector", None)
st.session_state.setdefault("simulate_by_room", {})     # {room: bool}
st.session_state.setdefault("cal_overview", False)
st.session_state.setdefault("cal_room", False)
st.session_state.setdefault("cal_overview_room", "Room 1")  # which room to place on Overview
st.session_state.setdefault("cal_room_detector", None)      # which detector to place in a room

# ─────────────────────────────
# URL query → session sync
# (supports ?room=...&det=...)
# ─────────────────────────────
qp = st.query_params
if "room" in qp:
    st.session_state["nav_tab"] = unquote(qp["room"])
    st.session_state["current_room"] = st.session_state["nav_tab"] if st.session_state["nav_tab"] not in ("Home", "Overview", "Settings", "AI Safety Assistant") else None
if "det" in qp:
    st.session_state["selected_detector"] = unquote(qp["det"])

# ─────────────────────────────
# Sidebar: navigation + calibration toggles
# ─────────────────────────────
tabs = [
    "Home", "Overview",
    "Room 1", "Room 2", "Room 3", "Room 12 17", "Room Production", "Room Production 2",
    "Settings", "AI Safety Assistant",
]
st.session_state["nav_tab"] = st.sidebar.radio(
    "🔎 Navigation",
    tabs,
    index=tabs.index(st.session_state["nav_tab"]) if st.session_state["nav_tab"] in tabs else 0,
    key="nav_tabs_radio",
)

with st.sidebar:
    st.markdown("### 🧭 Calibration")
    st.session_state["cal_overview"] = st.checkbox("Calibrate Overview", value=st.session_state["cal_overview"], key="cal_ov_chk")
    st.session_state["cal_room"] = st.checkbox("Calibrate Room", value=st.session_state["cal_room"], key="cal_rm_chk")

    if st.session_state["cal_overview"]:
        st.session_state["cal_overview_room"] = st.selectbox(
            "Room to place on Overview",
            ["Room 1", "Room 2", "Room 3", "Room 12 17", "Room Production", "Room Production 2"],
            index=["Room 1", "Room 2", "Room 3", "Room 12 17", "Room Production", "Room Production 2"].index(st.session_state["cal_overview_room"]),
            key="cal_ov_room_sel"
        )

# ─────────────────────────────
# Page routing
# ─────────────────────────────
tab = st.session_state["nav_tab"]

if tab == "Home":
    # Home / Cover with logo
    colL, colR = st.columns([2, 1], gap="large")
    with colL:
        facility.render_logo(IMAGES)  # uses images/logo.png if present
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
            st.info("Using a temporary logo. Add **images/logo.png** (your 3D artwork) to replace it.")

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

    # Top controls for simulation & back
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
            st.query_params.clear()
            st.rerun()

    # Side-by-side: left = image with detector buttons; right = live chart + chat
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
