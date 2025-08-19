import base64
import json
from pathlib import Path
import streamlit as st
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

# Rooms → candidate filenames (second bundle names included)
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

# Optional hotspots on the overview (percent L, T, W, H).
# These are placeholders; adjust to your Overview image later if needed.
ROOM_HOTSPOTS = {
    "Room 1":       (10, 15, 18, 18),
    "Room 2":       (32, 15, 18, 18),
    "Room 3":       (54, 15, 18, 18),
    "Room 12/17":   (76, 15, 18, 18),
    "Production":   (20, 48, 28, 25),
    "Production 2": (52, 48, 28, 25),
}

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
def render_overview(images_dir: Path, enable_hotspots: bool = True):
    img_path = _first_existing(images_dir, OVERVIEW_CANDIDATES)
    if not img_path:
        st.error("Overview image not found. Place 'Overview.png' (or 'Overview (1).png') in images/")
        return

    if not enable_hotspots:
        st.image(str(img_path), caption="Facility Overview", use_container_width=True)
        return

    # With hotspots overlayed
    b64 = _b64(img_path)
    # Build hotspot anchors (clicks -> postMessage enter_room)
    hotspot_html = []
    for rn, (L,T,W,H) in ROOM_HOTSPOTS.items():
        if rn not in rooms_available(images_dir):
            continue  # skip rooms without images
        hotspot_html.append(
            f"""
            <a class="hotspot"
               style="left:{L}%;top:{T}%;width:{W}%;height:{H}%;"
               onclick="window.parent.postMessage({{isStreamlitMessage:true, type:'streamlit:setComponentValue', key:'enter_room', value:'{rn}'}}, '*'); return false;">
               {rn}
            </a>
            """
        )
    hotspots_markup = "\n".join(hotspot_html)

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
        color:#67e8f9; font: 600 12px/1.2 system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
        border:1px dashed rgba(0,200,255,.35); border-radius:12px; padding:6px;
        text-decoration:none; background: rgba(13, 25, 40, .06);
      }}
      .hotspot:hover {{ background: rgba(13, 25, 40, .16); }}
      #fx {{ position:absolute; left:0; top:0; width:100%; height:100%; pointer-events:none; }}
    </style>
    <div class="wrap">
      <img id="bg" src="data:image/png;base64,{b64}" alt="facility"/>
      {hotspots_markup}
    </div>
    """

    try:
        components.html(html, height=760, scrolling=False)
    except Exception as e:
        st.error(f"❌ Error rendering overview: {e}")

    # Handle hotspot click -> enter room
    if "enter_room" in st.session_state and st.session_state["enter_room"]:
        st.session_state["current_room"] = st.session_state["enter_room"]
        st.session_state["enter_room"] = None
        st.rerun()

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
        lastClick = {{top: top, left: left}};
        // draw a temporary marker
        marker.style.display = 'block';
        marker.style.top = top + '%';
        marker.style.left = left + '%';
        // send to Streamlit
        window.parent.postMessage({{isStreamlitMessage:true, type:'streamlit:setComponentValue', key:'map_click_{room}', value: JSON.stringify(lastClick)}}, '*');
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

    try:
        components.html(html, height=720, scrolling=False)
    except Exception as e:
        st.error(f"❌ Error rendering room overlay: {e}")

    # Read detector button clicks (uniquely keyed)
    for i, _ in enumerate(dets, start=1):
        k = f"{room}_det_{i}"
        if k in st.session_state and st.session_state[k]:
            st.success(f"✅ {room} → {dets[i-1].get('label','Detector '+str(i))} selected")
            st.session_state[k] = False

    # Mapping controls
    if mapping_mode:
        st.info("Click anywhere on the image to add a detector at that location. Then press **Add Detector** to append it, and **Save Mapping** when finished.")

        pending_key = f"map_click_{room}"
        pending = st.session_state.get(pending_key)

        new_label = st.text_input("New detector label", value=f"{room} Detector {len(dets)+1}", key=f"label_{room}")
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

