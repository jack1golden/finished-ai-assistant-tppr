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
/* App base */
.block-container {{
  background:{WHITE} !important;
}}

/* --- NAV / TAB STRIP --- */
.stTabs [data-baseweb="tab-list"] {{
  background:{OBW_NAVY};
  padding: 6px 8px;
  border-radius: 10px;
}}
.stTabs [data-baseweb="tab"] {{
  color: #ffffff !important;     /* ✅ white text on navy */
  font-weight: 600;
}}
.stTabs [data-baseweb="tab"]:hover {{
  background: rgba(255,255,255,0.08);
}}
.stTabs [aria-selected="true"] {{
  border-bottom: 3px solid {OBW_RED} !important;
}}

/* Section headers that sit on navy bars (Room header chip etc) */
.obw-bar {{
  background:{OBW_NAVY};
  color:#ffffff;                 /* ✅ white */
  padding:8px 12px;
  border-radius:10px;
  display:inline-block;
  font-weight:700;
}}

/* Buttons */
.stButton > button {{
  background: {OBW_NAVY};
  color:#ffffff;                 /* ✅ white */
  border: 1px solid {OBW_NAVY};
  border-radius: 8px;
}}
.stButton > button:hover {{
  background: {OBW_RED};
  border-color: {OBW_RED};
}}

/* Chips on overview */
.chip {{
  display:inline-block; color:#0b1220; font-weight:800; padding:6px 10px;
  border-radius:999px; box-shadow:0 1px 6px rgba(0,0,0,.2);
}}

/* Overview hotspots (room buttons) */
.hotspot {{
  position:absolute; border:2px solid rgba(34,197,94,.95); border-radius:10px;
  background:rgba(16,185,129,.22); color:#0b1220; font-weight:800; font-size:12px;
  display:flex; align-items:flex-start; justify-content:flex-start; padding:4px 6px; z-index:20;
  text-decoration:none;
}}
.hotspot:hover {{ background:rgba(16,185,129,.32); }}
.hotspot span {{
  background:rgba(2,6,23,.06); border:1px solid rgba(10,35,66,.25); padding:2px 6px; border-radius:8px;
}}

