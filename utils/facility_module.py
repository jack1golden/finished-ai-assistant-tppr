iimport streamlit as st
import streamlit.components.v1 as components
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np
import json
from pathlib import Path

# 🔧 Define detector positions (hardcoded for now)
DETECTORS = {
    "Room 1": [{"label": "NH3", "x": 35, "y": 35, "reading": "0.3 ppm"}],
    "Room 2": [{"label": "O₂", "x": 85, "y": 20, "reading": "21 %"}],
    "Room 3": [{"label": "CO", "x": 50, "y": 60, "reading": "5 ppm"}],
    "Room 4": [{"label": "CH4", "x": 60, "y": 40, "reading": "2 ppm"}],
    "Room 5": [{"label": "Cl₂", "x": 25, "y": 55, "reading": "1 ppm"}],
    "Room 6": [{"label": "H₂S", "x": 70, "y": 30, "reading": "0.1 ppm"}],
}

# 🔧 Hardcoded room hotspots for Overview
ROOMS = {
    "Room 1": {"x": 15, "y": 30, "w": 12, "h": 18},
    "Room 2": {"x": 45, "y": 35, "w": 12, "h": 18},
    "Room 3": {"x": 70, "y": 40, "w": 12, "h": 18},
    "Room 4": {"x": 25, "y": 70, "w": 12, "h": 18},
    "Room 5": {"x": 65, "y": 70, "w": 12, "h": 18},
    "Room 6": {"x": 40, "y": 55, "w": 12, "h": 18},
}


def render_overview(images_dir: Path, calibrate=False, cal_room=None):
    """Render the facility overview map with clickable rooms."""
    img_path = images_dir / "Overview.png"
    img = Image.open(img_path)

    st.subheader("🏭 Facility Overview")

    if calibrate:
        st.info("Calibration Mode: Drag boxes to reposition rooms.")
        img_array = np.array(img)  # ✅ Convert PIL → np.ndarray

        canvas = st_canvas(
            background_image=img_array,
            update_streamlit=True,
            width=img.width,
            height=img.height,
            drawing_mode="rect",
            key="ov_canvas",
        )

        if canvas.json_data is not None:
            st.json(canvas.json_data)  # debug: see calibration json
    else:
        html = f"""
        <div style="position: relative; display: inline-block;">
          <img src="data:image/png;base64,{image_to_base64(img)}"
               style="max-width: 100%; height: auto;"/>
        """

        for room, pos in ROOMS.items():
            html += f"""
            <a class="hotspot" href="?room={room}" target="_top"
               style="position: absolute; 
                      left:{pos['x']}%; top:{pos['y']}%;
                      width:{pos['w']}%; height:{pos['h']}%;
                      border:2px solid green; border-radius:6px;
                      background:rgba(0,255,0,0.2);
                      text-align:center; color:black; font-weight:bold;">
              {room}
            </a>
            """

        html += "</div>"

        components.html(html, height=img.height + 50, scrolling=False)


def render_room(images_dir: Path, room: str, calibrate=False):
    """Render individual room view with detectors."""
    img_path = images_dir / f"{room}.png"
    img = Image.open(img_path)

    st.subheader(f"🚪 {room}")

    if calibrate:
        st.info(f"Calibration Mode: Place detectors for {room}")
        img_array = np.array(img)  # ✅ Convert PIL → np.ndarray

        canvas = st_canvas(
            background_image=img_array,
            update_streamlit=True,
            width=img.width,
            height=img.height,
            drawing_mode="circle",
            key=f"canvas_{room}",
        )

        if canvas.json_data is not None:
            st.json(canvas.json_data)  # debug: see calibration json
    else:
        html = f"""
        <div style="position: relative; display: inline-block;">
          <img src="data:image/png;base64,{image_to_base64(img)}"
               style="max-width: 100%; height: auto;"/>
        """

        if room in DETECTORS:
            for det in DETECTORS[room]:
                html += f"""
                <button style="position: absolute;
                               left:{det['x']}%; top:{det['y']}%;
                               transform: translate(-50%, -50%);
                               padding:6px 12px;
                               border:2px solid green;
                               border-radius:6px;
                               background:rgba(255,255,255,0.9);
                               font-weight:bold;
                               cursor:pointer;">
                  {det['label']} ({det['reading']})
                </button>
                """

        html += "</div>"

        components.html(html, height=img.height + 50, scrolling=False)


# Helper: convert PIL → base64 for embedding in HTML
import base64
from io import BytesIO

def image_to_base64(img: Image.Image) -> str:
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


        



