import streamlit as st
from pathlib import Path

ROOMS = {
    "Entry": "Entry.png",
    "Room 1": "Room 1.png",
    "Room 2": "Room 2.png",
    "Room 3": "Room 3.png",
    "Room 12/17": "Room 12 17.png",
    "Production": "Room Production.png",
    "Production 2": "Room Production 2.png",
}

def render_overview(images_dir: Path):
    st.image(str(images_dir / "Overview.png"), caption="Facility Overview", use_column_width=True)
    for rn in ROOMS:
        if st.button(f"Enter {rn}"):
            st.session_state["current_room"] = rn

def render_room(images_dir: Path, room: str):
    img_file = ROOMS[room]
    st.image(str(images_dir / img_file), caption=room, use_column_width=True)
    st.write(f"**Detectors in {room}**")
    if st.button(f"Detector in {room}"):
        st.session_state["detector_clicked"] = room
