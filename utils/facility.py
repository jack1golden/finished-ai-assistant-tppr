import streamlit as st
import streamlit.components.v1 as components
import random
import time
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# ---------------------------
# Paths
# ---------------------------
IMAGES = Path("images")

# ---------------------------
# Hardcoded Detector Map
# ---------------------------
DETECTORS = {
    "Room 1": [
        {"label": "NH₃", "x": 35, "y": 35, "range": "0–50 ppm"},
    ],
    "Room 2": [
        {"label": "NH₃", "x": 80, "y": 20, "range": "0–50 ppm"},
    ],
    "Room 3": [
        {"label": "O₂", "x": 28, "y": 72, "range": "19–23%"},
    ],
    "Room 4": [
        {"label": "CO₂", "x": 60, "y": 50, "range": "0–5000 ppm"},
    ],
    "Room 5": [
        {"label": "CH₄", "x": 40, "y": 65, "range": "0–1000 ppm"},
    ],
    "Room 6": [
        {"label": "Cl₂", "x": 55, "y": 40, "range": "0–1 ppm"},
    ],
}

# ---------------------------
# Facility Overview
# ---------------------------
def render_overview():
    st.header("🏭 Facility Overview")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.image(str(IMAGES / "Overview.png"), use_container_width=True)

        # Overlay clickable buttons
        cols = st.columns(3)
        if cols[0].button("➡️ Room 1"):
            st.session_state["current_room"] = "Room 1"
        if cols[1].button("➡️ Room 2"):
            st.session_state["current_room"] = "Room 2"
        if cols[2].button("➡️ Room 3"):
            st.session_state["current_room"] = "Room 3"

        cols2 = st.columns(3)
        if cols2[0].button("➡️ Room 4"):
            st.session_state["current_room"] = "Room 4"
        if cols2[1].button("➡️ Room 5"):
            st.session_state["current_room"] = "Room 5"
        if cols2[2].button("➡️ Room 6"):
            st.session_state["current_room"] = "Room 6"

    with col_right:
        st.subheader("🤖 AI Safety Assistant")
        st.info("Ask me about facility safety, detector readings, or emergency procedures!")

        user_input = st.text_input("You:", key="overview_chat")
        if user_input:
            st.success(f"AI: This is a placeholder response to '{user_input}'")

# ---------------------------
# Room View
# ---------------------------
def render_room(room, selected_detector):
    st.subheader(f"🚪 {room}")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.image(str(IMAGES / f"{room}.png"), use_container_width=True)

        # Render detectors as buttons
        for det in DETECTORS.get(room, []):
            label = f"{det['label']} ({det['range']})"
            if st.button(label, key=f"{room}_{det['label']}"):
                st.session_state["selected_detector"] = det

    with col_right:
        if selected_detector:
            show_detector_graph(selected_detector)
        else:
            st.subheader("🤖 AI Safety Assistant")
            user_input = st.text_input("You:", key=f"chat_{room}")
            if user_input:
                st.success(f"AI: This is a placeholder response to '{user_input}'")

    if st.button("⬅️ Back to Overview", key=f"back_{room}"):
        st.session_state["current_room"] = None
        st.session_state["selected_detector"] = None

# ---------------------------
# Detector Graph
# ---------------------------
def show_detector_graph(det):
    st.subheader(f"📈 {det['label']} Readings")

    x = np.arange(0, 50)
    y = np.cumsum(np.random.randn(50)) + 50  # random curve

    fig, ax = plt.subplots()
    ax.plot(x, y, label="Live Reading")
    ax.set_title(f"{det['label']} ({det['range']})")
    ax.legend()
    st.pyplot(fig)



