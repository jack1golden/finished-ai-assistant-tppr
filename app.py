# app.py
from __future__ import annotations
import sys
from pathlib import Path
from urllib.parse import unquote

import streamlit as st

# ---------- paths ----------
HERE = Path(__file__).parent.resolve()
IMAGES = HERE / "images"
IMAGES.mkdir(parents=True, exist_ok=True)

UTILS_DIR = HERE / "utils"
if str(UTILS_DIR) not in sys.path:
    sys.path.insert(0, str(UTILS_DIR))

from utils import facility          # utils/facility.py
from utils import ai as safety_ai   # utils/ai.py

# ---------- theme ----------
OBW_NAVY = "#0a2342"
OBW_RED = "#d81f26"

st.set_page_config(page_title="OBW — Pharma Safety HMI (AI First)", layout="wide")
st.markdown(f"""
<style>
  .block-container {{ padding-top: 1rem; }}
  .obw-bar {{
    background:{OBW_NAVY}; color:#fff; padding:8px 12px; border-radius:10px;
    display:inline-block; font-weight:700; margin-bottom: .25rem;
  }}
  .obw-smallbar {{
    background:{OBW_NAVY}; color:#fff; padding:4px 8px; border-radius:8px;
    display:inline-block; font-weight:700; margin:.25rem 0;
  }}
  .stTabs [data-baseweb="tab-list"] {{ background:{OBW_NAVY}; padding:6px 8px; border-radius:10px; }}
  .stTabs [data-baseweb="tab"] {{ color:#fff !important; font-weight:600; }}
  .stTabs [aria-selected="true"] {{ border-bottom:3px solid {OBW_RED} !important; }}
  .stButton > button {{
    background:{OBW_NAVY}; color:#fff; border:1px solid {OBW_NAVY};
    border-radius:10px; font-weight:700; width:100%;
  }}
  .stButton > button:hover {{ background:{OBW_RED}; border-color:{OBW_RED}; }}
  .ghost-note {{ color:#6b7280; font-size:0.9rem; margin-top:.25rem; }}
</style>
""", unsafe_allow_html=True)

# ---------- session defaults ----------
def _sset(k, v):
    if k not in st.session_state:
        st.session_state[k] = v

_sset("current_room", "Overview")
_sset("selected_detector", None)
_sset("simulate_by_room", {})   # {room: bool}
_sset("room_ops", {})           # {room: {...}}
_sset("force_rule_ai", False)

# ---------- read query params (from visual hotspots; non-blocking if absent) ----------
qp = st.query_params
if "room" in qp and qp["room"]:
    st.session_state["current_room"] = unquote(qp["room"])
if "det" in qp and qp["det"]:
    st.session_state["selected_detector"] = unquote(qp["det"])

# ---------- sanitize detector for current room ----------
def _sanitize_detector():
    room = st.session_state.get("current_room")
    if not room or room == "Overview":
        st.session_state["selected_detector"] = None
        return
    labels = [d["label"] for d in facility.get_detectors_for(room)]
    cur = st.session_state.get("selected_detector")
    if labels and cur not in labels:
        st.session_state["selected_detector"] = labels[0]

_sanitize_detector()

# ---------- header ----------
c1, c2 = st.columns([6, 1])
with c1:
    st.title("OBW — Pharma Safety HMI (AI-First)")
with c2:
    logo = IMAGES / "logo.png"
    if logo.exists():
        st.image(str(logo), use_container_width=True)

# ---------- tabs ----------
tab_overview, tab_room, tab_live, tab_ai, tab_reports, tab_settings = st.tabs(
    ["Overview", "Room", "Live Data", "AI Assistant", "Reports", "Settings"]
)

# ======================================================
# Overview (visual hotspots on the image + WORKING buttons underneath)
# ======================================================
with tab_overview:
    st.markdown('<div class="obw-bar">🏭 Facility Overview</div>', unsafe_allow_html=True)

    # 1) Visual only: shows your overview image with translucent hotspot boxes (non-clickable except URL query)
    facility.render_overview_image_only(IMAGES)

    # 2) WORKING navigation buttons (reliable)
    st.caption("Quick navigation")
    rooms = list(facility.DETECTORS.keys())
    cols = st.columns(6)
    for i, room in enumerate(rooms):
        with cols[i % 6]:
            if st.button(room, key=f"room_btn_{room}"):
                st.session_state["current_room"] = room
                # default detector for that room
                dets = facility.get_detectors_for(room)
                st.session_state["selected_detector"] = dets[0]["label"] if dets else None
                st.query_params.update({"room": room, "det": st.session_state["selected_detector"] or ""})
                st.rerun()

