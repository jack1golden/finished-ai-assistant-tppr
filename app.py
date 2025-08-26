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

from utils import facility          # utils/facility.py (updated below)
from utils import ai as safety_ai   # your existing utils/ai.py

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

# ---------- read query params (hotspots still set URL; we read but don't rely on them) ----------
qp = st.query_params
if "room" in qp and qp["room"]:
    st.session_state["current_room"] = unquote(qp["room"])
if "det" in qp and qp["det"]:
    st.session_state["selected_detector"] = unquote(qp["det"])

# ---------- header ----------
c1, c2 = st.columns([6, 1])
with c1:
    st.title("OBW — Pharma Safety HMI (AI-First)")
with c2:
    logo = IMAGES / "logo.png"
    if logo.exists():
        st.image(str(logo), use_container_width=True)

# ---------- TABS ----------
tab_overview, tab_live, tab_ai, tab_reports, tab_settings = st.tabs(
    ["Overview", "Live Data", "AI Assistant", "Reports", "Settings"]
)

# ======================================================
# Overview tab
# ======================================================
with tab_overview:
    st.markdown('<div class="obw-bar">🏭 Facility Overview</div>', unsafe_allow_html=True)

    # Visual only: overview image with hotspots (kept for look)
    facility.render_overview_image_only(IMAGES)

    # Working navigation buttons
    st.caption("Quick navigation")
    rooms = list(facility.DETECTORS.keys())
    cols = st.columns(6)
    for i, room in enumerate(rooms):
        with cols[i % 6]:
            if st.button(room, key=f"room_btn_{room}"):
                st.session_state["current_room"] = room
                dets = facility.get_detectors_for(room)
                st.session_state["selected_detector"] = dets[0]["label"] if dets else None
                st.query_params.update({"room": room, "det": st.session_state["selected_detector"] or ""})
                # Instead of switching tabs, we render the room inline, right below:
                st.session_state["__show_room_inline"] = True

    # Inline room render (so you don't have to switch tabs)
    if st.session_state.get("__show_room_inline") and st.session_state["current_room"] != "Overview":
        room = st.session_state["current_room"]
        st.markdown('<div class="obw-smallbar">🚪 Room view (inline)</div>', unsafe_allow_html=True)

        # 1) visual room image (hotspots kept for look)
        facility.render_room_image_only(
            images_dir=IMAGES,
            room=room,
            simulate=st.session_state["simulate_by_room"].get(room, False),
            selected_detector=st.session_state["selected_detector"],
            ops=st.session_state["room_ops"].get(room, {})
        )

        # 2) working detector buttons
        dets = facility.get_detectors_for(room)
        if dets:
            st.markdown('<div class="obw-smallbar">🎛 Choose detector</div>', unsafe_allow_html=True)
            cols2 = st.columns(len(dets))
            for i, d in enumerate(dets):
                with cols2[i]:
                    if st.button(d["label"], key=f"det_btn_inline_{room}_{d['label']}"):
                        st.session_state["selected_detector"] = d["label"]
                        st.query_params.update({"room": room, "det": d["label"]})
                        st.session_state["__force_room_refresh"] = True

        # 3) data panel (chart + thresholds + AI)
        if st.session_state.get("selected_detector"):
            facility.render_room_data_panel(
                images_dir=IMAGES,
                room=room,
                selected_detector=st.session_state["selected_detector"],
                simulate=st.session_state["simulate_by_room"].get(room, False),
                ai_force_rule=st.session_state["force_rule_ai"],
                ops=st.session_state["room_ops"].get(room, {}),
                brand={"navy": "#0a2342", "red": "#d81f26"},
            )
            st.session_state["room_ops"][room] = {}

# ======================================================
# Live Data tab (fallback)
# ======================================================
with tab_live:
    st.markdown('<div class="obw-bar">📡 Live Data</div>', unsafe_allow_html=True)
    rooms = list(facility.DETECTORS.keys())
    live_room = st.selectbox("Room", rooms,
        index=rooms.index(st.session_state["current_room"]) if st.session_state["current_room"] in rooms else 0)
    dets = facility.get_detectors_for(live_room)
    labels = [d["label"] for d in dets]
    if labels:
        live_det = st.selectbox("Detector", labels,
            index=labels.index(st.session_state["selected_detector"]) if st.session_state.get("selected_detector") in labels else 0)
    else:
        live_det = None

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
# AI / Reports / Settings
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







