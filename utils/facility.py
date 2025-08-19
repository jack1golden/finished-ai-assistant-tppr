from pathlib import Path
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# =========================================================
# HARD-CODED DETECTOR POSITIONS (in % of image width/height)
# Tweak x/y here to nudge dots/labels.
# =========================================================
DETECTOR_MAP = {
    "Room 1": [                  # NH3 centered on equipment block
        {"label": "NH₃", "x": 55.0, "y": 55.0},
    ],
    "Room 2": [                  # CO on wall/pillar
        {"label": "CO", "x": 52.0, "y": 50.0},
    ],
    "Room 3": [                  # O2 near machinery (left)
        {"label": "O₂", "x": 28.0, "y": 72.0},
    ],
    "Room 12 17": [              # Ethanol centered on long bench
        {"label": "Ethanol", "x": 58.0, "y": 36.0},
    ],
    "Room Production": [         # NH3 on upper run, O2 at lower-right
        {"label": "NH₃", "x": 30.0, "y": 28.0},
        {"label": "O₂",  "x": 78.0, "y": 72.0},
    ],
    "Room Production 2": [       # O2 + H2 on right bank
        {"label": "O₂", "x": 70.0, "y": 45.0},
        {"label": "H₂", "x": 70.0, "y": 65.0},
    ],
}

# We’ll try these filenames for each room (handles your second bundle)
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

def _draw_label(draw: ImageDraw.ImageDraw, xy, text, font, fill=(255,72,72,255)):
    x, y = xy
    shadow = (0,0,0,160)
    for dx, dy in ((1,1),(1,0),(0,1),(-1,0),(0,-1)):
        draw.text((x+dx, y+dy), text, fill=shadow, font=font)
    draw.text((x, y), text, fill=fill, font=font)

# =========================================================
# Overview (no mapping mode, simple room buttons)
# =========================================================
def render_overview(images_dir: Path):
    st.header("🏭 Facility Overview")

    ov = _first_existing(images_dir, OVERVIEW_CANDIDATES)
    if ov:
        st.image(str(ov), caption="Facility Overview", use_container_width=True)
    else:
        st.error("Overview image not found. Please add 'Overview.png' (or 'Overview (1).png') to images/.")

    st.markdown("### Rooms")
    # Show room buttons in a tidy grid (3 per row)
    existing_rooms = [rn for rn in ROOM_ORDER if _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(rn, []))]
    if not existing_rooms:
        st.caption("No room images detected in images/. Expected names like 'Room 1.png', 'Room Production.png', etc.")
        return

    for i in range(0, len(existing_rooms), 3):
        cols = st.columns(3)
        for j, rn in enumerate(existing_rooms[i:i+3]):
            with cols[j]:
                st.markdown(f"**{rn}**")
                if st.button("Enter", key=f"enter_{rn}"):
                    st.session_state["current_room"] = rn
                    st.experimental_rerun()

# =========================================================
# Room view with hard-coded detector overlays
# =========================================================
def render_room(images_dir: Path, room: str):
    img_path = _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(room, []))
    if not img_path:
        st.warning(f"No image found for {room}. Looked for: {ROOM_FILE_CANDIDATES.get(room, [])}")
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

    dets = DETECTOR_MAP.get(room, [])

    # Draw red dots + labels
    for i, d in enumerate(dets, start=1):
        x_px = int(d["x"] / 100.0 * bg.width)
        y_px = int(d["y"] / 100.0 * bg.height)
        r = max(6, int(min(bg.width, bg.height) * 0.008))  # scale dot with image size
        draw.ellipse((x_px - r, y_px - r, x_px + r, y_px + r), fill=(255, 72, 72, 220))
        _draw_label(draw, (x_px + r + 6, y_px - r - 2), d["label"], font)

    composed = Image.alpha_composite(bg, overlay)
    st.image(composed, caption=f"{room} — detectors", use_container_width=True)

    # Buttons below image for interaction / charts / AI
    if dets:
        st.markdown("### Detectors")
        cols = st.columns(min(3, len(dets)))
        for i, d in enumerate(dets):
            with cols[i % len(cols)]:
                if st.button(f"{d['label']}", key=f"{room}_det_{i}"):
                    st.success(f"📊 {room} → {d['label']} selected")
    else:
        st.info("No detectors mapped for this room (hard-coded map is empty).")




