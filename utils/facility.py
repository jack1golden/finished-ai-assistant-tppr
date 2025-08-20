from pathlib import Path
import json
import streamlit as st
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

# We’ll tolerate your alternate filenames from the “second bundle”
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

def _first_existing(images_dir: Path, names: list[str]) -> Path | None:
    for n in names:
        p = images_dir / n
        if p.exists():
            return p
    return None

# -------- Overrides (saved via Quick Adjust) ----------
def _map_path(images_dir: Path) -> Path:
    return images_dir / "detector_map.json"

def _load_overrides(images_dir: Path) -> dict:
    p = _map_path(images_dir)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}

def _save_overrides(images_dir: Path, data: dict):
    _map_path(images_dir).write_text(json.dumps(data, indent=2))

def _get_detectors_for_room(images_dir: Path, room: str):
    overrides = _load_overrides(images_dir)
    if room in overrides:
        return overrides[room]
    return DETECTOR_MAP_DEFAULT.get(room, [])

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

def render_room(images_dir: Path, room: str):
    img_path = _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(room, []))
    if not img_path:
        st.warning(f"No image found for {room}. Looked for: {ROOM_FILE_CANDIDATES.get(room, [])}")
        return

    # Load base image
    bg = Image.open(img_path).convert("RGBA")
    overlay = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Font for labels
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font = ImageFont.load_default()

    # Use overrides if present, else defaults
    dets = _get_detectors_for_room(images_dir, room)

    # Draw pins + labels
    for i, d in enumerate(dets, start=1):
        x_px = int(d["x"] / 100.0 * bg.width)
        y_px = int(d["y"] / 100.0 * bg.height)
        r = max(6, int(min(bg.width, bg.height) * 0.008))
        draw.ellipse((x_px - r, y_px - r, x_px + r, y_px + r), fill=(255, 72, 72, 220))
        label = d.get("label", f"D{i}")
        _draw_label(draw, (x_px + r + 6, y_px - r - 2), label, font)

    composed = Image.alpha_composite(bg, overlay)
    st.image(composed, caption=f"{room} — detectors", use_container_width=True)

    # Detector buttons (hook to charts/AI)
    if dets:
        st.markdown("### Detectors")
        cols = st.columns(min(3, len(dets)))
        for i, d in enumerate(dets):
            with cols[i % len(cols)]:
                if st.button(f"{d['label']}", key=f"{room}_det_{i}"):
                    st.session_state["selected_detector"] = f"{room} — {d['label']}"
                    st.success(f"📊 {room} → {d['label']} selected")
    else:
        st.info("No detectors configured for this room.")

    # ---------- Quick Adjust (no mapping mode) ----------
    with st.expander("⚙️ Quick Adjust positions (optional, saves to images/detector_map.json)"):
        if not dets:
            st.caption("Nothing to adjust.")
            return

        # Build editable copies
        new_dets = []
        for i, d in enumerate(dets, start=1):
            c1, c2, c3 = st.columns([2, 2, 3])
            with c1:
                x = st.number_input(f"{d['label']} — X %", min_value=0.0, max_value=100.0, step=0.5, value=float(d["x"]), key=f"adjx_{room}_{i}")
            with c2:
                y = st.number_input(f"{d['label']} — Y %", min_value=0.0, max_value=100.0, step=0.5, value=float(d["y"]), key=f"adjy_{room}_{i}")
            with c3:
                lbl = st.text_input("Label", value=d.get("label", f"D{i}"), key=f"adjlbl_{room}_{i}")
            new_dets.append({"x": float(x), "y": float(y), "label": lbl})

        colA, colB = st.columns(2)
        with colA:
            if st.button("💾 Save Positions", key=f"save_{room}"):
                overrides = _load_overrides(images_dir)
                overrides[room] = new_dets
                _save_overrides(images_dir, overrides)
                st.success("Saved positions. Reloading…")
                st.rerun()
        with colB:
            if st.button("↩️ Reset overrides for this room", key=f"reset_{room}"):
                overrides = _load_overrides(images_dir)
                if room in overrides:
                    del overrides[room]
                    _save_overrides(images_dir, overrides)
                st.success("Overrides cleared. Reloading…")
                st.rerun()

def _draw_label(draw: ImageDraw.ImageDraw, xy, text, font, fill=(255,72,72,255)):
    x, y = xy
    shadow = (0, 0, 0, 160)
    # small shadow for readability
    for dx, dy in ((1,1), (1,0), (0,1), (-1,0), (0,-1)):
        draw.text((x + dx, y + dy), text, fill=shadow, font=font)
    draw.text((x, y), text, fill=fill, font=font)


