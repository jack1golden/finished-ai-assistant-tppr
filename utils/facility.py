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
import streamlit as st
from pathlib import Path
import base64, json
import streamlit.components.v1 as components

# ---------- helpers ----------
def _b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def _first_existing(images_dir: Path, names: list[str]) -> Path | None:
    for n in names:
        p = images_dir / n
        if p.exists():
            return p
    return None

# Rooms and their possible image filename candidates (second bundle first)
ROOM_FILE_CANDIDATES = {
    "Entry":            ["Entry.png"],
    "Room 1":           ["Room 1.png"],
    "Room 2":           ["Room 2.png", "Room 2 (1).png"],
    "Room 3":           ["Room 3.png", "Room 3 (1).png"],
    "Room 12/17":       ["Room 12 17.png", "Room 12.png", "Room 17.png"],
    "Production":       ["Room Production.png"],
    "Production 2":     ["Room Production 2.png", "Room Production2.png"],
}

OVERVIEW_CANDIDATES = ["Overview.png", "Overview (1).png"]

# Detector map persistence
def _map_path(images_dir: Path) -> Path:
    return images_dir / "detector_map.json"

def _load_map(images_dir: Path) -> dict:
    p = _map_path(images_dir)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}

def _save_map(images_dir: Path, data: dict):
    p = _map_path(images_dir)
    p.write_text(json.dumps(data, indent=2))

# API for app.py
def rooms_available(images_dir: Path) -> list[str]:
    out = []
    for rn, cands in ROOM_FILE_CANDIDATES.items():
        if _first_existing(images_dir, cands):
            out.append(rn)
    return out

# ---------- renderers ----------
def render_overview(images_dir: Path):
    img_path = _first_existing(images_dir, OVERVIEW_CANDIDATES)
    if not img_path:
        st.error("Overview image not found. Place 'Overview.png' (or 'Overview (1).png') in images/")
        return
    st.image(str(img_path), caption="Facility Overview", use_container_width=True)
    st.caption("Click a room from the left Navigation. (Hotspot overlay coming next.)")

def render_room(images_dir: Path, room: str, mapping_mode: bool = False):
    img_path = _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(room, []))
    if not img_path:
        st.error(f"No image found for **{room}**. Expected one of: {ROOM_FILE_CANDIDATES.get(room, [])}")
        return

    # load existing map
    det_map = _load_map(images_dir)
    dets = det_map.get(room, [])  # list of {label, top, left}

    # base64 image
    b64 = _b64(img_path)

    # Build HTML with overlay buttons + (optional) mapping click-capture
    # We use a custom minimal component that posts clicks back to Streamlit via postMessage.
    component_key = f"map_{room}"

    # Inject existing detector buttons
    btn_html = []
    for i, d in enumerate(dets, start=1):
        top = float(d.get("top", 50))
        left = float(d.get("left", 50))
        label = d.get("label", f"Detector {i}")
        btn_html.append(f"""
        <button class="det-btn" style="top:{top}%;left:{left}%"
                onclick="window.parent.postMessage({{isStreamlitMessage:true, type:'streamlit:setComponentValue', key: '{room}_det_{i}', value: true}}, '*');">
          {label}
        </button>
        """)

    buttons_markup = "\n".join(btn_html)

    # If mapping mode, capture clicks and show crosshair where you click
    click_capture_js = f"""
      let lastClick = null;
      img.addEventListener('click', (ev) => {{
        const r = img.getBoundingClientRect();
        const top = ( (ev.clientY - r.top) / r.height ) * 100;
        const left = ( (ev.clientX - r.left) / r.width ) * 100;
        lastClick = {{top, left}};
        // draw a temporary marker
        marker.style.display = 'block';
        marker.style.top = top + '%';
        marker.style.left = left + '%';
        // send to Streamlit
        window.parent.postMessage({{isStreamlitMessage:true, type:'streamlit:setComponentValue', key:'{component_key}', value: JSON.stringify(lastClick)}}, '*');
      }});
    """ if mapping_mode else ""

    html = f"""
    <style>
      .wrap {{
        position: relative; width: 100%; max-width: 1200px; margin: 6px 0 10px 0;
        border:1px solid #1f2a44; border-radius:12px; overflow:hidden;
        box-shadow: 0 24px 60px rgba(0,0,0,.30);
      }}
      .wrap img {{ width:100%; height:auto; display:block; }}
      .det-btn {{
        position:absolute; transform:translate(-50%,-50%);
        background: rgba(15, 23, 42, .75); color:#e2e8f0;
        border:1px solid #67e8f9; border-radius:10px; padding:6px 10px;
        font: 600 12px/1 system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
        cursor:pointer;
      }}
      .det-btn:hover {{ background: rgba(15, 23, 42, .95); }}
      .marker {{
        position:absolute; width:16px; height:16px; border-radius:50%;
        background: rgba(99,102,241,.9); border:2px solid white;
        transform:translate(-50%,-50%); pointer-events:none; display:none;
        box-shadow: 0 8px 20px rgba(0,0,0,.35);
      }}
    </style>
    <div class="wrap">
      <img id="img" src="data:image/png;base64,{b64}" alt="{room}"/>
      <div id="marker" class="marker"></div>
      {buttons_markup}
    </div>
    <script>
      const img = window.document.getElementById('img');
      const marker = window.document.getElementById('marker');
      {click_capture_js}
    </script>
    """

    components.html(html, height=720, scrolling=False, key=f"roomview_{room}")

    # Read detector button clicks (uniquely keyed)
    for i, _ in enumerate(dets, start=1):
        k = f"{room}_det_{i}"
        if k in st.session_state and st.session_state[k]:
            st.success(f"✅ {room} → {dets[i-1].get('label','Detector '+str(i))} selected")
            st.session_state[k] = False

    # Mapping controls
    if mapping_mode:
        st.info("Click anywhere on the image to add a detector at that location. Then press **Add Detector** to append it to the list below, and **Save Mapping** when finished.")

        # The click handler posts JSON into this session_state key:
        pending_key = f"map_{room}"
        pending = st.session_state.get(pending_key)

        new_label = st.text_input("New detector label", value=f"{room} Detector {len(dets)+1}")
        colA, colB, colC = st.columns([1,1,3])
        with colA:
            if st.button("Add Detector", key=f"add_{room}"):
                if pending:
                    try:
                        pt = json.loads(pending)
                        dets.append({"label": new_label, "top": float(pt["top"]), "left": float(pt["left"])})
                        # persist to disk
                        det_map[room] = dets
                        _save_map(images_dir, det_map)
                        st.session_state[pending_key] = None
                        st.success("Added. Mapping saved.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not parse click position: {e}")
                else:
                    st.warning("Click on the image first to pick a position.")

        with colB:
            if st.button("Save Mapping", key=f"save_{room}"):
                det_map[room] = dets
                _save_map(images_dir, det_map)
                st.success("Mapping saved to images/detector_map.json")

        # Show current mapping table
        if dets:
            st.markdown("**Current detectors in this room:**")
            for i, d in enumerate(dets, start=1):
                st.write(f"{i}. {d['label']}  —  top: {d['top']:.2f}%, left: {d['left']:.2f}%")
        else:
            st.caption("No detectors mapped yet.")
