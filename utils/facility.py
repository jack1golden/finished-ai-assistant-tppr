import streamlit as st
from pathlib import Path
import base64

# --- helper to convert image to base64 for inline display ---
def get_base64_image(path: Path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


# --- facility overview (main blueprint) ---
def render_overview(images_dir: Path):
    st.image(
        str(images_dir / "Overview.png"),
        caption="Facility Overview",
        use_container_width=True,
    )


# --- single room renderer with detector overlays ---
def render_room(images_dir: Path, room: str):
    img_path = images_dir / f"{room}.png"

    if not img_path.exists():
        st.warning(f"No image found for {room} at {img_path}")
        return

    img_base64 = get_base64_image(img_path)

    # CSS/HTML overlay with detectors positioned manually
    # Adjust percentages (top/left) per room later to match your detectors
    html = f"""
    <div style="position: relative; display: inline-block; width: 100%; border: 2px solid #0af; border-radius: 10px;">
        <img src="data:image/png;base64,{img_base64}" style="width: 100%; height: auto; display: block;"/>

        <!-- Example Detector 1 -->
        <button onclick="window.parent.postMessage({{isStreamlitMessage: true, type: 'streamlit:setComponentValue', key: '{room}_det1', value: true}}, '*');"
                style="position: absolute; top: 30%; left: 35%;
                       background-color: rgba(255,0,0,0.8); color: white;
                       font-weight: bold; border: none; border-radius: 6px;
                       padding: 4px 10px; cursor: pointer;">
            Detector 1
        </button>

        <!-- Example Detector 2 -->
        <button onclick="window.parent.postMessage({{isStreamlitMessage: true, type: 'streamlit:setComponentValue', key: '{room}_det2', value: true}}, '*');"
                style="position: absolute; top: 60%; left: 65%;
                       background-color: rgba(0,0,255,0.8); color: white;
                       font-weight: bold; border: none; border-radius: 6px;
                       padding: 4px 10px; cursor: pointer;">
            Detector 2
        </button>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)

    # Show info if detector clicked
    for det in ["det1", "det2"]:
        key = f"{room}_{det}"
        if key in st.session_state and st.session_state[key]:
            st.success(f"✅ {room} → {det.upper()} selected")
            st.session_state[key] = False  # reset after showing
