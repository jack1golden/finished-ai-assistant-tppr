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

st.set_page_config(page_title="Pharma Safety HMI — AI First", layout="wide")

# ---------- session defaults ----------
def _d(k, v):
    if k not in st.session_state:
        st.session_state[k] = v

_d("current_room", None)
_d("selected_detector", None)
_d("simulate_by_room", {})   # {room: bool}
_d("force_rule_ai", False)   # force rule-based even if key exists

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

# ---------- sidebar ----------
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
        prev_room = st.session_state.get("current_room")
        st.session_state["current_room"] = sel
        if prev_room != sel:
            st.session_state["selected_detector"] = None
        _sanitize_selected_detector()

    # detector chooser (safe)
    room = st.session_state.get("current_room")
    if room and room != "Overview":
        det_list = facility.get_detectors_for(room) or []
        labels = [d["label"] for d in det_list]
        current = st.session_state.get("selected_detector")
        if labels:
            if current not in labels:
                current = labels[0]
                st.session_state["selected_detector"] = current
            chosen = st.radio(
                "Detector",
                labels,
                index=labels.index(current),
                key=f"rad_{room}",
            )
            if chosen != st.session_state.get("selected_detector"):
                st.session_state["selected_detector"] = chosen
            st.query_params.update({"room": room, "det": st.session_state["selected_detector"]})
        else:
            st.caption("No detectors defined for this room.")
            st.query_params.update({"room": room})

        st.write("---")
        c1, c2 = st.columns(2)
        if c1.button("💨 Simulate", use_container_width=True, key=f"sim_{room}"):
            st.session_state["simulate_by_room"][room] = True
        if c2.button("⏹ Reset", use_container_width=True, key=f"reset_{room}"):
            st.session_state["simulate_by_room"][room] = False

    st.write("---")
    st.markdown("### AI Mode")
    available = safety_ai.is_available()
    st.caption(f"Backend detected: **{'OpenAI (available)' if available else 'Rule-based only'}**")
    st.session_state["force_rule_ai"] = st.toggle(
        "Force rule‑based (no API calls)",
        value=st.session_state.get("force_rule_ai", False),
        help="Leave off to use OpenAI when available."
    )

    # 🔎 Self-test
    if st.button("Run AI self-test"):
        ctx = {"room": "Room 1", "gas": "NH₃", "value": 30.0, "status": "WARN",
               "thresholds": {"mode":"high","warn":25,"alarm":35,"units":"ppm"},
               "simulate": False, "recent_series":[28,29,30]}
        answer = safety_ai.ask_ai("Write a haiku about an H₂S alarm.", ctx,
                                  force_rule=st.session_state["force_rule_ai"])
        st.write("**Backend:**", safety_ai.backend_name(st.session_state["force_rule_ai"]))
        st.write(answer)

# ---------- header ----------
cols = st.columns([5, 1])
with cols[0]:
    st.title("Pharma Safety HMI — AI First")
with cols[1]:
    logo = IMAGES / "logo.png"
    if logo.exists():
        st.image(str(logo), caption="", use_container_width=True)

# ---------- main ----------
room = st.session_state["current_room"]

if not room:
    st.subheader("🏭 Facility Overview (2.5D)")
    # Traffic-light strip + image + hotspots
    facility.render_overview(IMAGES)
    st.markdown("#### Quick open")
    bcols = st.columns(6)
    for i, rn in enumerate(["Room 1", "Room 2", "Room 3", "Room Production", "Room Production 2", "Room 12 17"]):
        if bcols[i].button(rn, key=f"open_{rn}"):
            st.session_state["current_room"] = rn
            st.session_state["selected_detector"] = None
            _sanitize_selected_detector()
            st.query_params.update(
                {"room": rn, **({"det": st.session_state["selected_detector"]} if st.session_state["selected_detector"] else {})}
            )
            st.rerun()
else:
    st.subheader(f"🚪 {room}")
    simulate_flag = st.session_state["simulate_by_room"].get(room, False)

    facility.render_room(
        images_dir=IMAGES,
        room=room,
        simulate=simulate_flag,
        selected_detector=st.session_state.get("selected_detector"),
        ai_force_rule=st.session_state["force_rule_ai"],
    )

    st.write("---")
    if st.button("⬅️ Back to Overview"):
        st.session_state["current_room"] = None
        st.session_state["selected_detector"] = None
        st.query_params.clear()
        st.rerun()


