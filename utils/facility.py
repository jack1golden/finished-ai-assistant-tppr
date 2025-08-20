from pathlib import Path
import streamlit as st

# Candidate filenames for the overview
OVERVIEW_CANDIDATES = [
    "Overview.png", "overview.png", "Overview (1).png"
]

# Map rooms to their image filenames
ROOM_IMAGES = {
    "Room 1": "Room 1.png",
    "Room 2": "Room 2 (1).png",
    "Room 3": "Room 3 (1).png",
    "Room 4": "Room 5.png",          # adjust if your naming differs
    "Room 5": "Room 6.png",          # adjust if your naming differs
    "Room 6": "Room 8.png",          # adjust if your naming differs
}

def _first_existing(images_dir: Path, candidates):
    """Helper to find the first existing file in candidates."""
    for c in candidates:
        candidate = images_dir / c
        if candidate.exists():
            return candidate
    return None


def render_overview(images_dir: Path):
    st.header("🏭 Facility Overview")

    ov = _first_existing(images_dir, OVERVIEW_CANDIDATES)
    if not ov:
        st.error("❌ Overview image not found in images/. Please add 'Overview.png'")
        return

    # Show blueprint image
    st.image(str(ov), caption="Facility Overview", use_container_width=True)

    # Room selector buttons in grid
    st.markdown("### Select a Room")

    cols = st.columns(3)
    rooms = list(ROOM_IMAGES.keys())

    for idx, room in enumerate(rooms):
        with cols[idx % 3]:
            if st.button(room, key=f"overview_{room}"):
                st.session_state["current_room"] = room


def render_room(images_dir: Path, room: str):
    """Render an individual room view with detectors."""
    st.subheader(f"🚪 {room}")

    if room not in ROOM_IMAGES:
        st.warning("⚠️ No image mapped for this room.")
        return

    img_path = images_dir / ROOM_IMAGES[room]
    if not img_path.exists():
        st.error(f"❌ Image file missing: {img_path.name}")
        return

    # Show room image
    st.image(str(img_path), caption=room, use_container_width=True)

    # Detector + simulation controls
    st.markdown("### Controls")
    if st.button(f"📡 Detector in {room}"):
        st.session_state["show_graph"] = True
        st.session_state["graph_room"] = room

    if st.button("💨 Simulate Gas Leak"):
        st.session_state["simulate_leak"] = True
        st.session_state["leak_room"] = room

    if st.button("⬅️ Back to Overview"):
        st.session_state["current_room"] = None
