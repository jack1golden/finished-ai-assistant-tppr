import streamlit as st
from pathlib import Path
import json
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# ---------------------------
# Render Facility Overview
# ---------------------------
def render_overview(images_dir: Path):
    img_path = images_dir / "Overview.png"
    if not img_path.exists():
        st.error("❌ Overview.png not found in images/")
        return

    st.image(str(img_path), caption="Facility Overview", use_container_width=True)

    # Room navigation buttons (can be expanded)
    rooms = ["Room 1", "Room 2", "Room 3", "Room 12 17", "Room Production", "Room Production 2"]
    for rn in rooms:
        if st.button(f"Enter {rn}", key=f"enter_{rn}"):
            st.session_state.current_room = rn

# ---------------------------
# Render Individual Room
# ---------------------------
def render_room(images_dir: Path, room: str, mapping_mode=False):
    img_path = images_dir / f"{room}.png"
    if not img_path.exists():
        st.warning(f"No image found for {room}")
        return

    # Detector mapping file
    map_file = images_dir / "detector_map.json"
    mapping = {}
    if map_file.exists():
        with open(map_file, "r") as f:
            mapping = json.load(f)

    detectors = mapping.get(room, [])

    # ---------------------------
    # Mapping Mode
    # ---------------------------
    if mapping_mode:
        st.subheader("🛠 Detector Mapping Mode")
        st.info("Click anywhere on the image to add detector positions")

        image = Image.open(img_path)

        canvas = st_canvas(
            fill_color="rgba(255, 0, 0, 0.3)",
            stroke_width=0,
            background_image=str(img_path),  # ✅ FIXED: must be path, not PIL.Image
            update_streamlit=True,
            height=image.height,
            width=image.width,
            drawing_mode="point",
            key=f"canvas_{room}"
        )

        if canvas.json_data is not None and len(canvas.json_data["objects"]) > 0:
            # Take last clicked object
            obj = canvas.json_data["objects"][-1]
            x = (obj["left"] / image.width) * 100
            y = (obj["top"] / image.height) * 100
            st.write(f"📍 Clicked at: {x:.1f}%, {y:.1f}%")
            if st.button("Add Detector Here", key=f"add_det_{room}_{len(detectors)}"):
                detectors.append({"x": x, "y": y})
                mapping[room] = detectors
                with open(map_file, "w") as f:
                    json.dump(mapping, f, indent=2)
                st.success("✅ Detector saved! Refresh mapping to see it.")

    # ---------------------------
    # Normal Mode
    # ---------------------------
    else:
        st.image(str(img_path), caption=f"{room} View", use_container_width=True)

        if not detectors:
            st.info("No detectors mapped in this room yet.")
        else:
            st.write("🔎 Detectors:")
            for i, det in enumerate(detectors):
                if st.button(f"Detector {i+1} ({det['x']:.1f}%, {det['y']:.1f}%)", key=f"{room}_det_{i}"):
                    st.success(f"📊 Showing data for Detector {i+1} in {room}")


