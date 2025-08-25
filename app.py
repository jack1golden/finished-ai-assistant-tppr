# app.py
from __future__ import annotations
import sys
from pathlib import Path
from urllib.parse import unquote

import streamlit as st
import streamlit.components.v1 as components

# ---------- paths / imports ----------
HERE = Path(__file__).parent.resolve()
IMAGES = HERE / "images"
IMAGES.mkdir(parents=True, exist_ok=True)

UTILS_DIR = HERE / "utils"
if str(UTILS_DIR) not in sys.path:
    sys.path.insert(0, str(UTILS_DIR))

from utils import facility          # utils/facility.py
from utils import ai as safety_ai   # utils/ai.py

st.set_page_config(page_title="OBW — Pharma Safety HMI (AI First)", layout="wide")

# ---------- OBW Theme ----------
OBW_NAVY = "#0a2342"
OBW_RED = "#d81f26"
OBW_BLACK = "#000000"
WHITE = "#ffffff"

st.markdown(f"""
<style>
.block-container {{ background:{WHITE} !important; }}
.stTabs [data-baseweb="tab-list"] {{ background:{OBW_NAVY}; padding: 6px 8px; border-radius: 10px; }}
.stTabs [data-baseweb="tab"] {{ color: #ffffff !important; font-weight: 600; }}
.stTabs [aria-selected="true"] {{ border-bottom: 3px solid {OBW_RED} !important; }}
.obw-bar {{ background:{OBW_NAVY}; color:#ffffff; padding:8px 12px; border-radius:10px; display:inline-block; font-weight:700; }}
.stButton > button {{ background: {OBW_NAVY}; color:#ffffff; border: 1px solid {OBW_NAVY}; border-radius: 8px; }}
.stButton > button:hover {{ background: {OBW_RED}; border-color: {OBW_RED}; }}
.obw-smallbar {{ background:{OBW_NAVY}; color:#ffffff; padding:4px 8px; border-radius:8px; display:inline-block; font-weight:700; }}
</style>
""", unsafe_allow_html=True)

# ---------- session defaults ----------
def _d(k, v):
    if k not in st.session_state:
        st.session_state[k] = v

_d("current_room", "Overview")
_d("selected_detector", None)
_d("simulate_by_room", {})   # {room: bool}
_d("force_rule_ai", False)   # force rule-based
_d("room_ops", {})

# ---------- query params ----------
qp = st.query_params
if "room" in qp and qp["room"]:
    st.session_state["current_room"] = unquote(qp["room"])
if "det" in qp and qp["det"]:
    st.session_state["selected_detector"] = unquote(qp["det"])

# ---------- sanitize detector ----------
def _sanitize_selected_detector():
    room = st.session_state.get("current_room")
    if not room or room == "Overview":
        st.session_state["selected_detector"] = None
        return
    dets = facility.get_detectors_for(room) or []
    labels = [d["label"] for d in dets]
    cur = st.session_state.get("selected_detector")
    if not labels:
        st.session_state["selected_detector"] = None
        return
    if cur not in labels:
        st.session_state["selected_detector"] = labels[0]

_sanitize_selected_detector()

# ---------- header ----------
c1, c2 = st.columns([6, 1])
with c1:
    st.title("OBW — Pharma Safety HMI (AI-First)")
with c2:
    logo_path = IMAGES / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)

# ---------- tabs ----------
tab_overview, tab_room, tab_live, tab_ai, tab_logs, tab_settings = st.tabs(
    ["Overview", "Room", "Live Data", "AI Assistant", "Logs & Reports", "Settings"]
)

# ---------- Overview tab ----------
with tab_overview:
    st.markdown(f'<div class="obw-bar">🏭 Facility Overview</div>', unsafe_allow_html=True)
    facility.render_overview(IMAGES)