/* Detector badges in room */
.detector {{
  position:absolute; transform:translate(-50%,-50%);
  border:2px solid #22c55e; border-radius:10px; background:#ffffff;
  padding:6px 10px; min-width:72px; text-align:center; z-index:30; /* ✅ on top */
  box-shadow:0 0 10px rgba(34,197,94,.35); font-weight:800; color:#0f172a; text-decoration:none;
}}
.detector:hover {{ background:#eaffea; }}
.detector .lbl {{ font-size:14px; line-height:1.1; }}

/* Small navy label bars */
.obw-smallbar {{
  background:{OBW_NAVY};
  color:#ffffff;                 /* ✅ white */
  padding:4px 8px; border-radius:8px; display:inline-block; font-weight:700;
}}
</style>
""", unsafe_allow_html=True)

# ---------- session defaults ----------
def _d(k, v):
    if k not in st.session_state:
        st.session_state[k] = v

_d("current_room", "Overview")
_d("selected_detector", None)
_d("simulate_by_room", {})   # {room: bool}
_d("force_rule_ai", False)   # force rule-based even if key exists
_d("room_ops", {})           # per-room operator actions: {'close_shutter':bool, 'ventilate':bool, 'reset':bool, 'ack':bool}

# ---------- query params → session sync ----------
qp = st.query_params
if "room" in qp and qp["room"]:
    st.session_state["current_room"] = unquote(qp["room"])
if "det" in qp and qp["det"]:
    st.session_state["selected_detector"] = unquote(qp["det"])

# ---------- sanitize detector vs room ----------
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
        st.query_params.update({"room": room})
        return
    if cur not in labels:
        st.session_state["selected_detector"] = labels[0]
        st.query_params.update({"room": room, "det": labels[0]})

_sanitize_selected_detector()

# ---------- header (logo) ----------
c1, c2 = st.columns([6, 1])
with c1:
    st.title("OBW — Pharma Safety HMI (AI‑First)")
with c2:
    logo_path = IMAGES / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
    else:
        # SVG fallback: black OBW + red curve + "Technologies" red
        st.markdown(f"""
        <div style="display:flex;align-items:center;justify-content:center; background:#fff;">
          <svg width="180" height="60" viewBox="0 0 300 100" xmlns="http://www.w3.org/2000/svg">
            <text x="8" y="55" font-size="48" font-family="Arial, Helvetica, sans-serif" fill="{OBW_BLACK}" font-weight="700">OBW</text>
            <path d="M5 20 C 80 0, 180 0, 260 20" stroke="{OBW_RED}" stroke-width="6" fill="none"/>
            <text x="8" y="90" font-size="22" font-family="Arial, Helvetica, sans-serif" fill="{OBW_RED}">Technologies</text>
          </svg>
        </div>
        """, unsafe_allow_html=True)

# ---------- tabs ----------
tab_overview, tab_room, tab_ai, tab_logs, tab_settings = st.tabs(
    ["Overview", "Room", "AI Assistant", "Logs & Reports", "Settings"]
)

# ---------- Overview tab ----------
with tab_overview:
    st.markdown(f'<div class="obw-bar">🏭 Facility Overview (2.5D) — OBW Theme</div>', unsafe_allow_html=True)
    facility.render_overview(IMAGES)  # ✅ clickable hotspots restored

    st.markdown("#### Quick open")
    bcols = st.columns(6)
    for i, rn in enumerate(["Room 1", "Room 2", "Room 3", "Room Production", "Room Production 2", "Room 12 17"]):
        if bcols[i].button(rn, key=f"open_{rn}"):
            st.session_state["current_room"] = rn
            st.session_state["selected_detector"] = None
            _sanitize_selected_detector()
            st.query_params.update({"room": rn, **({"det": st.session_state["selected_detector"]} if st.session_state["selected_detector"] else {})})
            st.rerun()

# ---------- Room tab ----------
with tab_room:
    # Room selector & detector selector row
    csel1, csel2 = st.columns([2, 2])
    rooms = ["Room 1", "Room 2", "Room 3", "Room Production", "Room Production 2", "Room 12 17"]
    with csel1:
        current = st.session_state["current_room"] if st.session_state["current_room"] in rooms else rooms[0]
        rsel = st.selectbox("Select room", rooms, index=rooms.index(current), key="room_sel")
        if rsel != st.session_state["current_room"]:
            st.session_state["current_room"] = rsel
            st.session_state["selected_detector"] = None
            _sanitize_selected_detector()
            st.query_params.update({"room": rsel, **({"det": st.session_state["selected_detector"]} if st.session_state["selected_detector"] else {})})
            st.rerun()
    with csel2:
        det_list = facility.get_detectors_for(st.session_state["current_room"]) if st.session_state["current_room"] in rooms else []
        labels = [d["label"] for d in det_list]
        if labels:
            curdet = st.session_state.get("selected_detector") or labels[0]
            dsel = st.selectbox("Detector", labels, index=labels.index(curdet) if curdet in labels else 0, key="det_sel")
            if dsel != st.session_state.get("selected_detector"):
                st.session_state["selected_detector"] = dsel
                st.query_params.update({"room": st.session_state["current_room"], "det": dsel})
                st.rerun()
        else:
            st.info("No detectors configured for this room.")

    # Operator console
    st.write("---")
    st.markdown('<div class="obw-smallbar">🎛 Operator Console</div>', unsafe_allow_html=True)
    oc1, oc2, oc3, oc4, oc5 = st.columns(5)
    room = st.session_state["current_room"]
    if room and room != "Overview":
        if oc1.button("💨 Simulate leak", key=f"sim_{room}"):
            st.session_state["simulate_by_room"][room] = True
        if oc2.button("🛑 Close shutters", key=f"shut_{room}"):
            st.session_state["room_ops"].setdefault(room, {})["close_shutter"] = True
        if oc3.button("🌬 Increase ventilation", key=f"vent_{room}"):
            st.session_state["room_ops"].setdefault(room, {})["ventilate"] = True
        if oc4.button("✅ Acknowledge alarm", key=f"ack_{room}"):
            st.session_state["room_ops"].setdefault(room, {})["ack"] = True
        if oc5.button("♻️ Reset detector", key=f"reset_{room}"):
            st.session_state["room_ops"].setdefault(room, {})["reset"] = True

    st.write("---")
    # Render room (image, badges, cloud/shutter, timeline, predictive chart, AI)
    if room and room != "Overview":
        simulate_flag = st.session_state["simulate_by_room"].get(room, False)
        facility.render_room(
            images_dir=IMAGES,
            room=room,
            simulate=simulate_flag,
            selected_detector=st.session_state.get("selected_detector"),
            ai_force_rule=st.session_state["force_rule_ai"],
            ops=st.session_state["room_ops"].get(room, {}),
            brand={"navy": OBW_NAVY, "red": OBW_RED}
        )
        # Reset one-shot ops
        st.session_state["room_ops"][room] = {}

# ---------- AI Assistant tab (global) ----------
with tab_ai:
    st.markdown('<div class="obw-bar">🤖 Global AI Assistant</div>', unsafe_allow_html=True)
    st.caption("Ask about the entire facility — trends, cross-room reasoning, best actions. Uses GPT if available; otherwise the rule-based brain.")
    if p := st.chat_input("Ask a facility-wide question…", key="chat_global"):
        st.chat_message("user").write(p)
        snapshot = facility.build_facility_snapshot()
        answer = safety_ai.ask_ai(
            p,
            context={"facility": snapshot, "room": "All", "gas": None, "value": None, "status": "Mixed"},
            force_rule=st.session_state["force_rule_ai"]
        )
        st.chat_message("ai").write(answer)

# ---------- Logs & Reports tab ----------
with tab_logs:
    st.markdown('<div class="obw-bar">📜 AI Event Log</div>', unsafe_allow_html=True)
    logs = st.session_state.get("ai_log", {})
    if not logs:
        st.info("No events yet. Trigger a spike or let AI auto-comment when status changes.")
    else:
        for rm, entries in logs.items():
            if not entries:
                continue
            st.markdown(f"#### {rm}")
            for e in reversed(entries[-12:]):
                st.markdown(f"- **{facility.ts_str(e['ts'])}** — {e['text']}")
            st.write("---")
    if st.button("⬇️ Export Incident Log (HTML)"):
        html = facility.export_incident_html(logs, brand={"navy": OBW_NAVY, "red": OBW_RED})
        st.download_button("Download HTML", data=html, file_name="OBW_Incident_Log.html", mime="text/html")

# ---------- Settings tab ----------
with tab_settings:
    st.markdown('<div class="obw-bar">⚙️ Settings</div>', unsafe_allow_html=True)
    st.markdown("**AI Mode**")
    available = safety_ai.is_available()
    st.caption(f"Backend detected: **{'OpenAI (available)' if available else 'Rule-based only'}**")
    st.session_state["force_rule_ai"] = st.toggle(
        "Force rule‑based (no API calls)",
        value=st.session_state.get("force_rule_ai", False),
        help="Leave off to use OpenAI when available."
    )
    if st.button("Run AI self-test"):
        ctx = {"room": "Room 1", "gas": "NH₃", "value": 30.0, "status": "WARN",
               "thresholds": {"mode":"high","warn":25,"alarm":35,"units":"ppm"},
               "simulate": False, "recent_series":[28,29,30]}
        answer = safety_ai.ask_ai("Write a haiku about an H₂S alarm.", ctx,
                                  force_rule=st.session_state["force_rule_ai"])
        st.write("**Backend:**", safety_ai.backend_name(st.session_state["force_rule_ai"]))
        st.write(answer)

    st.write("---")
    st.markdown(f"""
    <div style="border:1px solid {OBW_NAVY}; padding:8px; border-radius:10px;">
      <div style="background:{OBW_NAVY}; color:#fff; padding:6px 10px; border-radius:8px; display:inline-block;">Navy bar (white text)</div>
      <div style="margin-top:6px; height:4px; background:{OBW_RED}; width:120px;"></div>
    </div>
    """, unsafe_allow_html=True)



