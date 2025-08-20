import json
import base64
import random
from pathlib import Path
from urllib.parse import quote, unquote

import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont

# Canvas for calibration (click on image)
try:
    from streamlit_drawable_canvas import st_canvas
except Exception:
    st_canvas = None

# ─────────────────────────────────────────────────────────
# Static config
# ─────────────────────────────────────────────────────────
ROOMS = [
    "Room 1", "Room 2", "Room 3",
    "Room 12 17", "Room Production", "Room Production 2",
]

ROOM_FILE_CANDIDATES = {
    "Room 1": ["Room 1.png"],
    "Room 2": ["Room 2 (1).png", "Room 2.png"],
    "Room 3": ["Room 3 (1).png", "Room 3.png"],
    "Room 12 17": ["Room 12 17.png", "Room 12.png", "Room 17.png"],
    "Room Production": ["Room Production.png"],
    "Room Production 2": ["Room Production 2.png", "Room Production2.png"],
}
OVERVIEW_CANDIDATES = ["Overview.png", "Overview (1).png", "overview.png"]

GAS_RANGES = {
    "NH₃": "0–50 ppm",
    "O₂": "19–23 %",
    "CO₂": "0–5000 ppm",
    "H₂S": "0–100 ppm",
    "CO": "0–200 ppm",
    "CH₄": "0–100 %LEL",
    "Ethanol": "0–1000 ppm",
    "H₂": "0–1000 ppm",
}

GAS_COLOUR = {
    "NH₃": "#38bdf8", "CO": "#f97316", "O₂": "#22c55e", "H₂": "#a855f7",
    "CH₄": "#f59e0b", "Ethanol": "#ef4444", "CO₂": "#06b6d4", "H₂S": "#eab308",
}

# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────
def _b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _first_existing(images_dir: Path, candidates: list[str]) -> Path | None:
    for name in candidates:
        p = images_dir / name
        if p.exists():
            return p
    return None

def _mapping_paths(base_dir: Path) -> tuple[Path, Path]:
    root = base_dir.parent
    return root / "mapping_overview.json", root / "mapping_rooms.json"

def _load_mappings(images_dir: Path):
    ov_path, rm_path = _mapping_paths(images_dir)
    ov = json.loads(ov_path.read_text()) if ov_path.exists() else None
    rm = json.loads(rm_path.read_text()) if rm_path.exists() else None
    return ov, rm

def _save_overview_mapping(images_dir: Path, mapping: dict):
    ov_path, _ = _mapping_paths(images_dir)
    ov_path.write_text(json.dumps(mapping, indent=2))

def _save_room_mapping(images_dir: Path, mapping: dict):
    _, rm_path = _mapping_paths(images_dir)
    rm_path.write_text(json.dumps(mapping, indent=2))

def _canvas_dims(img: Image.Image, max_w: int = 1200) -> tuple[int, int]:
    """Scale canvas to max_w, keep aspect."""
    w, h = img.size
    if w <= max_w:
        return w, h
    scale = max_w / w
    return int(w * scale), int(h * scale)

# Defaults if no JSON yet
DEFAULT_OV_HOTSPOTS = {
    "Room 1": (12, 20, 15, 16),
    "Room 2": (32, 20, 15, 16),
    "Room 3": (52, 20, 15, 16),
    "Room 12 17": (72, 20, 15, 16),
    "Room Production": (24, 52, 24, 22),
    "Room Production 2": (54, 52, 24, 22),
}

DEFAULT_ROOM_DETECTORS = {
    "Room 1": [{"label": "NH₃", "x": 35.0, "y": 35.0}],
    "Room 2": [{"label": "CO",  "x": 93.0, "y": 33.0}],
    "Room 3": [{"label": "O₂",  "x": 28.0, "y": 72.0}],
    "Room 12 17": [{"label": "Ethanol", "x": 58.0, "y": 36.0}],
    "Room Production": [
        {"label": "NH₃", "x": 30.0, "y": 28.0},
        {"label": "O₂",  "x": 78.0, "y": 72.0},
    ],
    "Room Production 2": [
        {"label": "O₂", "x": 70.0, "y": 45.0},
        {"label": "H₂", "x": 70.0, "y": 65.0},
    ],
}

