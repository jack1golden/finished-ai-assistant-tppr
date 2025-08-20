import json
import base64
import random
from pathlib import Path
from urllib.parse import quote, unquote

import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────────────────
# Static config
# ─────────────────────────────────────────────────────────
ROOMS = [
    "Room 1", "Room 2", "Room 3",
    "Room 12 17", "Room Production", "Room Production 2",
]

# Preferred filenames for each room image (checks in order)
ROOM_FILE_CANDIDATES = {
    "Room 1": ["Room 1.png"],
    "Room 2": ["Room 2 (1).png", "Room 2.png"],
    "Room 3": ["Room 3 (1).png", "Room 3.png"],
    "Room 12 17": ["Room 12 17.png", "Room 12.png", "Room 17.png"],
    "Room Production": ["Room Production.png"],
    "Room Production 2": ["Room Production 2.png", "Room Production2.png"],
}
OVERVIEW_CANDIDATES = ["Overview.png", "Overview (1).png", "overview.png"]

# Hardcoded ranges by gas label
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
    # Store mappings at project root for persistence
    root = base_dir.parent
    return root / "mapping_overview.json", root / "mapping_rooms.json"

def _load_mappings(images_dir: Path):
    ov_path, rm_path = _mapping_paths(images_dir)
    ov = None
    rm = None
    if ov_path.exists():
        ov = json.loads(ov_path.read_text())
    if rm_path.exists():
        rm = json.loads(rm_path.read_text())
    return ov, rm

def _save_overview_mapping(images_dir: Path, mapping: dict):
    ov_path, _ = _mapping_paths(images_dir)
    ov_path.write_text(json.dumps(mapping, indent=2))

def _save_room_mapping(images_dir: Path, mapping: dict):
    _, rm_path = _mapping_paths(images_dir)
    rm_path.write_text(json.dumps(mapping, indent=2))

# ─────────────────────────────────────────────────────────
# Defaults (used if no mapping_* JSON present)
# Hotspots: left, top, width, height (percent)
# Detectors: per room => list of {label, x, y}
# ─────────────────────────────────────────────────────────
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
# Live reading simulator (per detector)
# ─────────────────────────────────────────────────────────
def _sim_key(room: str, label: str) -> str:
    return f"{room}::{label}"

