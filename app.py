import streamlit as st
import utils.facility as facility

# ---------------------------
# Page Setup
# ---------------------------
st.set_page_config(page_title="AI Safety Assistant", layout="wide")

# Session State
if "current_room" not in st.session_state:
    st.session_state["current_room"] = None
if "selected_detector" not in st.session_state:
    st.session_state["selected_detector"] = None

# ---------------------------
# Main
# ---------------------------
st.title("🏭 AI Safety Assistant")

if st.session_state["current_room"] is None:
    facility.render_overview()
else:
    facility.render_room(
        st.session_state["current_room"],
        st.session_state["selected_detector"]
    )

