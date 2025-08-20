import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from utils import facility, chat  # chat is optional; stub responses

st.set_page_config(page_title="Pharma Safety HMI — Demo", layout="wide")

HERE = Path(__file__).parent
IMAGES = HERE / "images"

# Session defaults
st.session_state.setdefault("current_room", None)
st.session_state.setdefault("messages", [])
st.session_state.setdefault("gas_data", [])
st.session_state.setdefault("selected_detector", None)

# Layout: Nav | Main View | AI/Chart
col_nav, col_view, col_side = st.columns([1, 2, 1], gap="large")

# -------- NAV ----------
with col_nav:
    st.header("Navigation")
    if st.button("🏠 Back to Overview", key="nav_back"):
        st.session_state["current_room"] = None
        st.rerun()

    # Quick room list
    rooms = facility.rooms_available(IMAGES)
    for rn in rooms:
        if st.button(f"Enter {rn}", key=f"nav_{rn}"):
            st.session_state["current_room"] = rn
            st.rerun()

# -------- MAIN VIEW ----------
with col_view:
    if st.session_state["current_room"] is None:
        facility.render_overview(IMAGES)
    else:
        rn = st.session_state["current_room"]
        st.subheader(f"🚪 {rn}")
        facility.render_room(IMAGES, rn)

# -------- SIDE: AI + Live Gas ----------
with col_side:
    st.header("AI Safety")
    sel = st.session_state.get("selected_detector")
    if sel:
        st.caption(f"Focused on: **{sel}**")

    user_msg = st.text_input("Message AI:", key="ai_input")
    if st.button("Send", key="ai_send"):
        if user_msg:
            st.session_state["messages"].append(("You", user_msg))
            # fake AI reply (optional utils/chat.py)
            try:
                reply = chat.fake_ai_response(user_msg)
            except Exception:
                reply = "AI suggests monitoring ventilation and closing shutters if levels rise."
            st.session_state["messages"].append(("AI", reply))
            st.rerun()

    for who, msg in st.session_state["messages"][-8:]:
        st.write(f"**{who}:** {msg}")

    st.divider()
    st.header("Live Gas (demo)")
    # Append new value each rerun (random base + occasional spike)
    val = float(np.random.normal(20, 4))
    if np.random.rand() < 0.06:
        val += float(np.random.randint(25, 70))
    st.session_state["gas_data"].append(val)
    if len(st.session_state["gas_data"]) > 240:
        st.session_state["gas_data"] = st.session_state["gas_data"][-240:]

    fig, ax = plt.subplots()
    ax.plot(st.session_state["gas_data"], label="Gas level (ppm)")
    ax.set_xlabel("Time")
    ax.set_ylabel("ppm")
    ax.legend()
    st.pyplot(fig, use_container_width=True)
