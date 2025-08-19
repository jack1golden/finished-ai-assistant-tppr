from pathlib import Path
import json

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from streamlit_drawable_canvas import st_canvas


# ---------------------------
# Facility Overview
# ---------------------------
def render_overview(images_dir: Path):
    st.header("🏭 Facility Overview")
    overview_path = images_dir / "Overview.png"

    if overview_path.exists():
        st.image(str(overview_path), caption="Facility Overview", use_container_width=True)
    else:
        st.error("❌ Overview.png not found in images/")

    # Auto-list rooms by filename like 'Room *.png'
    rooms = sorted([p.stem for p in images_dir.glob("Room*.png")])
    if not rooms:
        st.caption("No room images found (files like 'Room 1.png', 'Room 2.png', ...).")
        return

    st.markdown("### Rooms")
    for room in rooms:
        if st.button(f"Enter {room}", key=f"enter_{room}"):
            st.session_state["current_room"] = room
            st.experimental_rerun()


# ---------------------------
# Room View (mapping + normal)
# ---------------------------
def render_room(images_dir: Path, room: str, mapping_mode: bool = False):
    """
    In mapping_mode: click on image to set detector points; save to images/detector_map.json
    In normal mode: draw detectors as red dots with labels on the image and show buttons below.
    """
    img_path = images_dir / f"{room}.png"
    if not img_path.exists():
        st.warning(f"No image found for {room} at {img_path}")
        return

    # Detector mapping file (persist positions here)
    map_file = images_dir / "detector_map.json"
    mapping = {}
    if map_file.exists():
        try:
            mapping = json.loads(map_file.read_text())
        except Exception:
            mapping = {}

    detectors = mapping.get(room, [])  # list of dicts {x:%, y:% , label?:str}

    if mapping_mode:
        st.subheader("🛠 Detector Mapping Mode")
        st.info("Click anywhere on the image to add detector positions, then press **Add Detector Here**. Click **Save Mapping** when done.")

        # Load image and convert to RGB numpy array for st_canvas
        pil_img = Image.open(img_path).convert("RGB")
        bg_np = np.array(pil_img)

        canvas = st_canvas(
            fill_color="rgba(255, 0, 0, 0.3)",
            stroke_width=0,
            background_image=bg_np,        # ✅ NumPy array (RGB)
            update_streamlit=True,
            height=bg_np.shape[0],
            width=bg_np.shape[1],
            drawing_mode="point",
            key=f"canvas_{room}"
        )

        # Read last clicked point from the canvas JSON
        last_pt = None
        if canvas.json_data is not None and canvas.json_data.get("objects"):
            obj = canvas.json_data["objects"][-1]
            # Canvas returns absolute pixels; convert to percentages
            x_pct = (obj["left"] / bg_np.shape[1]) * 100.0
            y_pct = (obj["top"]  / bg_np.shape[0]) * 100.0
            last_pt = {"x": x_pct, "y": y_pct}
            st.write(f"📍 Clicked at: x={x_pct:.2f}%, y={y_pct:.2f}%")

        # Controls to add/save
        default_label = f"D{len(detectors)+1}"
        new_label = st.text_input("Detector label", value=default_label, key=f"label_{room}")

        colA, colB, _ = st.columns([1,1,4])
        with colA:
            if st.button("Add Detector Here", key=f"add_{room}_{len(detectors)}"):
                if last_pt is None:
                    st.warning("Click on the image first to pick a position.")
                else:
                    detectors.append({"x": float(last_pt["x"]), "y": float(last_pt["y"]), "label": new_label})
                    mapping[room] = detectors
                    map_file.write_text(json.dumps(mapping, indent=2))
                    st.success("✅ Detector added & mapping saved.")
                    st.experimental_rerun()
        with colB:
            if st.button("Save Mapping", key=f"save_{room}"):
                mapping[room] = detectors
                map_file.write_text(json.dumps(mapping, indent=2))
                st.success("💾 Mapping saved to images/detector_map.json")

        # Show current list
        if detectors:
            st.markdown("**Current detectors in this room:**")
            for i, d in enumerate(detectors, start=1):
                st.write(f"{i}. {d.get('label', f'D{i}')}: x={d['x']:.2f}%, y={d['y']:.2f}%")
        else:
            st.caption("No detectors mapped yet.")

    else:
        # Normal mode: show image + overlay dots + labels
        pil_img = Image.open(img_path).convert("RGBA")
        overlay = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Optional: font for labels (fallback to default if not available)
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except Exception:
            font = None

        for i, d in enumerate(detectors, start=1):
            x = int(d["x"] / 100.0 * pil_img.width)
            y = int(d["y"] / 100.0 * pil_img.height)
            r = 10
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(255, 72, 72, 220))
            label = d.get("label", f"D{i}")
            # Draw label with a tiny shadow for readability
            if font:
                draw.text((x+12, y-14), label, fill=(255, 72, 72, 255), font=font)
            else:
                draw.text((x+12, y-14), label, fill=(255, 72, 72, 255))

        combined = Image.alpha_composite(pil_img, overlay)
        st.image(combined, caption=f"{room} View", use_container_width=True)

        # Buttons under image for selecting detectors (hook these to charts later)
        if detectors:
            st.markdown("### Detectors")
            for i, d in enumerate(detectors, start=1):
                label = d.get("label", f"D{i}")
                if st.button(f"Open {label}", key=f"{room}_det_{i}"):
                    st.success(f"📊 Showing data for {label} in {room}")
        else:
            st.info("No detectors mapped in this room yet. Enable Mapping Mode to add some.")



