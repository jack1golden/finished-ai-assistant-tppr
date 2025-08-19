import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

from utils import chat, facility

# Paths
HERE = Path(__file__).parent
IMAGES = HERE / "images"

st.set_page_config(layout="wide", page_title="Pharma Facility Demo")

# ---- Session init ----
st.session_state.setdefault("current_room", None)
st.session_state.setdefault("messages", [])
st.session_state.setdefault("gas_data", [])
st.session_state.setdefault("mapping_mode", False)  # <— toggle Mapping Mode

# ---- Sidebar: global toggles ----
with st.sidebar:
    st.markdown("### Tools")
    st.session_state.mapping_mode = st.toggle("Detector Mapping Mode", value=st.session_state.mapping_mode, help="Click on the room image to add detector buttons at exact positions. Save to JSON when done.")
    if st.session_state.mapping_mode:
        st.info("Mapping Mode is ON — click on the image to drop detector pins. Use the Save button under the image.")

# ---- Layout: Navigation | View | AI/Chart ----
col_nav, col_view, col_ai = st.columns([1, 2, 1], gap="large")

# 1) Navigation (no images here — avoids duplicate renders)
with col_nav:
    st.header("Navigation")
    if st.button("🏠 Back to Overview", key="nav_back"):
        st.session_state["current_room"] = None

    rooms = facility.rooms_available(IMAGES)
    st.markdown("**Rooms**")
    for rn in rooms:
        if st.button(f"Enter {rn}", key=f"nav_{rn}"):
            st.session_state["current_room"] = rn

# 2) Center: Overview or Room with overlay
with col_view:
    if st.session_state["current_room"]:
        facility.render_room(IMAGES, st.session_state["current_room"], mapping_mode=st.session_state.mapping_mode)
    else:
        facility.render_overview(IMAGES)

# 3) Right: AI chat + Live gas (always visible)
with col_ai:
    st.header("AI Safety")
    user_input = st.text_input("Message AI:", key="ai_input")
    if st.button("Send", key="ai_send"):
        if user_input:
            st.session_state["messages"].append(("You", user_input))
            reply = chat.fake_ai_response(user_input)
            st.session_state["messages"].append(("AI", reply))
            st.rerun()

    # Show last few
    for sender, msg in st.session_state["messages"][-8:]:
        st.write(f"**{sender}:** {msg}")

    st.divider()
    st.header("Live Gas")
    # Random live curve with occasional spikes
    val = float(np.random.normal(20, 4))
    if np.random.rand() < 0.06:
        val += float(np.random.randint(25, 70))
    st.session_state["gas_data"].append(val)
    if len(st.session_state["gas_data"]) > 180:
        st.session_state["gas_data"] = st.session_state["gas_data"][-180:]

    fig, ax = plt.subplots()
    ax.plot(st.session_state["gas_data"], label="Gas level (ppm)")
    ax.set_xlabel("Time (ticks)")
    ax.set_ylabel("ppm")
    ax.legend()
    st.pyplot(fig, use_container_width=True)

