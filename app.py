import streamlit as st
from utils import facility

st.set_page_config(page_title="AI Safety Assistant", layout="wide")

# -----------------------
# Initialize session state
# -----------------------
if "current_room" not in st.session_state:
    st.session_state["current_room"] = None
if "current_detector" not in st.session_state:
    st.session_state["current_detector"] = None

# -----------------------
# Sidebar
# -----------------------
st.sidebar.image("images/logo.png", width=200)
st.sidebar.title("🏭 AI Safety Assistant")

if st.sidebar.button("🏠 Home"):
    st.session_state["current_room"] = None
    st.session_state["current_detector"] = None

st.sidebar.markdown("### Quick Navigation")
for i in range(1, 7):
    if st.sidebar.button(f"Room {i}"):
        st.session_state["current_room"] = f"Room {i}"
        st.session_state["current_detector"] = None

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI Assistant")
st.sidebar.write("This is a placeholder for AI safety insights.")
user_input = st.sidebar.text_input("Ask AI about safety:")
if user_input:
    st.sidebar.success(f"AI Response: '{user_input}' is under control ✅")  # fake response

# -----------------------
# Main Area
# -----------------------
if st.session_state["current_room"] is None:
    facility.render_overview()
else:
    facility.render_room(
        room=st.session_state["current_room"],
        detector=st.session_state["current_detector"]
    )

