import base64
from pathlib import Path
import streamlit as st
from urllib.parse import quote

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def load_image_b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# -------------------------------------------------------------------
# Hardcoded mapping (adjust % values here)
# -------------------------------------------------------------------
OVERVIEW_HOTSPOTS = [
    {"room": "Room 1", "left": 15, "top": 30, "width": 12, "height": 18},
    {"room": "Room 2", "left": 45, "top": 35, "width": 12, "height": 18},
    {"room": "Room 3", "left": 70, "top": 40, "width": 12, "height": 18},
    {"room": "Room 4", "left": 25, "top": 70, "width": 12, "height": 18},
    {"room": "Room 5", "left": 65, "top": 70, "width": 12, "height": 18},
]

DETECTOR_MAP = {
    "Room 1": [{"x": 35, "y": 35, "label": "NH₃"}],
    "Room 2": [{"x": 40, "y": 50, "label": "Cl₂"}],
    "Room 3": [{"x": 28, "y": 72, "label": "O₂"}],
    "Room 4": [{"x": 60, "y": 40, "label": "CO"}],
    "Room 5": [{"x": 55, "y": 60, "label": "CH₄"}],
}


# -------------------------------------------------------------------
# Facility overview renderer
# -------------------------------------------------------------------
def render_overview(images_dir: Path):
    img_path = images_dir / "Overview.png"
    b64 = load_image_b64(img_path)

    html = f"""
    <style>
      .wrap {{
        position: relative; width: 100%; max-width: 1200px; margin: 10px auto;
        border:1px solid #1f2a44; border-radius:12px; overflow:hidden;
        box-shadow: 0 24px 60px rgba(0,0,0,.30);
      }}
      .wrap img {{ width:100%; height:auto; display:block; }}
      .hotspot {{
        position:absolute; border:2px dashed rgba(56,189,248,0.9);
        background:rgba(56,189,248,0.25); border-radius:8px;
        text-align:center; font-weight:700; color:#0f172a;
        display:flex; align-items:center; justify-content:center;
        text-decoration:none; z-index:15;
      }}
      .hotspot:hover {{ background:rgba(56,189,248,0.45); }}
    </style>
    <div class="wrap">
      <img src="data:image/png;base64,{b64}" alt="Facility Overview"/>
    """

    hotspots = []
    for hs in OVERVIEW_HOTSPOTS:
        L, T, W, H = hs["left"], hs["top"], hs["width"], hs["height"]
        rn = hs["room"]
        href = f"?room={quote(rn)}"
        hotspots.append(f"""
          <a class="hotspot" href="{href}" target="_top"
             style="left:{L}%;top:{T}%;width:{W}%;height:{H}%;">
            {rn}
          </a>
        """)

    html += "\n".join(hotspots)
    html += "</div>"

    st.markdown(html, unsafe_allow_html=True)


# -------------------------------------------------------------------
# Single room renderer
# -------------------------------------------------------------------
def render_room(images_dir: Path, room: str):
    img_file = f"{room}.png"
    img_path = images_dir / img_file
    if not img_path.exists():
        st.error(f"❌ No image found for {room}")
        return

    b64 = load_image_b64(img_path)
    dets = DETECTOR_MAP.get(room, [])

    html = f"""
    <style>
      .wrap {{
        position: relative; width: 100%; max-width: 900px; margin: 10px auto;
        border:1px solid #1f2a44; border-radius:12px; overflow:hidden;
        box-shadow: 0 16px 40px rgba(0,0,0,.25);
      }}
      .wrap img {{ width:100%; height:auto; display:block; }}
      .pin {{
        position:absolute; transform:translate(-50%,-50%);
        background: rgba(239, 68, 68, .92); color: #fff; font-weight: 800;
        border: 0; border-radius: 10px; padding: 6px 10px; cursor: pointer;
        box-shadow: 0 10px 24px rgba(0,0,0,.35); text-decoration:none;
        z-index:20;
      }}
      .pin:hover {{ filter: brightness(0.95); }}
    </style>
    <div class="wrap">
      <img src="data:image/png;base64,{b64}" alt="{room}"/>
    """

    for d in dets:
        x = float(d["x"]); y = float(d["y"]); label = d["label"]
        href = f"?room={quote(room)}&det={quote(label)}"
        html += f"""
          <a class="pin" href="{href}" target="_top" style="left:{x}%;top:{y}%;">
            {label}
          </a>
        """

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)



