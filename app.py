import streamlit as st
from utils import facility

st.set_page_config(page_title="AI Safety Assistant", layout="wide")

# Initialize session state
if "current_room" not in st.session_state:
    st.session_state["current_room"] = None
if "current_detector" not in st.session_state:
    st.session_state["current_detector"] = None

# Sidebar navigation
st.sidebar.title("🏭 Navigation")
if st.sidebar.button("🏠 Home"):
    st.session_state["current_room"] = None
    st.session_state["current_detector"] = None

st.sidebar.markdown("---")
st.sidebar.write("Quick Rooms:")
for i in range(1, 7):
    if st.sidebar.button(f"Room {i}"):
        st.session_state["current_room"] = f"Room {i}"
        st.session_state["current_detector"] = None

st.sidebar.markdown("---")
st.sidebar.write("⚙️ Settings (placeholder)")

# Main page logic
if st.session_state["current_room"] is None:
    facility.render_overview()
else:
    facility.render_room(st.session_state["current_room"], st.session_state["current_detector"])


