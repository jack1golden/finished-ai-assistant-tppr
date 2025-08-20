from pathlib import Path
from urllib.parse import quote
import time
import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import base64

# -----------------------------------------------
# Hotspots over Overview (in percent L,T,W,H)
# Tune these to where the rooms appear on Overview.png
# -----------------------------------------------
OVERVIEW_HOTSPOTS = {
    "Room 1":       (10, 18, 16, 16),
    "Room 2":       (30, 18, 16, 16),
    "Room 3":       (50, 18, 16, 16),
    "Room 12 17":   (70, 18, 16, 16),
    "Room Production":  (22, 48, 26, 24),
    "Room Production 2":(52, 48, 26, 24),
}

# Try alternate filenames (second bundle friendly)
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
    "Room 1","Room 2","Room 3","Room 12 17","Room Production","Room Production 2"
]

# -----------------------------------------------
# Detector locations (percent x,y) and labels
# You gave Room 1 exactly x=35, y=35; others are reasonable starters
# Nudge later if needed (Quick Adjust not included in this minimal build).
# -----------------------------------------------
DETECTOR_MAP = {
    "Room 1": [ {"label": "NH₃", "x": 35.0, "y": 35.0} ],
    "Room 2": [ {"label": "CO",  "x": 52.0, "y": 50.0} ],
    "Room 3": [ {"label": "O₂",  "x": 28.0, "y": 72.0} ],
    "Room 12 17": [ {"label": "Ethanol", "x": 58.0, "y": 36.0} ],
    "Room Production": [
        {"label": "NH₃", "x": 30.0, "y": 28.0},
        {"label": "O₂",  "x": 78.0, "y": 72.0},
    ],
    "Room Production 2": [
        {"label": "O₂", "x": 70.0, "y": 45.0},
        {"label": "H₂", "x": 70.0, "y": 65.0},
    ],
}

GAS_COLOR = {
    "NH₃": (0, 180, 170, 130),    # teal-ish cloud
    "CO":  (160,160,160,130),     # grey
    "O₂":  (50,120,255,110),      # oxygen dip visualization
    "Ethanol": (255,140,0,120),   # orange
    "H₂":  (185, 90, 255, 120),   # violet
}

# -----------------------------------------------
# Helpers
# -----------------------------------------------
def _first_existing(images_dir: Path, names: list[str]) -> Path | None:
    for n in names:
        p = images_dir / n
        if p.exists():
            return p
    return None

def rooms_available(images_dir: Path) -> list[str]:
    out = []
    for rn in ROOM_ORDER:
        if _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(rn, [])):
            out.append(rn)
    return out

