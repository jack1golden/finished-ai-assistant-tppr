from pathlib import Path
import streamlit as st
import json
from PIL import Image, ImageDraw
from streamlit_drawable_canvas import st_canvas


def render_overview(images_dir: Path):
    """Render facility overview with clickable rooms"""
    st.header("🏭 Facility Overview")
    overview_path = images_dir / "Overview.png"

    if overview_path.exists():
        st.image(str(overview_path), caption="Facility Overview", use_container_width=True)
    else:
        st.error("Overview.png not found in images folder!")

    rooms = [p.stem for p in images_dir.glob("Room*.png")]
    for room in rooms:
        if st.button(f"Enter {room}", key=f"enter_{room}"):
            st.session_state["current_room"] = room
            st.experimental_rerun()


def render_room(images_dir: Path, room: str, mapping_mode=False):
    """Render individual room with detectors and mapping option"""
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
            background_image=image,   # ✅ PIL image
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
        # Load original room image
        image = Image.open(img_path).convert("RGBA")
        overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        # Draw detectors if any
        for i, det in enumerate(detectors):
            x = int(det["x"] / 100 * image.width)
            y = int(det["y"] / 100 * image.height)
            r = 10
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(255, 0, 0, 180))
            draw.text((x+12, y-12), f"D{i+1}", fill=(255, 0, 0, 255))

        combined = Image.alpha_composite(image, overlay)

        st.image(combined, caption=f"{room} View with Detectors", use_container_width=True)

        if not detectors:
            st.info("No detectors mapped in this room yet.")
        else:
            st.write("🔎 Detectors:")
            for i, det in enumerate(detectors):
                if st.button(f"Detector {i+1} ({det['x']:.1f}%, {det['y']:.1f}%)", key=f"{room}_det_{i}"):
                    st.success(f"📊 Showing data for Detector {i+1} in {room}")



