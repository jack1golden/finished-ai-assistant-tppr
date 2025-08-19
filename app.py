import streamlit as st
from pathlib import Path
import utils.facility as facility

# ---------------------------
# Setup
# ---------------------------
HERE = Path(__file__).parent
IMAGES = HERE / "images"

st.set_page_config(layout="wide", page_title="Pharma Safety HMI Demo")

# ---------------------------
# Sidebar
# ---------------------------
st.sidebar.title("⚙️ Controls")
if "mapping_mode" not in st.session_state:
    st.session_state.mapping_mode = False

if "current_room" not in st.session_state:
    st.session_state.current_room = None

st.session_state.mapping_mode = st.sidebar.checkbox("Mapping Mode", value=st.session_state.mapping_mode)

# ---------------------------
# Main View
# ---------------------------
if st.session_state["current_room"] is None:
    st.title("🏭 Facility Overview (2.5D)")
    facility.render_overview(IMAGES)
else:
    st.title(f"🚪 {st.session_state['current_room']}")
    facility.render_room(IMAGES, st.session_state["current_room"], mapping_mode=st.session_state.mapping_mode)

    if st.button("⬅️ Back to Overview"):
        st.session_state["current_room"] = None

