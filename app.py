import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from urllib.parse import unquote

from utils import facility, chat  # chat.fake_ai_response is mocked

st.set_page_config(page_title="Pharma Safety HMI — Demo", layout="wide")

HERE = Path(__file__).parent
IMAGES = HERE / "images"

# ---------------- Session defaults ----------------
st.session_state.setdefault("current_room", None)           # e.g. "Room 1"
st.session_state.setdefault("selected_detector", None)      # e.g. "Room 1 — NH₃"
st.session_state.setdefault("messages", [])
st.session_state.setdefault("detector_data", {})            # key -> list[float]

# ---------------- Parse query params ----------------
# We drive navigation reliably with query params (?room=Room%201&det=NH%E2%82%83)
qp = st.query_params
room_qp = qp.get("room", None)
det_qp = qp.get("det", None)

if room_qp:
    st.session_state["current_room"] = unquote(room_qp)
if det_qp and st.session_state["current_room"]:
    st.session_state["selected_detector"] = f"{st.session_state['current_room']} — {unquote(det_qp)}"

# ---------------- Sim baselines / thresholds ----------------
BASELINES = {"NH₃": 8.0, "CO": 10.0, "O₂": 20.8, "Ethanol": 120.0, "H₂": 5.0}
UNITS     = {"NH₃":"ppm","CO":"ppm","O₂":"%vol","Ethanol":"ppm","H₂":"ppm"}
THRESH = {
    "NH₃": {"mode":"high","warn":25.0,"alarm":35.0},
    "CO":  {"mode":"high","warn":35.0,"alarm":50.0},
    "O₂":  {"mode":"low", "warn":19.5,"alarm":18.0},
    "Ethanol":{"mode":"high","warn":300.0,"alarm":500.0},
    "H₂":  {"mode":"high","warn":10.0,"alarm":15.0},
}

def sim_next(gas: str, t: int) -> float:
    base = BASELINES.get(gas, 10.0)
    jitter = np.sin(t/12.0)*0.7 + np.random.randn()*0.3
    val = base + jitter
    if np.random.rand() < 0.03:
        if gas == "O₂":
            val -= np.random.uniform(1.0, 3.0)
        else:
            val += np.random.uniform(10.0, 40.0)
    return float(val)

def status_for(gas: str, val: float) -> str:
    thr = THRESH.get(gas)
    if not thr: return "HEALTHY"
    if thr["mode"] == "low":
        if val <= thr["alarm"]: return "ALARM"
        if val <= thr["warn"]:  return "WARN"
        return "HEALTHY"
    else:
        if val >= thr["alarm"]: return "ALARM"
        if val >= thr["warn"]:  return "WARN"
        return "HEALTHY"

# ---------------- Layout ----------------
col_nav, col_view, col_side = st.columns([1, 2, 1], gap="large")

# NAV
with col_nav:
    st.header("Navigation")
    if st.button("🏠 Back to Overview"):
        # clear query params to return to overview
        st.query_params.clear()
        st.session_state["current_room"] = None
        st.session_state["selected_detector"] = None
        st.rerun()

    # Quick buttons as a fallback
    for rn in facility.rooms_available(IMAGES):
        if st.button(f"Enter {rn}", key=f"nav_{rn}"):
            st.query_params["room"] = rn
            st.rerun()

# VIEW
with col_view:
    room = st.session_state["current_room"]
    if not room:
        facility.render_overview(IMAGES)  # draws hotspots over image using links
    else:
        st.subheader(f"🚪 {room}")
        # Draw room with detector pins (pins are links that set ?room=..&det=..)
        facility.render_room(IMAGES, room)

        # Detector control row
        det_label = None
        sel = st.session_state.get("selected_detector")
        if sel and "—" in sel:
            _, det_label = [s.strip() for s in sel.split("—", 1)]

        c1, c2 = st.columns([1,1])
        with c1:
            if det_label:
                if st.button("📈 Open detector chart"):
                    pass  # the side panel always shows live chart for selected detector
        with c2:
            if st.button("⚠️ Simulate gas leak"):
                # push a friendly AI message
                st.session_state["messages"].append(("AI", f"[{det_label or 'NH₃'}] Simulating leak… closing shutters soon if needed."))
                # run the animation inside the room view
                facility.simulate_gas_and_shutters(IMAGES, room, preferred_label=det_label)

# SIDE: AI + live chart
with col_side:
    st.header("AI Safety")
    sel = st.session_state.get("selected_detector")
    if sel:
        st.caption(f"Focused on: **{sel}**")
        try:
            _, gas = [s.strip() for s in sel.split("—", 1)]
        except Exception:
            gas = "NH₃"
    else:
        st.caption("No detector selected — showing demo signal.")
        gas = "NH₃"

    user_msg = st.text_input("Message AI:", key="ai_input")
    if st.button("Send", key="ai_send"):
        if user_msg:
            st.session_state["messages"].append(("You", user_msg))
            try:
                reply = chat.fake_ai_response(user_msg)
            except Exception:
                reply = "AI suggests closing shutters if levels approach alarm."
            st.session_state["messages"].append(("AI", f"[{gas}] {reply}"))
            st.rerun()
    for who, msg in st.session_state["messages"][-8:]:
        st.write(f"**{who}:** {msg}")

    st.divider()
    st.header("Live Reading")
    series_key = sel if sel else f"DEMO — {gas}"
    data = st.session_state["detector_data"].setdefault(series_key, [])
    t = len(data)
    data.append(sim_next(gas, t))
    if len(data) > 300:
        del data[:len(data)-300]

    current = data[-1]
    units = {"NH₃":"ppm","CO":"ppm","O₂":"%vol","Ethanol":"ppm","H₂":"ppm"}.get(gas, "")
    st_status = status_for(gas, current)
    if st_status == "ALARM":
        st.error(f"{gas} {current:.2f} {units} — **ALARM**")
    elif st_status == "WARN":
        st.warning(f"{gas} {current:.2f} {units} — **WARN**")
    else:
        st.success(f"{gas} {current:.2f} {units} — Healthy")

    fig, ax = plt.subplots()
    ax.plot(data, label=f"{gas} ({units})")
    ax.set_xlabel("Time")
    ax.set_ylabel(units or "value")
    ax.legend()
    st.pyplot(fig, use_container_width=True)

