import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

from pathlib import Path
from utils import sim, chat, facility

# Paths
HERE = Path(__file__).parent
IMAGES = HERE / "images"

# Session state init
if "current_room" not in st.session_state:
    st.session_state["current_room"] = None
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "gas_data" not in st.session_state:
    st.session_state["gas_data"] = []

st.set_page_config(layout="wide", page_title="Pharma Facility Demo")

# Layout
col1, col2, col3 = st.columns([1,2,1])

with col1:
    st.header("Navigation")
    if st.button("🏠 Back to Overview"):
        st.session_state["current_room"] = None
    if st.session_state["current_room"]:
        facility.render_room(IMAGES, st.session_state["current_room"])
    else:
        facility.render_overview(IMAGES)

with col2:
    st.header("Facility View")
    if st.session_state["current_room"]:
        facility.render_room(IMAGES, st.session_state["current_room"])
    else:
        facility.render_overview(IMAGES)

with col3:
    st.header("AI Chatbox")
    user_input = st.text_input("Message AI:")
    if st.button("Send"):
        if user_input:
            st.session_state["messages"].append(("You", user_input))
            reply = chat.fake_ai_response(user_input)
            st.session_state["messages"].append(("AI", reply))
    for sender, msg in st.session_state["messages"][-5:]:
        st.write(f"**{sender}:** {msg}")

    st.header("Gas Sensor")
    # Simulate random live gas data
    new_val = np.random.normal(20, 5)
    if np.random.rand() < 0.05:
        new_val += np.random.randint(30, 80)
    st.session_state["gas_data"].append(new_val)
    if len(st.session_state["gas_data"]) > 50:
        st.session_state["gas_data"].pop(0)

    fig, ax = plt.subplots()
    ax.plot(st.session_state["gas_data"], label="Gas Level (ppm)")
    ax.legend()
    st.pyplot(fig)
