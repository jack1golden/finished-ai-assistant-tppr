import base64
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import quote
from PIL import Image

# ----------------------------
# Helpers
# ----------------------------
def _b64(path: Path) -> str:
    """Return base64 string for an image file."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _first_existing(images_dir: Path, names: list[str]) -> Path | None:
    """Find first existing file in list of names inside images_dir."""
    for n in names:
        p = images_dir / n
        if p.exists():
            return p
    return None

# ----------------------------
# Room setup
# ----------------------------
ROOMS = [
    "Room 1",
    "Room 2",
    "Room 3",
    "Room 12 17",
    "Room Production",
    "Room Production 2",
]

OVERVIEW_CANDIDATES = ["Overview.png", "Overview (1).png"]

# Hotspot positions (left %, top %, width %, height %)
OVERVIEW_HOTSPOTS = {
    "Room 1": (10, 18, 16, 16),
    "Room 2": (30, 18, 16, 16),
    "Room 3": (50, 18, 16, 16),
    "Room 12 17": (70, 18, 16, 16),
    "Room Production": (22, 50, 26, 24),
    "Room Production 2": (52, 50, 26, 24),
}

# ----------------------------
# Overview renderer
# ----------------------------
def render_overview(images_dir: Path):
    st.header("🏭 Facility Overview")

    ov = _first_existing(images_dir, OVERVIEW_CANDIDATES)
    if not ov:
        st.error("Overview image not found. Add 'Overview.png' or 'Overview (1).png' in images/.")
        return

    b64 = _b64(ov)

    hotspots_html = []
    for rn in ROOMS:
        if rn not in OVERVIEW_HOTSPOTS:
            continue
        L, T, W, H = OVERVIEW_HOTSPOTS[rn]
        href = f"?room={quote(rn)}"
        hotspots_html.append(f"""
          <a class="hotspot" href="{href}" target="_top"
             style="left:{L}%;top:{T}%;width:{W}%;height:{H}%;">
            <span>{rn}</span>
          </a>
        """)
    hotspots = "\n".join(hotspots_html)

    html = f"""
    <style>
      .wrap {{
        position: relative; width: min(1200px, 96%); margin: 10px auto 16px auto;
        border-radius: 12px; border:1px solid #1f2a44; overflow:hidden;
        box-shadow: 0 24px 80px rgba(0,0,0,.35);
      }}
      .wrap img {{
        display:block; width:100%; height:auto;
      }}
      .hotspot {{
        position:absolute; display:flex; align-items:flex-start; justify-content:flex-start;
        color:#e2e8f0; font: 700 12px/1.2 system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;
        border:1px dashed rgba(0,200,255,.35); border-radius:12px; padding:6px;
        text-decoration:none; background: rgba(13, 25, 40, .12);
        z-index: 20;
      }}
      .hotspot:hover {{ background: rgba(13, 25, 40, .22); }}
      .hotspot span {{
        background: rgba(15,23,42,.65); padding: 2px 6px; border-radius: 8px;
        border:1px solid rgba(103,232,249,.5);
      }}
    </style>
    <div class="wrap">
      <img src="data:image/png;base64,{b64}" alt="overview"/>
      {hotspots}
    </div>
    """

    components.html(html, height=760, scrolling=False)

# ----------------------------
# Room renderer
# ----------------------------
def render_room(images_dir: Path, room: str):
    """Show a room image + detectors (hardcoded demo for now)."""
    img_file = None
    for ext in ["png", "jpg", "jpeg"]:
        candidate = images_dir / f"{room}.{ext}"
        if candidate.exists():
            img_file = candidate
            break

    if not img_file:
        st.warning(f"No image found for {room}")
        return

    st.subheader(f"🚪 {room}")
    st.image(str(img_file), caption=room, use_container_width=True)

    # Example detector (hardcoded coords for now)
    if st.button(f"Detector in {room}"):
        st.line_chart({"Gas": [0.1, 0.3, 0.7, 0.2, 0.5]})

    if st.button("⬅️ Back to Overview"):
        st.session_state["current_room"] = None