def _next_value(room: str, label: str) -> float:
    key = _sim_key(room, label)
    state = st.session_state.setdefault("det_sim", {})
    v = state.get(key, random.uniform(0.0, 1.0) * 10.0)
    # gentle random walk with clamping
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
# Logo / Home
# ─────────────────────────────────────────────────────────
def render_logo(images_dir: Path):
    user_logo = images_dir / "logo.png"
    if user_logo.exists():
        st.image(str(user_logo), use_container_width=True)
        return
    # Minimal fallback
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
# Facility Overview (hotspots over image) + calibration
# ─────────────────────────────────────────────────────────
def render_overview(images_dir: Path, calibrate: bool = False, cal_room: str = "Room 1"):
    ov = _first_existing(images_dir, OVERVIEW_CANDIDATES)
    if not ov:
        st.error("Overview image not found. Put 'Overview.png' (or 'Overview (1).png') in images/.")
        return

    ov_map, _ = _load_mappings(images_dir)
    if ov_map is None:
        ov_map = DEFAULT_OV_HOTSPOTS.copy()

    # Which rooms have images
    available = set(r for r in ROOMS if _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(r, [])))

    # Handle calibration click (?ov_set=1&room=...&L=..&T=..)
    qp = st.query_params
    if calibrate and all(k in qp for k in ("ov_set", "room", "L", "T")):
        try:
            L = float(qp["L"]); T = float(qp["T"])
            rname = qp["room"]  # already encoded by JS; Streamlit decodes automatically
            # preserve existing W/H
            W, H = ov_map.get(rname, DEFAULT_OV_HOTSPOTS.get(rname, (12,20,15,16)))[2:]
            ov_map[rname] = (max(0,min(100,L)), max(0,min(100,T)), W, H)
            _save_overview_mapping(images_dir, ov_map)
            st.query_params.clear()
            st.rerun()
        except Exception:
            pass

    # Optional size adjust UI
    if calibrate:
        room_list = list(ROOMS)
        st.markdown("#### Overview Calibration")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            sel = st.selectbox("Room", room_list, index=room_list.index(cal_room) if cal_room in room_list else 0, key="ov_sel_room")
        with c2:
            cur = ov_map.get(sel, DEFAULT_OV_HOTSPOTS.get(sel, (12,20,15,16)))
            L, T, W, H = cur
            W = c2.slider("Width (%)", 5.0, 40.0, float(W), 0.5, key="ov_w_slider")
        with c3:
            H = c3.slider("Height (%)", 5.0, 40.0, float(H), 0.5, key="ov_h_slider")
        with c4:
            if st.button("💾 Save box size", key="ov_save_wh"):
                ov_map[sel] = (L, T, W, H)
                _save_overview_mapping(images_dir, ov_map)
                st.success(f"Saved size for {sel}: W={W:.1f}%, H={H:.1f}%")

    # Build hotspots HTML (disable pointer-events when calibrating so clicks pass through)
    hotspot_tags = []
    for rn in ROOMS:
        if rn not in available:
            continue
        L, T, W, H = ov_map.get(rn, DEFAULT_OV_HOTSPOTS.get(rn, (12,20,15,16)))
        href = f"?room={quote(rn)}"
        hotspot_tags.append(
            f"""
            <a class="hotspot {'cal' if calibrate else ''}" href="{href}" target="_top"
               style="left:{L}%; top:{T}%; width:{W}%; height:{H}%;">
              <span>{rn}</span>
            </a>
            """
        )
    tags = "\n".join(hotspot_tags)

    # Click-capture overlay for calibration
    click_overlay = ""
    if calibrate:
        # Use JSON string to avoid double-encoding; encode in JS.
        room_js = json.dumps(cal_room)
        click_overlay = f"""
        <div id="ov_click" class="clickcatch" title="Click to set the top/left of {cal_room}"></div>
        <script>
          (function(){{
            const cc = document.getElementById('ov_click');
            cc.addEventListener('click', function(ev){{
              const r = cc.getBoundingClientRect();
              const L = (ev.clientX - r.left) / r.width * 100.0;
              const T = (ev.clientY - r.top) / r.height * 100.0;
              const room = encodeURIComponent({room_js});
              const qs = "?ov_set=1&room=" + room + "&L=" + L.toFixed(2) + "&T=" + T.toFixed(2);
              try {{ window.parent.location.search = qs; }} catch(e) {{ window.top.location.search = qs; }}
            }});
          }})();
        </script>
        """

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
      .hotspot.cal {{ pointer-events: none; }}  /* allow clicks to pass to overlay while calibrating */

      .clickcatch {{
        position:absolute; left:0; top:0; right:0; bottom:0; z-index: 9999;
        background: rgba(0,0,0,0); cursor: crosshair;
      }}
    </style>
    <div class="wrap" id="wrap">
      <img src="data:image/png;base64,{_b64(ov)}" alt="overview"/>
      {tags}
      {click_overlay}
    </div>
    """
    components.html(html, height=780, scrolling=False)

# ─────────────────────────────────────────────────────────
# Room view (detector buttons on image) + calibration + gas cloud
# ─────────────────────────────────────────────────────────
def render_room(images_dir: Path, room: str, simulate: bool = False, calibrate: bool = False):
    img_path = _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(room, []))
    if not img_path:
        st.error(f"❌ No image found for {room}.")
        return

    # Load mappings
    _, rm_map = _load_mappings(images_dir)
    if rm_map is None:
        rm_map = DEFAULT_ROOM_DETECTORS.copy()

    dets = rm_map.get(room, DEFAULT_ROOM_DETECTORS.get(room, []))

    # Handle calibration click (?rm_set=1&room=...&dlabel=...&x=..&y=..)
    qp = st.query_params
    if calibrate and all(k in qp for k in ("rm_set", "room", "dlabel", "x", "y")):
        try:
            rx = float(qp["x"]); ry = float(qp["y"])
            rname = qp["room"]
            dlabel = qp["dlabel"]
            # upsert detector
            updated = False
            cur_dets = rm_map.get(rname, [])
            for d in cur_dets:
                if d["label"] == dlabel:
                    d["x"], d["y"] = rx, ry
                    updated = True
                    break
            if not updated:
                cur_dets.append({"label": dlabel, "x": rx, "y": ry})
            rm_map[rname] = cur_dets
            _save_room_mapping(images_dir, rm_map)
            st.query_params.clear()
            st.rerun()
        except Exception:
            pass

    colL, colR = st.columns([2, 1], gap="large")

    # LEFT: image + detector buttons
    with colL:
        gas = dets[0]["label"] if dets else "Ethanol"
        colour = GAS_COLOUR.get(gas, "#38bdf8")

        # Build detector buttons
        pins_html = []
        for d in dets:
            lbl = d["label"]
            live = _next_value(room, lbl)
            rng = GAS_RANGES.get(lbl, "")
            # percent vs ppm display
            if "%" in rng:
                display_val = f"{(19.5 + (live*0.05)):.1f} %"
            else:
                display_val = f"{live:.0f} ppm"

            x = float(d["x"]); y = float(d["y"])
            href = f"?room={quote(room)}&det={quote(lbl)}"
            # disable pointer-events in calibration so overlay can capture
            cls = "detector-btn cal" if calibrate else "detector-btn"
            pins_html.append(
                f"""
                <a class="{cls}" href="{href}" target="_top" style="left:{x}%; top:{y}%;">
                  <div class="lbl">{lbl}</div>
                  <div class="val">{display_val}</div>
                  <div class="rng">{rng}</div>
                </a>
                """
            )
        pins = "\n".join(pins_html)

        # Calibration overlay for room (choose detector in sidebar expander)
        click_js = ""
        if calibrate:
            # choose detector label to move
            default_lbl = dets[0]["label"] if dets else "NH₃"
            cur_lbl = st.session_state.get("cal_room_detector", default_lbl)
            with st.expander("⚙ Positioning (this room)", expanded=False):
                labels_here = [d["label"] for d in dets] if dets else [default_lbl]
                cur_lbl = st.selectbox("Detector to place", labels_here, index=0 if default_lbl not in labels_here else labels_here.index(default_lbl), key=f"sel_det_{room}")
                st.session_state["cal_room_detector"] = cur_lbl
                st.caption("Click on the image to set the pin. (Pins are disabled while calibrating)")

            room_js = json.dumps(room)
            dlabel_js = json.dumps(cur_lbl)
            click_js = f"""
            <div id="rm_click" class="clickcatch" title="Click to set {cur_lbl}">
            </div>
            <script>
              (function(){{
                const cc = document.getElementById('rm_click');
                cc.addEventListener('click', function(ev){{
                  const r = cc.getBoundingClientRect();
                  const x = (ev.clientX - r.left) / r.width * 100.0;
                  const y = (ev.clientY - r.top) / r.height * 100.0;
                  const room = encodeURIComponent({room_js});
                  const dlabel = encodeURIComponent({dlabel_js});
                  const qs = "?rm_set=1&room=" + room + "&dlabel=" + dlabel + "&x=" + x.toFixed(2) + "&y=" + y.toFixed(2);
                  try {{ window.parent.location.search = qs; }} catch(e) {{ window.top.location.search = qs; }}
                }});
              }})();
            </script>
            """

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
          .detector-btn.cal {{ pointer-events: none; }}  /* disable during calibration */

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

          .clickcatch {{
            position:absolute; left:0; top:0; right:0; bottom:0; z-index: 9999;
            background: rgba(0,0,0,0); cursor: crosshair;
          }}
        </style>

        <div id="roomwrap" class="wrap">
          <img id="roomimg" src="data:image/png;base64,{_b64(img_path)}" alt="{room}"/>
          <canvas id="cloud" class="cloud"></canvas>
          <div id="shutter" class="shutter"></div>
          {pins}
          {click_js}
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
        components.html(html, height=720, scrolling=False)

    # RIGHT: live chart + AI chat
    with colR:
        det = st.session_state.get("selected_detector")
        if det is None:
            st.subheader("🤖 AI Safety Assistant")
            if p := st.chat_input("Ask about leaks, thresholds or actions…"):
                st.chat_message("user").write(p)
                st.chat_message("ai").write("Recommendation: close shutters; increase extraction; verify detector calibrations.")
        else:
            lbl = det
            st.subheader(f"📈 {lbl} — Live trend")
            series = _series(room, lbl, n=60)
            st.line_chart({"reading": series})
            st.caption(f"Range: {GAS_RANGES.get(lbl, '—')}")

            st.divider()
            st.subheader("🤖 AI Safety Assistant")
            st.info(f"If {lbl} exceeds safe range, shutters will auto-close and evacuation is advised.")

    # Reflect detector selection (?det=...)
    qp = st.query_params
    if "det" in qp:
        st.session_state["selected_detector"] = unquote(qp["det"])

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



