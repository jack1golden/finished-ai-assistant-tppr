import streamlit as st
from pathlib import Path
import utils.facility as facility

# -----------------------------
# Setup
# -----------------------------
HERE = Path(__file__).parent
IMAGES = HERE / "images"

if "current_room" not in st.session_state:
    st.session_state["current_room"] = None
if "current_detector" not in st.session_state:
    st.session_state["current_detector"] = None

# -----------------------------
# URL query support
# -----------------------------
query_params = st.query_params
if "room" in query_params:
    st.session_state["current_room"] = query_params["room"]
if "det" in query_params:
    st.session_state["current_detector"] = query_params["det"]

# -----------------------------
# Render
# -----------------------------
if st.session_state["current_room"] is None:
    st.title("🏭 Facility Overview")
    facility.render_overview(IMAGES)
else:
    room = st.session_state["current_room"]
    st.title(f"🚪 {room}")
    facility.render_room(IMAGES, room)

    if st.session_state["current_detector"]:
        det = st.session_state["current_detector"]
        st.subheader(f"📊 Detector Selected: {det}")
        st.info("This is where live graph / AI advisory will appear.")

    if st.button("⬅️ Back to Overview"):
        st.session_state["current_room"] = None
        st.session_state["current_detector"] = None
        st.query_params.clear()