# ======================================================
# Room (visual hotspots on the image + WORKING detector buttons underneath)
# ======================================================
with tab_room:
    # Top operator strip
    ch1, ch2, ch3, ch4 = st.columns([2,2,2,2])
    with ch1:
        if st.button("⬅ Back to overview"):
            st.session_state["current_room"] = "Overview"
            st.session_state["selected_detector"] = None
            st.query_params.clear()
            st.rerun()
    with ch2:
        if st.button("💨 Simulate leak"):
            r = st.session_state["current_room"]
            st.session_state["simulate_by_room"][r] = True
    with ch3:
        if st.button("🛑 Close shutters"):
            r = st.session_state["current_room"]
            st.session_state["room_ops"].setdefault(r, {})["close_shutter"] = True
    with ch4:
        if st.button("🌬 Ventilation"):
            r = st.session_state["current_room"]
            st.session_state["room_ops"].setdefault(r, {})["ventilate"] = True

    room = st.session_state["current_room"]
    if room == "Overview":
        st.info("Pick a room from Overview.")
    else:
        # 1) Visual only: your room image with detector tags (hotspots)
        facility.render_room_image_only(IMAGES, room,
                                        simulate=st.session_state["simulate_by_room"].get(room, False),
                                        selected_detector=st.session_state["selected_detector"],
                                        ops=st.session_state["room_ops"].get(room, {}))

        # 2) WORKING detector buttons underneath
        dets = facility.get_detectors_for(room)
        if not dets:
            st.warning("No detectors defined for this room.")
        else:
            st.markdown('<div class="obw-smallbar">🎛 Choose detector</div>', unsafe_allow_html=True)
            cols = st.columns(len(dets))
            for i, d in enumerate(dets):
                with cols[i]:
                    if st.button(d["label"], key=f"det_btn_{room}_{d['label']}"):
                        st.session_state["selected_detector"] = d["label"]
                        st.query_params.update({"room": room, "det": d["label"]})
                        st.rerun()

        # 3) Data panel (live chart + thresholds + Honeywell + AI)
        if st.session_state.get("selected_detector"):
            facility.render_room_data_panel(
                images_dir=IMAGES,
                room=room,
                selected_detector=st.session_state["selected_detector"],
                simulate=st.session_state["simulate_by_room"].get(room, False),
                ai_force_rule=st.session_state["force_rule_ai"],
                ops=st.session_state["room_ops"].get(room, {}),
                brand={"navy": OBW_NAVY, "red": OBW_RED},
            )
            # clear one-shot ops
            st.session_state["room_ops"][room] = {}

# ======================================================
# Live Data (fallback demo path that always works)
# ======================================================
with tab_live:
    st.markdown('<div class="obw-bar">📡 Live Data</div>', unsafe_allow_html=True)
    rooms = list(facility.DETECTORS.keys())
    live_room = st.selectbox("Room", rooms,
                             index=rooms.index(st.session_state["current_room"]) if st.session_state["current_room"] in rooms else 0)
    dets = facility.get_detectors_for(live_room)
    labels = [d["label"] for d in dets]
    live_det = st.selectbox("Detector", labels,
                            index=labels.index(st.session_state["selected_detector"]) if st.session_state["selected_detector"] in labels else 0 if labels else None) if labels else None

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("💨 Simulate leak", key=f"live_sim_{live_room}"):
        st.session_state["simulate_by_room"][live_room] = True
    if c2.button("🛑 Shutters", key=f"live_shut_{live_room}"):
        st.session_state["room_ops"].setdefault(live_room, {})["close_shutter"] = True
    if c3.button("🌬 Ventilation", key=f"live_vent_{live_room}"):
        st.session_state["room_ops"].setdefault(live_room, {})["ventilate"] = True
    if c4.button("♻ Reset", key=f"live_reset_{live_room}"):
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

# ======================================================
# AI Assistant / Reports / Settings
# ======================================================
with tab_ai:
    st.markdown('<div class="obw-bar">🤖 Global AI Assistant</div>', unsafe_allow_html=True)
    if q := st.chat_input("Ask anything about safety, alarms, or policy…", key="chat_global"):
        st.chat_message("user").write(q)
        snapshot = facility.build_facility_snapshot()
        ans = safety_ai.ask_ai(q, context={"facility": snapshot}, force_rule=st.session_state["force_rule_ai"])
        st.chat_message("ai").write(ans)

with tab_reports:
    st.markdown('<div class="obw-bar">📜 AI Event Log</div>', unsafe_allow_html=True)
    log = st.session_state.get("ai_log", {})
    if not log:
        st.info("No events yet.")
    else:
        for rm, entries in log.items():
            st.markdown(f"#### {rm}")
            for e in reversed(entries[-15:]):
                st.markdown(f"- **{facility.ts_str(e['ts'])}** — {e['text']}")

with tab_settings:
    st.markdown('<div class="obw-bar">⚙ Settings</div>', unsafe_allow_html=True)
    st.session_state["force_rule_ai"] = st.toggle("Force rule-based AI (no API calls)",
                                                  value=st.session_state.get("force_rule_ai", False))
    if st.button("Run AI self-test"):
        ans = safety_ai.ask_ai("Write a haiku about an H₂S alarm.",
                               context={"room": "Room 1", "gas": "H₂S", "status": "ALARM"},
                               force_rule=st.session_state["force_rule_ai"])
        st.write(ans)






