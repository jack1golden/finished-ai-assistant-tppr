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
from utils import history           # utils/history.py  (6-month data)

# ---------- theme ----------
OBW_NAVY = "#0a2342"
OBW_RED = "#d81f26"

st.set_page_config(page_title="OBW — Pharma Safety HMI (AI First)", layout="wide")
st.markdown(f"""
<style>
  .block-container {{ padding-top: 1rem; }}
  .obw-bar {{
    background:{OBW_NAVY}; color:#fff; padding:8px 12px; border-radius:10px;
    display:inline-block; font-weight:700; margin-bottom:.5rem;
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
_sset("room_ops", {})           # {room: {...}} (close_shutter/ventilate/reset)

# ---------- query params (hotspots update the URL; we read them) ----------
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

# ---------- init 6 months of history (with weekly spikes) ----------
# 180 days, 15-minute resolution to keep memory light & charts smooth
history.init_if_needed(facility.DETECTORS, days=180, step_minutes=15, spikes_per_week=1)

# ---------- tabs ----------
tab_overview, tab_live, tab_settings = st.tabs(["Overview", "Live Data", "Settings"])

# ======================================================
# Overview (image + hotspots + WORKING buttons + inline room)
# ======================================================
with tab_overview:
    st.markdown('<div class="obw-bar">🏭 Facility Overview</div>', unsafe_allow_html=True)

    # Visual overview image with hotspots (for look)
    facility.render_overview_image_only(IMAGES)

    # Working navigation buttons under the image
    st.caption("Quick navigation")
    rooms = list(facility.DETECTORS.keys())
    cols = st.columns(min(6, len(rooms)) or 1)
    for i, room in enumerate(rooms):
        with cols[i % len(cols)]:
            if st.button(room, key=f"room_btn_{room}"):
                st.session_state["current_room"] = room
                dets = facility.get_detectors_for(room)
                st.session_state["selected_detector"] = dets[0]["label"] if dets else None
                st.query_params.update({"room": room, "det": st.session_state["selected_detector"] or ""})
                st.session_state["__show_room_inline"] = True

    # Inline room view (so no tab-hopping)
    if st.session_state.get("__show_room_inline") and st.session_state["current_room"] != "Overview":
        room = st.session_state["current_room"]
        st.markdown('<div class="obw-smallbar">🚪 Room view (inline)</div>', unsafe_allow_html=True)

        # Room image with detector pins (visual) + gas cloud/shutter reactions
        facility.render_room_image_only(
            images_dir=IMAGES,
            room=room,
            simulate=st.session_state["simulate_by_room"].get(room, False),
            selected_detector=st.session_state["selected_detector"],
            ops=st.session_state["room_ops"].get(room, {}),
        )

        # Detector buttons (WORKING)
        dets = facility.get_detectors_for(room)
        if dets:
            st.markdown('<div class="obw-smallbar">🎛 Choose detector</div>', unsafe_allow_html=True)
            cols2 = st.columns(len(dets))
            for i, d in enumerate(dets):
                with cols2[i]:
                    if st.button(d["label"], key=f"det_btn_{room}_{d['label']}"):
                        st.session_state["selected_detector"] = d["label"]
                        st.query_params.update({"room": room, "det": d["label"]})

        # Controls for simulate/shutters/vent/reset
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("💨 Simulate leak", key=f"sim_{room}"):
            st.session_state["simulate_by_room"][room] = True
        if c2.button("🛑 Close shutter", key=f"shut_{room}"):
            st.session_state["room_ops"].setdefault(room, {})["close_shutter"] = True
        if c3.button("🌬 Ventilation", key=f"vent_{room}"):
            st.session_state["room_ops"].setdefault(room, {})["ventilate"] = True
        if c4.button("♻ Reset", key=f"reset_{room}"):
            st.session_state["room_ops"].setdefault(room, {})["reset"] = True

        # Data panel (chart + thresholds + simple AI note)
        if st.session_state.get("selected_detector"):
            facility.render_room_data_panel(
                images_dir=IMAGES,
                room=room,
                selected_detector=st.session_state["selected_detector"],
                simulate=st.session_state["simulate_by_room"].get(room, False),
                ops=st.session_state["room_ops"].get(room, {}),
                brand={"navy": OBW_NAVY, "red": OBW_RED},
            )
            # consume ops so buttons feel one-shot
            st.session_state["room_ops"][room] = {}

# ======================================================
# Live Data (dropdowns, always shows a chart)
# ======================================================
with tab_live:
    st.markdown('<div class="obw-bar">📡 Live Data</div>', unsafe_allow_html=True)

    rooms = list(facility.DETECTORS.keys())
    live_room = st.selectbox("Room", rooms,
        index=rooms.index(st.session_state["current_room"]) if st.session_state["current_room"] in rooms else 0)
    dets = facility.get_detectors_for(live_room)
    labels = [d["label"] for d in dets]
    live_det = st.selectbox("Detector", labels,
        index=labels.index(st.session_state["selected_detector"]) if st.session_state.get("selected_detector") in labels else 0) if labels else None

    # Controls
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
            ops=st.session_state["room_ops"].get(live_room, {}),
            brand={"navy": OBW_NAVY, "red": OBW_RED}
        )
        st.session_state["room_ops"][live_room] = {}

# ======================================================
# Settings
# ======================================================
with tab_settings:
    st.markdown('<div class="obw-bar">⚙ Settings</div>', unsafe_allow_html=True)
    st.write("This baseline uses synthetic data seeded for 6 months with one spike per week per detector.")
    st.write("Images expected in `/images` (Overview.png / Room X.png names you already use).")