# ---------- Room tab ----------
with tab_room:
    rooms = list(facility.DETECTORS.keys())
    room = st.selectbox("Select room", rooms, index=rooms.index(st.session_state["current_room"]) if st.session_state["current_room"] in rooms else 0, key="room_sel")
    dets = facility.get_detectors_for(room)
    labels = [d["label"] for d in dets]
    det = st.selectbox("Select detector", labels, index=labels.index(st.session_state.get("selected_detector")) if st.session_state.get("selected_detector") in labels else 0, key="det_sel") if labels else None

    st.session_state["current_room"] = room
    st.session_state["selected_detector"] = det

    st.write("---")
    st.markdown('<div class="obw-smallbar">🎛 Operator Console</div>', unsafe_allow_html=True)
    oc1, oc2, oc3, oc4 = st.columns(4)
    if oc1.button("💨 Simulate leak", key=f"sim_{room}"):
        st.session_state["simulate_by_room"][room] = True
    if oc2.button("🛑 Close shutters", key=f"shut_{room}"):
        st.session_state["room_ops"].setdefault(room, {})["close_shutter"] = True
    if oc3.button("🌬 Ventilation", key=f"vent_{room}"):
        st.session_state["room_ops"].setdefault(room, {})["ventilate"] = True
    if oc4.button("♻️ Reset", key=f"reset_{room}"):
        st.session_state["room_ops"].setdefault(room, {})["reset"] = True

    if room and det:
        facility.render_room(
            images_dir=IMAGES,
            room=room,
            simulate=st.session_state["simulate_by_room"].get(room, False),
            selected_detector=det,
            ai_force_rule=st.session_state["force_rule_ai"],
            ops=st.session_state["room_ops"].get(room, {}),
            brand={"navy": OBW_NAVY, "red": OBW_RED}
        )
        st.session_state["room_ops"][room] = {}

# ---------- Live Data tab ----------
with tab_live:
    st.markdown('<div class="obw-bar">📡 Live Data — Quick Controls</div>', unsafe_allow_html=True)
    rooms = list(facility.DETECTORS.keys())
    live_room = st.selectbox("Room", rooms, index=rooms.index(st.session_state["current_room"]) if st.session_state["current_room"] in rooms else 0, key="live_room")
    labels = [d["label"] for d in facility.get_detectors_for(live_room)]
    live_det = st.selectbox("Detector", labels, index=labels.index(st.session_state["selected_detector"]) if st.session_state["selected_detector"] in labels else 0, key="live_det") if labels else None

    oc1, oc2, oc3, oc4 = st.columns(4)
    if oc1.button("💨 Simulate leak", key=f"live_sim_{live_room}"):
        st.session_state["simulate_by_room"][live_room] = True
    if oc2.button("🛑 Shutters", key=f"live_shut_{live_room}"):
        st.session_state["room_ops"].setdefault(live_room, {})["close_shutter"] = True
    if oc3.button("🌬 Ventilation", key=f"live_vent_{live_room}"):
        st.session_state["room_ops"].setdefault(live_room, {})["ventilate"] = True
    if oc4.button("♻️ Reset", key=f"live_reset_{live_room}"):
        st.session_state["room_ops"].setdefault(live_room, {})["reset"] = True

    if live_det:
        facility.render_live_only(
            images_dir=IMAGES,
            room=live_room,
            selected_detector=live_det,
            simulate=st.session_state["simulate_by_room"].get(live_room, False),
            ai_force_rule=st.session_state["force_rule_ai"],
            ops=st.session_state["room_ops"].get(live_room, {}),
            brand={"navy": OBW_NAVY, "red": OBW_RED}
        )
        st.session_state["room_ops"][live_room] = {}

# ---------- AI Assistant tab ----------
with tab_ai:
    st.markdown('<div class="obw-bar">🤖 Global AI Assistant</div>', unsafe_allow_html=True)
    if p := st.chat_input("Ask a facility-wide question…", key="chat_global"):
        st.chat_message("user").write(p)
        snapshot = facility.build_facility_snapshot()
        answer = safety_ai.ask_ai(
            p,
            context={"facility": snapshot, "room": "All"},
            force_rule=st.session_state["force_rule_ai"]
        )
        st.chat_message("ai").write(answer)

# ---------- Logs & Reports ----------
with tab_logs:
    st.markdown('<div class="obw-bar">📜 AI Event Log</div>', unsafe_allow_html=True)
    logs = st.session_state.get("ai_log", {})
    if not logs:
        st.info("No events yet.")
    else:
        for rm, entries in logs.items():
            st.markdown(f"#### {rm}")
            for e in reversed(entries[-12:]):
                st.markdown(f"- **{facility.ts_str(e['ts'])}** — {e['text']}")

# ---------- Settings ----------
with tab_settings:
    st.markdown('<div class="obw-bar">⚙️ Settings</div>', unsafe_allow_html=True)
    st.session_state["force_rule_ai"] = st.toggle(
        "Force rule-based (no API calls)",
        value=st.session_state.get("force_rule_ai", False)
    )
    if st.button("Run AI self-test"):
        ctx = {"room": "Room 1", "gas": "NH₃", "value": 30.0, "status": "WARN"}
        answer = safety_ai.ask_ai("Write a haiku about an H₂S alarm.", ctx,
                                  force_rule=st.session_state["force_rule_ai"])
        st.write(answer)




