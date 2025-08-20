from pathlib import Path
import base64
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont

# =========================================================
# Hard-coded detector positions (percentages)
# Adjust x/y here if needed. Labels show on pins & buttons.
# =========================================================
DETECTOR_MAP_DEFAULT = {
    "Room 1": [
        {"label": "NH₃", "x": 55.0, "y": 55.0},
    ],
    "Room 2": [
        {"label": "CO", "x": 52.0, "y": 50.0},
    ],
    "Room 3": [
        {"label": "O₂", "x": 28.0, "y": 72.0},
    ],
    "Room 12 17": [
        {"label": "Ethanol", "x": 58.0, "y": 36.0},
    ],
    "Room Production": [
        {"label": "NH₃", "x": 30.0, "y": 28.0},
        {"label": "O₂",  "x": 78.0, "y": 72.0},
    ],
    "Room Production 2": [
        {"label": "O₂", "x": 70.0, "y": 45.0},
        {"label": "H₂", "x": 70.0, "y": 65.0},
    ],
}

# We’ll tolerate alternate filenames from your “second bundle”
ROOM_FILE_CANDIDATES = {
    "Room 1":           ["Room 1.png"],
    "Room 2":           ["Room 2.png", "Room 2 (1).png"],
    "Room 3":           ["Room 3.png", "Room 3 (1).png"],
    "Room 12 17":       ["Room 12 17.png", "Room 12.png", "Room 17.png"],
    "Room Production":  ["Room Production.png"],
    "Room Production 2":["Room Production 2.png", "Room Production2.png"],
}
OVERVIEW_CANDIDATES = ["Overview.png", "Overview (1).png"]

ROOM_ORDER = [
    "Room 1",
    "Room 2",
    "Room 3",
    "Room 12 17",
    "Room Production",
    "Room Production 2",
]

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def _first_existing(images_dir: Path, names: list[str]) -> Path | None:
    for n in names:
        p = images_dir / n
        if p.exists():
            return p
    return None

def _b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

# =========================================================
# Public API
# =========================================================
def rooms_available(images_dir: Path) -> list[str]:
    out = []
    for rn in ROOM_ORDER:
        if _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(rn, [])):
            out.append(rn)
    return out

def render_overview(images_dir: Path):
    st.header("🏭 Facility Overview")

    ov = _first_existing(images_dir, OVERVIEW_CANDIDATES)
    if ov:
        st.image(str(ov), caption="Facility Overview", use_container_width=True)
    else:
        st.error("Overview image not found. Please add 'Overview.png' (or 'Overview (1).png') to images/.")

    st.markdown("### Rooms")
    existing_rooms = rooms_available(images_dir)
    if not existing_rooms:
        st.caption("No room images detected in images/. Expected names like 'Room 1.png', 'Room Production.png', etc.")
        return

    # neat grid of enter buttons (3 per row)
    for i in range(0, len(existing_rooms), 3):
        cols = st.columns(3)
        for j, rn in enumerate(existing_rooms[i:i+3]):
            with cols[j]:
                st.markdown(f"**{rn}**")
                if st.button("Enter", key=f"enter_{rn}"):
                    st.session_state["current_room"] = rn
                    st.rerun()

def render_room(images_dir: Path, room: str) -> str | None:
    """
    Shows the room as an HTML overlay with clickable detector pins.
    Also renders fallback buttons below. Returns the label of a clicked pin,
    or None if none was clicked.
    """
    img_path = _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(room, []))
    if not img_path:
        st.warning(f"No image found for {room}. Looked for: {ROOM_FILE_CANDIDATES.get(room, [])}")
        return None

    dets = DETECTOR_MAP_DEFAULT.get(room, [])

    # Build HTML overlay with clickable pins
    b64 = _b64(img_path)
    pin_html = []
    for i, d in enumerate(dets, start=1):
        x = float(d["x"])
        y = float(d["y"])
        label = d["label"]
        # HTML pin; clicking posts a message to Streamlit to set a value in session_state
        pin_html.append(f"""
          <button class="pin" style="left:{x}%; top:{y}%;"
                  onclick="window.parent.postMessage({{isStreamlitMessage:true, type:'streamlit:setComponentValue', key:'pin_click_{room}_{i}', value:'{label}'}}, '*');">
            {label}
          </button>
        """)

    pins = "\n".join(pin_html)
    html = f"""
    <style>
      .wrap {{
        position: relative; width: 100%; max-width: 1200px; margin: 6px 0 10px 0;
        border:1px solid #1f2a44; border-radius:12px; overflow:hidden;
        box-shadow: 0 24px 60px rgba(0,0,0,.30);
      }}
      .wrap img {{ width:100%; height:auto; display:block; }}
      .pin {{
        position:absolute; transform:translate(-50%,-50%);
        background: rgba(239, 68, 68, .90); color: #fff; font-weight: 700;
        border: 0; border-radius: 10px; padding: 6px 10px; cursor: pointer;
        box-shadow: 0 10px 24px rgba(0,0,0,.35);
      }}
      .pin:hover {{ filter: brightness(0.95); }}
    </style>
    <div class="wrap">
      <img src="data:image/png;base64,{b64}" alt="{room}"/>
      {pins}
    </div>
    """

    # Render overlay
    try:
        components.html(html, height=720, scrolling=False)
    except Exception as e:
        st.error(f"❌ Error rendering room overlay: {e}")

    # Read clicks from pins
    clicked_label = None
    for i, d in enumerate(dets, start=1):
        k = f"pin_click_{room}_{i}"
        if k in st.session_state and st.session_state[k]:
            clicked_label = st.session_state[k]
            st.session_state[k] = None

    # Fallback buttons under the image (also select)
    if dets:
        st.markdown("### Detectors")
        cols = st.columns(min(3, len(dets)))
        for i, d in enumerate(dets):
            with cols[i % len(cols)]:
                if st.button(f"{d['label']}", key=f"{room}_btn_{i}"):
                    clicked_label = d["label"]

    return clicked_label


