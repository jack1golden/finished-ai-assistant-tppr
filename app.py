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

# ---------- sidebar: robust navigation fallback ----------
with st.sidebar:
    st.markdown("### Navigation")
    rooms = ["Overview", "Room 1", "Room 2", "Room 3", "Room Production", "Room Production 2", "Room 12 17"]
    idx = rooms.index(st.session_state["current_room"]) if st.session_state["current_room"] in rooms else 0
    sel = st.selectbox("Go to…", rooms, index=idx)
    if sel == "Overview":
        st.session_state["current_room"] = None
        st.session_state["selected_detector"] = None
        st.query_params.clear()
    else:
        st.session_state["current_room"] = sel
        st.query_params.update({"room": sel, **({"det": st.session_state["selected_detector"]} if st.session_state["selected_detector"] else {})})

    if st.session_state["current_room"] and st.session_state["current_room"] != "Overview":
        det_list = facility.get_detectors_for(st.session_state["current_room"])
        if det_list:
            labels = [d["label"] for d in det_list]
            current = st.session_state.get("selected_detector") or labels[0]
            chosen = st.radio("Detector", labels, index=labels.index(current))
            if chosen != st.session_state.get("selected_detector"):
                st.session_state["selected_detector"] = chosen
                st.query_params.update({"room": st.session_state["current_room"], "det": chosen})

        st.write("---")
        c1, c2 = st.columns(2)
        if c1.button("💨 Simulate", use_container_width=True):
            st.session_state["simulate_by_room"][st.session_state["current_room"]] = True
        if c2.button("⏹ Reset", use_container_width=True):
            st.session_state["simulate_by_room"][st.session_state["current_room"]] = False

# ---------- header ----------
cols = st.columns([5, 1])
with cols[0]:
    st.title("Pharma Safety HMI — AI First")
with cols[1]:
    logo = IMAGES / "logo.png"
    if logo.exists():
        st.image(str(logo), caption="", use_container_width=True)

# ---------- main area ----------
room = st.session_state["current_room"]

if not room:
    st.subheader("🏭 Facility Overview (2.5D)")
    facility.render_overview(IMAGES)
    st.markdown("#### Quick open")
    bcols = st.columns(6)
    for i, rn in enumerate(["Room 1", "Room 2", "Room 3", "Room Production", "Room Production 2", "Room 12 17"]):
        if bcols[i].button(rn, key=f"open_{rn}"):
            st.session_state["current_room"] = rn
            st.query_params.update({"room": rn})
            st.rerun()  # navigate immediately
else:
    st.subheader(f"🚪 {room}")
    simulate_flag = st.session_state["simulate_by_room"].get(room, False)

    facility.render_room(
        images_dir=IMAGES,
        room=room,
        simulate=simulate_flag,
        selected_detector=st.session_state.get("selected_detector"),
    )

    st.write("---")
    if st.button("⬅️ Back to Overview"):
        st.session_state["current_room"] = None
        st.session_state["selected_detector"] = None
        st.query_params.clear()
        st.rerun()