# ─────────────────────────────────────────────────────────
# Live reading simulator
# ─────────────────────────────────────────────────────────
def _sim_key(room: str, label: str) -> str:
    return f"{room}::{label}"

def _next_value(room: str, label: str) -> float:
    key = _sim_key(room, label)
    state = st.session_state.setdefault("det_sim", {})
    v = state.get(key, random.uniform(0.0, 1.0) * 10.0)
    v += random.uniform(-0.6, 0.9)
    v = max(0.0, v)
    state[key] = v
    return v

def _series(room: str, label: str, n: int = 60):
    key = _sim_key(room, label)
    buf = st.session_state.setdefault("det_buf", {}).setdefault(key, [])
    buf.append(_next_value(room, label))
    if len(buf) > n:
        buf[:] = buf[-n:]
    return buf

# ─────────────────────────────────────────────────────────
# Logo
# ─────────────────────────────────────────────────────────
def render_logo(images_dir: Path):
    user_logo = images_dir / "logo.png"
    if user_logo.exists():
        st.image(str(user_logo), use_container_width=True)
        return
    # Fallback
    W, H = 900, 260
    img = Image.new("RGBA", (W, H), (13, 17, 23, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((40, 60, 180, 220), 18, outline=(80, 200, 255), width=6)
    try:
        fnt = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
    except Exception:
        fnt = None
    d.text((40, 15), "Pharma Safety HMI — Innovation Project", fill=(200, 230, 255), font=fnt)
    st.image(img, use_container_width=True)

# ─────────────────────────────────────────────────────────
# OVERVIEW
# ─────────────────────────────────────────────────────────
def render_overview(images_dir: Path, calibrate: bool = False, cal_room: str = "Room 1"):
    ov_path = _first_existing(images_dir, OVERVIEW_CANDIDATES)
    if not ov_path:
        st.error("Overview image not found. Put 'Overview.png' (or 'Overview (1).png') in images/.")
        return

    ov_map, _ = _load_mappings(images_dir)
    if ov_map is None:
        ov_map = DEFAULT_OV_HOTSPOTS.copy()

    # Only show rooms with images available
    available = set(r for r in ROOMS if _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(r, [])))

    # ── CALIBRATION MODE (click-to-place using st_canvas)
    if calibrate:
        if st_canvas is None:
            st.error("Calibration requires streamlit-drawable-canvas. Add 'streamlit-drawable-canvas==0.9.3' to requirements.txt.")
            return

        img = Image.open(ov_path)
        cw, ch = _canvas_dims(img, max_w=1200)
        st.markdown("#### Overview Calibration — click to set **top-left** for the selected room box")
        colL, colR = st.columns([3, 1])
        with colR:
            sel = st.selectbox("Room", list(ROOMS), index=list(ROOMS).index(cal_room) if cal_room in ROOMS else 0, key="ov_cal_room_sel")
            cur = ov_map.get(sel, DEFAULT_OV_HOTSPOTS.get(sel, (12,20,15,16)))
            L, T, W, H = cur
            W = st.slider("Width (%)", 5.0, 40.0, float(W), 0.5, key="ov_cal_w")
            H = st.slider("Height (%)", 5.0, 40.0, float(H), 0.5, key="ov_cal_h")
            if st.button("💾 Save size", key="ov_cal_save_size"):
                ov_map[sel] = (L, T, W, H)
                _save_overview_mapping(images_dir, ov_map)
                st.success(f"Saved size for {sel}: W={W:.1f}%, H={H:.1f}%")

        with colL:
            canvas = st_canvas(
                background_image=img,
                update_streamlit=True,
                height=ch,
                width=cw,
                drawing_mode="point",
                point_display_radius=6,
                stroke_width=1,
                key="ov_canvas",
            )

            if canvas.json_data and canvas.json_data.get("objects"):
                obj = canvas.json_data["objects"][-1]
                left = float(obj.get("left", 0))
                top = float(obj.get("top", 0))
                # center correction (circle has 'radius'; otherwise width/2)
                radius = float(obj.get("radius", 0)) if obj.get("radius") is not None else 0.0
                width = float(obj.get("width", 0))
                height = float(obj.get("height", 0))
                cx = left + (radius if radius else width/2.0)
                cy = top + (radius if radius else height/2.0)

                L_pct = max(0.0, min(100.0, cx / cw * 100.0))
                T_pct = max(0.0, min(100.0, cy / ch * 100.0))
                # keep size
                ov_map[sel] = (L_pct, T_pct, W, H)
                _save_overview_mapping(images_dir, ov_map)
                st.success(f"📍 Saved {sel} position: left={L_pct:.1f}%, top={T_pct:.1f}%")

        # draw current with hotspots overlay (non-clickable)
        _render_overview_static(ov_path, ov_map, available, clickable=False)
        return

    # ── NORMAL MODE
    _render_overview_static(ov_path, ov_map, available, clickable=True)

def _render_overview_static(ov_path: Path, ov_map: dict, available_rooms: set, clickable: bool = True):
    # Build hotspots HTML
    hotspot_tags = []
    for rn in ROOMS:
        if rn not in available_rooms:
            continue
        L, T, W, H = ov_map.get(rn, DEFAULT_OV_HOTSPOTS.get(rn, (12,20,15,16)))
        href = f"?room={quote(rn)}" if clickable else "#"
        extra = "" if clickable else " style='pointer-events:none; opacity:.9;'"
        hotspot_tags.append(
            f"""
            <a class="hotspot" href="{href}" target="_top"
               style="left:{L}%; top:{T}%; width:{W}%; height:{H}%;"{extra}>
              <span>{rn}</span>
            </a>
            """
        )
    tags = "\n".join(hotspot_tags)

    html = f"""
    <style>
      .wrap {{
        position: relative; width: min(1280px, 96%); margin: 8px auto 10px auto;
        border-radius: 12px; border:1px solid #1f2a44; overflow:hidden;
        box-shadow: 0 24px 80px rgba(0,0,0,.35);
      }}
      .wrap img {{ display:block; width:100%; height:auto; }}
      .hotspot {{
        position:absolute; display:flex; align-items:flex-start; justify-content:flex-start;
        color:#e2e8f0; font: 700 12px/1.2 system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;
        border:2px solid rgba(34,197,94,.8); border-radius:12px; padding:4px 6px;
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
      <img src="data:image/png;base64,{_b64(ov_path)}" alt="overview"/>
      {tags}
    </div>
    """
    components.html(html, height=780, scrolling=False)

# ─────────────────────────────────────────────────────────
# ROOM VIEW
# ─────────────────────────────────────────────────────────
def render_room(images_dir: Path, room: str, simulate: bool = False, calibrate: bool = False):
    img_path = _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(room, []))
    if not img_path:
        st.error(f"❌ No image found for {room}.")
        return

    _, rm_map = _load_mappings(images_dir)
    if rm_map is None:
        rm_map = DEFAULT_ROOM_DETECTORS.copy()
    dets = rm_map.get(room, DEFAULT_ROOM_DETECTORS.get(room, []))

    colL, colR = st.columns([2, 1], gap="large")

    # ── CALIBRATION MODE (room): click-to-place detector
    if calibrate:
        if st_canvas is None:
            with colL:
                st.error("Calibration requires streamlit-drawable-canvas. Add 'streamlit-drawable-canvas==0.9.3' to requirements.txt.")
            _render_room_static(colL, img_path, dets, room, simulate, clickable=False)
        else:
            with colL:
                st.markdown("#### Room Calibration — click to set detector position")
                labels = [d["label"] for d in dets] if dets else ["NH₃"]
                sel = st.selectbox("Detector", labels, key=f"room_cal_sel_{room}")
                # Show canvas
                img = Image.open(img_path)
                cw, ch = _canvas_dims(img, max_w=1200)
                canvas = st_canvas(
                    background_image=img,
                    update_streamlit=True,
                    height=ch,
                    width=cw,
                    drawing_mode="point",
                    point_display_radius=6,
                    stroke_width=1,
                    key=f"rm_canvas_{room}",
                )
                if canvas.json_data and canvas.json_data.get("objects"):
                    obj = canvas.json_data["objects"][-1]
                    left = float(obj.get("left", 0))
                    top = float(obj.get("top", 0))
                    radius = float(obj.get("radius", 0)) if obj.get("radius") is not None else 0.0
                    width = float(obj.get("width", 0))
                    height = float(obj.get("height", 0))
                    cx = left + (radius if radius else width/2.0)
                    cy = top + (radius if radius else height/2.0)

                    x_pct = max(0.0, min(100.0, cx / cw * 100.0))
                    y_pct = max(0.0, min(100.0, cy / ch * 100.0))
                    # upsert
                    updated = False
                    for d in dets:
                        if d["label"] == sel:
                            d["x"], d["y"] = x_pct, y_pct
                            updated = True
                            break
                    if not updated:
                        dets.append({"label": sel, "x": x_pct, "y": y_pct})
                    rm_map[room] = dets
                    _save_room_mapping(images_dir, rm_map)
                    st.success(f"📍 Saved {sel}: x={x_pct:.1f}%, y={y_pct:.1f}%")

            # Also render static overlay with current detector buttons (non-clickable)
            _render_room_static(colL, img_path, dets, room, simulate, clickable=False)
            # Right column (chart/chat)
            _render_room_right(colR, room)
        return

    # ── NORMAL MODE
    _render_room_static(colL, img_path, dets, room, simulate, clickable=True)
    _render_room_right(colR, room)