def _b64img(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def _draw_label(draw: ImageDraw.ImageDraw, xy, text, font, fill=(255,72,72,255)):
    x, y = xy
    shadow = (0,0,0,160)
    for dx, dy in ((1,1),(1,0),(0,1),(-1,0),(0,-1)):
        draw.text((x+dx, y+dy), text, fill=shadow, font=font)
    draw.text((x, y), text, fill=fill, font=font)

# -----------------------------------------------
# Overview with clickable hotspots (link anchors)
# -----------------------------------------------
def render_overview(images_dir: Path):
    st.header("🏭 Facility Overview")

    ov = _first_existing(images_dir, OVERVIEW_CANDIDATES)
    if not ov:
        st.error("Overview image not found. Add 'Overview.png' (or 'Overview (1).png') to images/.")
        return

    # We render the overview image with overlayed <a> regions that link via query params.
    b64 = _b64img(ov)
    hotspots = []
    for rn, (L,T,W,H) in OVERVIEW_HOTSPOTS.items():
        if rn not in rooms_available(images_dir):
            continue
        href = f"?room={quote(rn)}"
        hotspots.append(f"""
          <a class="hotspot" href="{href}" style="left:{L}%;top:{T}%;width:{W}%;height:{H}%;">
            <span>{rn}</span>
          </a>
        """)
    hs_html = "\n".join(hotspots)

    html = f"""
    <style>
      .wrap {{
        position: relative; width: min(1200px, 96%); margin: 10px auto 16px auto;
        border-radius: 12px; border:1px solid #1f2a44; overflow:hidden;
        box-shadow: 0 24px 80px rgba(0,0,0,.35);
      }}
      .wrap img {{ display:block; width:100%; height:auto; }}
      .hotspot {{
        position:absolute; display:flex; align-items:flex-start; justify-content:flex-start;
        color:#e2e8f0; font: 700 12px/1.2 system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;
        border:1px dashed rgba(0,200,255,.35); border-radius:12px; padding:6px;
        text-decoration:none; background: rgba(13, 25, 40, .10);
      }}
      .hotspot:hover {{ background: rgba(13, 25, 40, .20); }}
      .hotspot span {{
        background: rgba(15,23,42,.65); padding: 2px 6px; border-radius: 8px; border:1px solid rgba(103,232,249,.5);
      }}
    </style>
    <div class="wrap">
      <img src="data:image/png;base64,{b64}" alt="overview"/>
      {hs_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    # Fallback grid of room buttons (in case overlay fails)
    st.markdown("#### Rooms")
    for i, rn in enumerate(rooms_available(images_dir)):
        cols = st.columns(3)
        with cols[i % 3]:
            if st.button(f"Enter {rn}", key=f"enter_{rn}"):
                st.query_params["room"] = rn
                st.rerun()

# -----------------------------------------------
# Room view with detector pins (as links)
# -----------------------------------------------
def render_room(images_dir: Path, room: str):
    img_path = _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(room, []))
    if not img_path:
        st.warning(f"No image found for {room}. Searched: {ROOM_FILE_CANDIDATES.get(room, [])}")
        return

    dets = DETECTOR_MAP.get(room, [])
    b64 = _b64img(img_path)

    # Build pin overlay — each pin is an <a> that sets ?room=..&det=..
    pins = []
    for d in dets:
        x = float(d["x"]); y = float(d["y"]); label = d["label"]
        href = f"?room={quote(room)}&det={quote(label)}"
        pins.append(f"""
          <a class="pin" href="{href}" style="left:{x}%;top:{y}%;">
            {label}
          </a>
        """)
    pins_html = "\n".join(pins)

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
        background: rgba(239, 68, 68, .92); color: #fff; font-weight: 800;
        border: 0; border-radius: 10px; padding: 6px 10px; cursor: pointer;
        box-shadow: 0 10px 24px rgba(0,0,0,.35); text-decoration:none;
      }}
      .pin:hover {{ filter: brightness(0.95); }}
    </style>
    <div class="wrap">
      <img src="data:image/png;base64,{b64}" alt="{room}"/>
      {pins_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    # Fallback detector buttons (in case overlay links are blocked)
    if dets:
        st.markdown("### Detectors")
        cols = st.columns(min(3, len(dets)))
        for i, d in enumerate(dets):
            with cols[i % len(cols)]:
                if st.button(d["label"], key=f"{room}_btn_{i}"):
                    # update query params for consistency
                    st.query_params["room"] = room
                    st.query_params["det"]  = d["label"]
                    st.rerun()

# -----------------------------------------------
# Gas leak + shutters animation (in-place)
# -----------------------------------------------
def simulate_gas_and_shutters(images_dir: Path, room: str, preferred_label: str | None = None):
    """
    Draws a growing colored cloud from the detector, then closes shutters, then fades out.
    Runs inside a placeholder to look smooth.
    """
    img_path = _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(room, []))
    if not img_path:
        st.warning("Room image not found; cannot simulate.")
        return

    base = Image.open(img_path).convert("RGBA")
    W, H = base.size

    # pick source (detector)
    dets = DETECTOR_MAP.get(room, [])
    src = dets[0] if dets else {"label": "NH₃", "x": 50.0, "y": 50.0}
    if preferred_label:
        for d in dets:
            if d["label"] == preferred_label:
                src = d
                break

    label = src["label"]
    color = GAS_COLOR.get(label, (239,68,68,120))
    cx = int(src["x"] * W / 100.0)
    cy = int(src["y"] * H / 100.0)

    holder = st.empty()
    frames = 36
    max_r = int(min(W, H) * 0.55)

    # Legend
    st.caption("Legend — gas cloud color by type: NH₃=teal, CO=grey, O₂=blue, Ethanol=orange, H₂=violet")

    # Phase 1: grow cloud
    for i in range(frames):
        r = int(max_r * (i+1) / frames)
        overlay = Image.new("RGBA", (W, H), (0,0,0,0))
        mask = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(mask)
        d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=180)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=max(4, r*0.08)))
        cloud = Image.new("RGBA", (W, H), color)
        overlay = Image.composite(cloud, overlay, mask)
        composed = Image.alpha_composite(base, overlay)
        holder.image(composed, use_container_width=True)
        time.sleep(0.05)

    # Phase 2: shutters close (top & bottom bands sliding to center)
    for j in range(18):
        frac = (j+1)/18.0
        band_h = int(H * 0.5 * frac)
        overlay = Image.new("RGBA", (W, H), (0,0,0,0))
        d = ImageDraw.Draw(overlay)
        shutter_col = (24, 36, 48, 180)
        d.rectangle((0, 0, W, band_h), fill=shutter_col)
        d.rectangle((0, H-band_h, W, H), fill=shutter_col)
        composed = Image.alpha_composite(base, overlay)
        holder.image(composed, use_container_width=True)
        time.sleep(0.05)

    # Phase 3: fade out to clear view
    for k in range(10):
        alpha = int(255 * (1 - (k+1)/10))
        fade = base.copy()
        fade.putalpha(alpha)
        holder.image(base, use_container_width=True)
        time.sleep(0.03)


