# app.py
# Repo tree expected:
# finished-ai-assistant-tppr/
# ├─ app.py
# ├─ requirements.txt
# ├─ images/
# │  ├─ Overview.png
# │  ├─ Room 1.png
# │  ├─ Room 2 (1).png
# │  ├─ Room 3 (1).png
# │  ├─ Room 12 17.png
# │  ├─ Room Production.png
# │  ├─ Room Production 2.png
# │  └─ logo.png    (optional)
# └─ utils/
#    ├─ __init__.py (empty is fine)
#    └─ facility.py (the renderer)

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote

import streamlit as st

# ---------- import utils/facility robustly ----------
HERE = Path(__file__).parent.resolve()
IMAGES = HERE / "images"
IMAGES.mkdir(parents=True, exist_ok=True)

UTILS_DIR = HERE / "utils"
if str(UTILS_DIR) not in sys.path:
    sys.path.insert(0, str(UTILS_DIR))

from utils import facility  # <- keep file named utils/facility.py

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
    st.session_state["current_room"] = unquote(qp["room"])
    st.session_state["nav"] = st.session_state["current_room"]
if "det" in qp and qp["det"]:
    st.session_state["selected_detector"] = unquote(qp["det"])

# ---------- header: tabs + logo ----------
cols = st.columns([5, 1])
with cols[0]:
    tabs = st.tabs(["Overview", "Room 1", "Room 2", "Room 3", "Room Production",
                    "Room Production 2", "Room 12 17", "Settings", "AI"])
with cols[1]:
    logo = IMAGES / "logo.png"
    if logo.exists():
        st.image(str(logo), caption="", use_container_width=True)

# A tiny helper to route when a tab becomes active
def _activate(name: str):
    st.session_state["nav"] = name
    st.session_state["current_room"] = None if name == "Overview" else name
    st.session_state["selected_detector"] = None
    if name == "Overview":
        st.query_params.clear()
    else:
        st.query_params.update({"room": name})

# ---------- render based on active tab ----------
active = st.session_state["nav"]

# We render all tabs, but only show body under the one that is active
with tabs[0]:
    if active == "Overview":
        st.title("🏭 Facility Overview (2.5D)")
        facility.render_overview(IMAGES)
        # Native backup navigation buttons (in case HTML hotspots are blocked):
        st.markdown("#### Quick open (backup)")
        bcols = st.columns(6)
        labels = ["Room 1", "Room 2", "Room 3", "Room Production", "Room Production 2", "Room 12 17"]
        for i, rn in enumerate(labels):
            if bcols[i].button(rn, key=f"open_{rn}"):
                _activate(rn)
                st.rerun()

with tabs[1]:
    if active == "Room 1":
        st.title("🚪 Room 1")
        c1, c2, c3 = st.columns([1, 1, 2])
        if c1.button("💨 Simulate Gas Leak", key="sim_room1"):
            st.session_state["simulate_by_room"]["Room 1"] = True
            st.rerun()
        if c2.button("⏹ Reset", key="reset_room1"):
            st.session_state["simulate_by_room"]["Room 1"] = False
            st.rerun()
        if c3.button("⬅️ Back to Overview", key="back_room1"):
            _activate("Overview")
            st.rerun()
        facility.render_room(
            IMAGES, "Room 1",
            simulate=st.session_state["simulate_by_room"].get("Room 1", False),
            selected_detector=st.session_state["selected_detector"],
        )

with tabs[2]:
    if active == "Room 2":
        st.title("🚪 Room 2")
        c1, c2, c3 = st.columns([1, 1, 2])
        if c1.button("💨 Simulate Gas Leak", key="sim_room2"):
            st.session_state["simulate_by_room"]["Room 2"] = True
            st.rerun()
        if c2.button("⏹ Reset", key="reset_room2"):
            st.session_state["simulate_by_room"]["Room 2"] = False
            st.rerun()
        if c3.button("⬅️ Back to Overview", key="back_room2"):
            _activate("Overview")
            st.rerun()
        facility.render_room(
            IMAGES, "Room 2",
            simulate=st.session_state["simulate_by_room"].get("Room 2", False),
            selected_detector=st.session_state["selected_detector"],
        )

with tabs[3]:
    if active == "Room 3":
        st.title("🚪 Room 3")
        c1, c2, c3 = st.columns([1, 1, 2])
        if c1.button("💨 Simulate Gas Leak", key="sim_room3"):
            st.session_state["simulate_by_room"]["Room 3"] = True
            st.rerun()
        if c2.button("⏹ Reset", key="reset_room3"):
            st.session_state["simulate_by_room"]["Room 3"] = False
            st.rerun()
        if c3.button("⬅️ Back to Overview", key="back_room3"):
            _activate("Overview")
            st.rerun()
        facility.render_room(
            IMAGES, "Room 3",
            simulate=st.session_state["simulate_by_room"].get("Room 3", False),
            selected_detector=st.session_state["selected_detector"],
        )

with tabs[4]:
    if active == "Room Production":
        st.title("🚪 Production 1")
        c1, c2, c3 = st.columns([1, 1, 2])
        if c1.button("💨 Simulate Gas Leak", key="sim_prod1"):
            st.session_state["simulate_by_room"]["Room Production"] = True
            st.rerun()
        if c2.button("⏹ Reset", key="reset_prod1"):
            st.session_state["simulate_by_room"]["Room Production"] = False
            st.rerun()
        if c3.button("⬅️ Back to Overview", key="back_prod1"):
            _activate("Overview")
            st.rerun()
        facility.render_room(
            IMAGES, "Room Production",
            simulate=st.session_state["simulate_by_room"].get("Room Production", False),
            selected_detector=st.session_state["selected_detector"],
        )

with tabs[5]:
    if active == "Room Production 2":
        st.title("🚪 Production 2")
        c1, c2, c3 = st.columns([1, 1, 2])
        if c1.button("💨 Simulate Gas Leak", key="sim_prod2"):
            st.session_state["simulate_by_room"]["Room Production 2"] = True
            st.rerun()
        if c2.button("⏹ Reset", key="reset_prod2"):
            st.session_state["simulate_by_room"]["Room Production 2"] = False
            st.rerun()
        if c3.button("⬅️ Back to Overview", key="back_prod2"):
            _activate("Overview")
            st.rerun()
        facility.render_room(
            IMAGES, "Room Production 2",
            simulate=st.session_state["simulate_by_room"].get("Room Production 2", False),
            selected_detector=st.session_state["selected_detector"],
        )

with tabs[6]:
    if active == "Room 12 17":
        st.title("🚪 Room 12/17")
        c1, c2, c3 = st.columns([1, 1, 2])
        if c1.button("💨 Simulate Gas Leak", key="sim_r1217"):
            st.session_state["simulate_by_room"]["Room 12 17"] = True
            st.rerun()
        if c2.button("⏹ Reset", key="reset_r1217"):
            st.session_state["simulate_by_room"]["Room 12 17"] = False
            st.rerun()
        if c3.button("⬅️ Back to Overview", key="back_r1217"):
            _activate("Overview")
            st.rerun()
        facility.render_room(
            IMAGES, "Room 12 17",
            simulate=st.session_state["simulate_by_room"].get("Room 12 17", False),
            selected_detector=st.session_state["selected_detector"],
        )

with tabs[7]:
    if active == "Settings":
        st.title("⚙️ Settings")
        facility.render_settings()

with tabs[8]:
    if active == "AI":
        st.title("🤖 AI Safety Assistant")
        facility.render_ai_chat()