def _render_room_static(colL_container, img_path: Path, dets: list, room: str, simulate: bool, clickable: bool):
    gas = dets[0]["label"] if dets else "Ethanol"
    pins_html = []
    for d in dets:
        lbl = d["label"]
        live = _next_value(room, lbl)
        rng = GAS_RANGES.get(lbl, "")
        display_val = f"{(19.5 + (live*0.05)):.1f} %" if "%" in rng else f"{live:.0f} ppm"
        x = float(d["x"]); y = float(d["y"])
        href = f"?room={quote(room)}&det={quote(lbl)}" if clickable else "#"
        extra_cls = "" if clickable else " cal"
        pins_html.append(
            f"""
            <a class="detector-btn{extra_cls}" href="{href}" target="_top" style="left:{x}%; top:{y}%;">
              <div class="lbl">{lbl}</div>
              <div class="val">{display_val}</div>
              <div class="rng">{rng}</div>
            </a>
            """
        )
    pins = "\n".join(pins_html)

    auto_start = "true" if simulate else "false"
    html = f"""
    <style>
      .wrap {{
        position: relative; width: 100%; max-width: 1200px; margin: 6px 0 10px 0;
        border:1px solid #1f2a44; border-radius:12px; overflow:hidden;
        box-shadow: 0 24px 60px rgba(0,0,0,.30);
      }}
      .wrap img {{ width:100%; height:auto; display:block; }}

      .detector-btn {{
        position:absolute; transform:translate(-50%,-50%);
        padding: 6px 10px; border: 2px solid #22c55e; border-radius: 10px;
        background: #ffffff; color: #0f172a; font-weight: 800; text-align:center;
        text-decoration:none; box-shadow: 0 0 10px rgba(34,197,94,.35); z-index: 20;
        min-width: 88px;
      }}
      .detector-btn .lbl {{ font-size: 14px; line-height: 1.1; }}
      .detector-btn .val {{ font-size: 13px; font-weight: 700; opacity:.9; }}
      .detector-btn .rng {{ font-size: 11px; opacity:.7; }}
      .detector-btn:hover {{ background:#eaffea; }}
      .detector-btn.cal {{ pointer-events: none; }}

      canvas.cloud {{
        position:absolute; left:0; top:0; width:100%; height:100%;
        pointer-events:none; z-index:15;
      }}
      .shutter {{
        position:absolute; right:0; top:0; width:24px; height:100%;
        background:rgba(15,23,42,.55);
        transform:translateX(110%); transition: transform 1.2s ease; z-index:18;
        border-left:2px solid rgba(148,163,184,.5);
      }}
      .shutter.active {{ transform:translateX(0%); }}
    </style>

    <div id="roomwrap" class="wrap">
      <img id="roomimg" src="data:image/png;base64,{_b64(img_path)}" alt="{room}"/>
      <canvas id="cloud" class="cloud"></canvas>
      <div id="shutter" class="shutter"></div>
      {pins}
    </div>

    <script>
      (function(){{
        const autoStart = {auto_start};
        const canvas = document.getElementById("cloud");
        const wrap = document.getElementById("roomwrap");
        const sh = document.getElementById("shutter");
        const ctx = canvas.getContext("2d");

        function resize() {{
          const r = wrap.getBoundingClientRect();
          canvas.width = r.width;
          canvas.height = r.height;
        }}
        resize(); window.addEventListener('resize', resize);

        let t0 = null, raf = null;
        function draw(ts) {{
          if (!t0) t0 = ts;
          const t = (ts - t0)/1000;
          ctx.clearRect(0,0,canvas.width,canvas.height);

          for (let i=0;i<24;i++) {{
            const ang = i * 0.26;
            const r = 20 + t*60 + i*8;
            const x = canvas.width*0.55 + Math.cos(ang)*r;
            const y = canvas.height*0.55 + Math.sin(ang)*r*0.62;
            const a = Math.max(0, 0.6 - i*0.02 - t*0.07);
            ctx.beginPath();
            ctx.fillStyle = "{GAS_COLOUR.get('Ethanol', '#38bdf8')}" + Math.floor(a*255).toString(16).padStart(2,'0');
            ctx.arc(x, y, 32 + i*0.8 + t*3, 0, Math.PI*2);
            ctx.fill();
          }}
          raf = requestAnimationFrame(draw);
        }}

        function start() {{
          if (raf) cancelAnimationFrame(raf);
          t0 = null;
          sh.classList.add('active');
          raf = requestAnimationFrame(draw);
          setTimeout(() => {{
            sh.classList.remove('active');
            if (raf) cancelAnimationFrame(raf);
            ctx.clearRect(0,0,canvas.width,canvas.height);
          }}, 12000);
        }}

        if (autoStart) start();
      }})();
    </script>
    """
    colL_container.components.html(html, height=720, scrolling=False)

