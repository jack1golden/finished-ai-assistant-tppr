import streamlit as st
from pathlib import Path
import utils.facility as facility

st.set_page_config(layout="wide", page_title="Pharma Safety HMI — Demo")

# Paths
HERE = Path(__file__).parent
IMAGES = HERE / "images"

# Session
st.session_state.setdefault("current_room", None)

# View
if st.session_state["current_room"] is None:
    facility.render_overview(IMAGES)
else:
    st.title(f"🚪 {st.session_state['current_room']}")
    facility.render_room(IMAGES, st.session_state["current_room"])
    if st.button("⬅️ Back to Overview"):
        st.session_state["current_room"] = None
        st.experimental_rerun()
