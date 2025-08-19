from pathlib import Path
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# =========================================================
# HARD-CODED DETECTOR POSITIONS (percent of image width/height)
# x, y are in percent (0-100). Label is what is drawn & shown.
# Tweak these numbers to nudge the dot/label placement.
# =========================================================
DETECTOR_MAP = {
    "Room 1": [                  # sketch: NH3 centered on the equipment block
        {"label": "NH₃", "x": 55.0, "y": 55.0},
    ],
    "Room 2": [                  # sketch: CO on wall/pillar
        {"label": "CO", "x": 52.0, "y": 50.0},
    ],
    "Room 3": [                  # sketch: detector near machinery (left)
        {"label": "O₂", "x": 28.0, "y": 72.0},
    ],
    "Room 12 17": [              # sketch: Ethanol centered on long bench
        {"label": "Ethanol", "x": 58.0, "y": 36.0},
    ],
    "Room Production": [         # sketch: NH3 on the upper run, O2 at lower-right
        {"label": "NH₃", "x": 30.0, "y": 28.0},
        {"label": "O₂",  "x": 78.0, "y": 72.0},
    ],
    "Room Production 2": [       # sketch: O2 on right, H2 also on right bank
        {"label": "O₂", "x": 70.0, "y": 45.0},
        {"label": "H₂", "x": 70.0, "y": 65.0},
    ],
}

# Rooms we show in the Overview nav (order)
ROOM_ORDER = [
    "Room 1",
    "Room 2",
    "Room 3",
    "Room 12 17",
    "Room Production",
    "Room Production 2",
]

# ---------------------------------------------------------
# Simple text shadow helper for readability on busy images
# ---------------------------------------------------------
def _draw_label(draw: ImageDraw.ImageDraw, xy, text, font, fill_main=(255, 72, 72, 255)):
    x, y = xy
    shadow = (0, 0, 0, 160)
    # tiny shadow for readability
    for dx, dy in ((1,1),(1,0),(0,1),(-1,0),(0,-1)):
        draw.text((x+dx, y+dy), text, fill=shadow, font=font)
    draw.text((x, y), text, fill=fill_main, font=font)

# =========================================================
# PUBLIC API
# =========================================================
def render_overview(images_dir: Path, enable_hotspots: bool = False):
    """Show the overview image and navigation buttons."""
    st.header("🏭 Facility Overview")
    overview_path = images_dir / "Overview.png"
    if overview_path.exists():
        st.image(str(overview_path), caption="Facility Overview", use_container_width=True)
    else:
        st.error("Overview.png not found in images/")

    st.markdown("### Rooms")
    for rn in ROOM_ORDER:
        img_path = images_dir / f"{rn}.png"
        if img_path.exists():
            if st.button(f"Enter {rn}", key=f"enter_{rn}"):
                st.session_state["current_room"] = rn
                st.experimental_rerun()
        else:
            st.caption(f"({rn} image missing)")

def render_room(images_dir: Path, room: str):
    """Render a room with hard-coded detector overlays and detector buttons."""
    img_path = images_dir / f"{room}.png"
    if not img_path.exists():
        st.warning(f"No image found for {room} at {img_path}")
        return

    # Load background
    bg = Image.open(img_path).convert("RGBA")
    overlay = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Font
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font = ImageFont.load_default()

    # Get detectors for this room
    dets = DETECTOR_MAP.get(room, [])

    # Draw red dots + labels
    for i, d in enumerate(dets, start=1):
        x_px = int(d["x"] / 100.0 * bg.width)
        y_px = int(d["y"] / 100.0 * bg.height)
        r = max(6, int(min(bg.width, bg.height) * 0.008))  # scale the dot a bit by image size
        draw.ellipse((x_px - r, y_px - r, x_px + r, y_px + r), fill=(255, 72, 72, 220))
        _draw_label(draw, (x_px + r + 6, y_px - r - 2), d["label"], font)

    composed = Image.alpha_composite(bg, overlay)
    st.image(composed, caption=f"{room} — detectors", use_container_width=True)

    # Buttons to interact with detectors (hook these to your charts/AI)
    if dets:
        st.markdown("### Detectors")
        cols = st.columns(min(3, len(dets)))  # lay out a few per row
        for i, d in enumerate(dets):
            with cols[i % len(cols)]:
                if st.button(f"{d['label']}", key=f"{room}_det_{i}"):
                    st.success(f"📊 {room} → {d['label']} selected")
    else:
        st.info("No detectors mapped for this room (hard-coded map is empty).")