def _render_room_right(colR_container, room: str):
    det = st.session_state.get("selected_detector")
    if det is None:
        colR_container.subheader("🤖 AI Safety Assistant")
        if p := colR_container.chat_input("Ask about leaks, thresholds or actions…"):
            colR_container.chat_message("user").write(p)
            colR_container.chat_message("ai").write("Recommendation: close shutters; increase extraction; verify detector calibrations.")
    else:
        lbl = det
        colR_container.subheader(f"📈 {lbl} — Live trend")
        series = _series(room, lbl, n=60)
        colR_container.line_chart({"reading": series})
        colR_container.caption(f"Range: {GAS_RANGES.get(lbl, '—')}")
        colR_container.divider()
        colR_container.subheader("🤖 AI Safety Assistant")
        colR_container.info(f"If {lbl} exceeds safe range, shutters will auto-close and evacuation is advised.")

# ─────────────────────────────────────────────────────────
# Settings / AI chat pages
# ─────────────────────────────────────────────────────────
def render_settings():
    st.write("Add thresholds, units, and endpoints here. (Placeholder)")
    st.write("Mappings are saved to `mapping_overview.json` and `mapping_rooms.json` at the project root.")

def render_ai_chat():
    st.chat_message("ai").write("Hi, I’m your safety AI. Ask me about leaks, thresholds, or actions.")
    if p := st.chat_input("Ask the AI Safety Assistant…"):
        st.chat_message("user").write(p)
        st.chat_message("ai").write(
            "Recommendation: close shutters in all affected rooms; increase extraction in Production areas; "
            "verify detector calibrations and evacuate if O₂ < 19.5%."
        )

        



