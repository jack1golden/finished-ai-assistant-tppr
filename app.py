import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from utils import facility, chat  # chat.fake_ai_response used (mock AI)

st.set_page_config(page_title="Pharma Safety HMI — Demo", layout="wide")

HERE = Path(__file__).parent
IMAGES = HERE / "images"

# ---------- Session ----------
st.session_state.setdefault("current_room", None)
st.session_state.setdefault("messages", [])
st.session_state.setdefault("selected_detector", None)     # e.g., "Room 1 — NH₃"
st.session_state.setdefault("detector_data", {})           # key -> list[float]

# ---------- Sim defaults ----------
# Baselines per gas (for nicer-looking curves)
BASELINES = {
    "NH₃":  8.0,   # ppm
    "CO":   10.0,  # ppm
    "O₂":   20.8,  # %vol
    "Ethanol": 120.0, # ppm
    "H₂":   5.0,   # ppm
}
UNITS = {"NH₃":"ppm","CO":"ppm","O₂":"%vol","Ethanol":"ppm","H₂":"ppm"}
# Simple thresholds for demo (advice on right will use these)
THRESH = {
    "NH₃": {"mode":"high","warn":25.0,"alarm":35.0},
    "CO":  {"mode":"high","warn":35.0,"alarm":50.0},
    "O₂":  {"mode":"low", "warn":19.5,"alarm":18.0},
    "Ethanol":{"mode":"high","warn":300.0,"alarm":500.0},
    "H₂":  {"mode":"high","warn":10.0,"alarm":15.0},
}

def sim_next(gas: str, t: int) -> float:
    """Very light demo simulator per gas."""
    base = BASELINES.get(gas, 10.0)
    jitter = np.sin(t/12.0)*0.7 + np.random.randn()*0.3
    val = base + jitter
    # rare spikes
    if np.random.rand() < 0.03:
        if gas == "O₂":
            val -= np.random.uniform(1.0, 3.0)   # O2 dips
        else:
            val += np.random.uniform(10.0, 40.0) # others spike upward
    return float(val)

def worst_status(gas: str, value: float) -> str:
    thr = THRESH.get(gas)
    if not thr: 
        return "HEALTHY"
    if thr["mode"] == "low":
        if value <= thr["alarm"]: return "ALARM"
        if value <= thr["warn"]:  return "WARN"
        return "HEALTHY"
    else:
        if value >= thr["alarm"]: return "ALARM"
        if value >= thr["warn"]:  return "WARN"
        return "HEALTHY"


# ---------- Layout: Nav | View | AI/Chart ----------
col_nav, col_view, col_side = st.columns([1, 2, 1], gap="large")

# NAV
with col_nav:
    st.header("Navigation")
    if st.button("🏠 Back to Overview", key="nav_back"):
        st.session_state["current_room"] = None
        st.session_state["selected_detector"] = None
        st.rerun()

    for rn in facility.rooms_available(IMAGES):
        if st.button(f"Enter {rn}", key=f"nav_{rn}"):
            st.session_state["current_room"] = rn
            st.rerun()

# MAIN VIEW
with col_view:
    if st.session_state["current_room"] is None:
        facility.render_overview(IMAGES)  # overview + enter buttons
    else:
        room = st.session_state["current_room"]
        st.subheader(f"🚪 {room}")
        # This renders the room image with clickable pins (HTML overlay) + fallback buttons.
        clicked = facility.render_room(IMAGES, room)  # returns label if a pin was clicked
        if clicked:
            st.session_state["selected_detector"] = f"{room} — {clicked}"
            st.success(f"Selected: {st.session_state['selected_detector']}")

# SIDE: AI + live per-detector chart
with col_side:
    # Determine target (selected detector) & gas
    sel = st.session_state.get("selected_detector")
    st.header("AI Safety")
    if sel:
        st.caption(f"Focused on: **{sel}**")
        # parse "Room X — GAS"
        try:
            _, gas = [s.strip() for s in sel.split("—", 1)]
        except Exception:
            gas = "NH₃"
    else:
        st.caption("No detector selected — showing demo chart.")
        gas = "NH₃"

    # Detector-aware AI chat
    user_msg = st.text_input("Message AI:", key="ai_input")
    if st.button("Send", key="ai_send"):
        if user_msg:
            st.session_state["messages"].append(("You", user_msg))
            # Make a detector-aware fake reply
            try:
                advice = chat.fake_ai_response(user_msg)
            except Exception:
                advice = "AI suggests closing shutters if levels approach alarm."
            # Add a little context
            advice = f"[{gas}] {advice}"
            st.session_state["messages"].append(("AI", advice))
            st.rerun()
    for who, msg in st.session_state["messages"][-8:]:
        st.write(f"**{who}:** {msg}")

    st.divider()
    st.header("Live Reading")

    # Build a stable key for time series: room+gas or generic
    series_key = sel if sel else f"DEMO — {gas}"
    data = st.session_state["detector_data"].setdefault(series_key, [])
    t = len(data)
    data.append(sim_next(gas, t))
    # cap length
    if len(data) > 300:
        del data[: len(data)-300]

    # Status bubble
    current = data[-1]
    status = worst_status(gas, current)
    units = UNITS.get(gas, "")
    if status == "ALARM":
        st.error(f"{gas} {current:.2f} {units} — **ALARM**")
    elif status == "WARN":
        st.warning(f"{gas} {current:.2f} {units} — **WARN**")
    else:
        st.success(f"{gas} {current:.2f} {units} — Healthy")

    # Plot (per selected detector)
    fig, ax = plt.subplots()
    ax.plot(data, label=f"{gas} ({units})")
    ax.set_xlabel("Time")
    ax.set_ylabel(units or "value")
    ax.legend()
    st.pyplot(fig, use_container_width=True)
