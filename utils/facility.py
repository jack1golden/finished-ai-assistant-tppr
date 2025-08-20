import base64
from pathlib import Path
from urllib.parse import quote, unquote

import streamlit as st
import streamlit.components.v1 as components

# =========================
# Helpers
# =========================
def _b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _first_existing(images_dir: Path, candidates: list[str]) -> Path | None:
    for name in candidates:
        p = images_dir / name
        if p.exists():
            return p
    return None

# =========================
# Files & Rooms
# =========================
ROOMS = [
    "Room 1",
    "Room 2",
    "Room 3",
    "Room 12 17",
    "Room Production",
    "Room Production 2",
]

OVERVIEW_CANDIDATES = ["Overview.png", "Overview (1).png", "overview.png"]

ROOM_FILE_CANDIDATES = {
    "Room 1": ["Room 1.png"],
    "Room 2": ["Room 2.png", "Room 2 (1).png"],
    "Room 3": ["Room 3.png", "Room 3 (1).png"],
    "Room 12 17": ["Room 12 17.png", "Room 12.png", "Room 17.png"],
    "Room Production": ["Room Production.png"],
    "Room Production 2": ["Room Production 2.png", "Room Production2.png"],
}

# =========================
# Overview Hotspots — tune (left, top, width, height) in %
# =========================
OVERVIEW_HOTSPOTS = {
    "Room 1":            (12, 20, 15, 16),
    "Room 2":            (32, 20, 15, 16),
    "Room 3":            (52, 20, 15, 16),
    "Room 12 17":        (72, 20, 15, 16),
    "Room Production":   (24, 52, 24, 22),
    "Room Production 2": (54, 52, 24, 22),
}

# =========================
# Detector pins (x,y in % of the room image)
# =========================
DETECTOR_MAP = {
    "Room 1":            [{"label": "NH₃",     "x": 35.0, "y": 35.0}],
    "Room 2":            [{"label": "CO",      "x": 52.0, "y": 50.0}],
    "Room 3":            [{"label": "O₂",      "x": 28.0, "y": 72.0}],
    "Room 12 17":        [{"label": "Ethanol", "x": 58.0, "y": 36.0}],
    "Room Production":   [{"label": "NH₃",     "x": 30.0, "y": 28.0},
                          {"label": "O₂",      "x": 78.0, "y": 72.0}],
    "Room Production 2": [{"label": "O₂",      "x": 70.0, "y": 45.0},
                          {"label": "H₂",      "x": 70.0, "y": 65.0}],
}

# Gas colour per label
GAS_COLOUR = {
    "NH₃": "#38bdf8",     # cyan-ish
    "CO":  "#f97316",     # amber
    "O₂":  "#22c55e",     # green
    "H₂":  "#a855f7",     # purple
    "CH₄": "#f59e0b",
    "Ethanol": "#ef4444",
}

def rooms_available(images_dir: Path) -> list[str]:
    out = []
    for rn in ROOMS:
        if _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(rn, [])):
            out.append(rn)
    return out

# =========================
# Overview with hotspots
# =========================
def render_overview(images_dir: Path):
    ov = _first_existing(images_dir, OVERVIEW_CANDIDATES)
    if not ov:
        st.error("Overview image not found. Put 'Overview.png' (or 'Overview (1).png') in images/.")
        return

    b64 = _b64(ov)
    hotspots_html = []
    for rn in ROOMS:
        if rn not in OVERVIEW_HOTSPOTS:
            continue
        if rn not in rooms_available(images_dir):
            continue
        L, T, W, H = OVERVIEW_HOTSPOTS[rn]
        href = f"?room={quote(rn)}"
        hotspots_html.append(
            f"""
            <a class="hotspot" href="{href}" target="_top"
               style="left:{L}%; top:{T}%; width:{W}%; height:{H}%;">
              <span>{rn}</span>
            </a>
            """
        )

    hotspots = "\n".join(hotspots_html)
    html = f"""
    <style>
      .wrap {{
        position: relative; width: min(1280px, 96%); margin: 4px auto 10px auto;
        border-radius: 12px; border:1px solid #1f2a44; overflow:hidden;
        box-shadow: 0 24px 80px rgba(0,0,0,.35);
      }}
      .wrap img {{ display:block; width:100%; height:auto; }}
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

# =========================
# Room with detector pins + optional gas animation
# =========================
def render_room(images_dir: Path, room: str, simulate: bool = False):
    img_path = _first_existing(images_dir, ROOM_FILE_CANDIDATES.get(room, []))
    if not img_path:
        st.error(f"❌ No image found for {room}.")
        return

    dets = DETECTOR_MAP.get(room, [])
    b64 = _b64(img_path)

    # Pick a gas colour (use first detector’s label if present)
    gas = dets[0]["label"] if dets else "Ethanol"
    cloud_color = GAS_COLOUR.get(gas, "#38bdf8")
    auto_start = "true" if simulate else "false"

    # Build detector pins
    pins_html = []
    for d in dets:
        x = float(d["x"]); y = float(d["y"]); label = d["label"]
        href = f"?room={quote(room)}&det={quote(label)}"
        pins_html.append(
            f"""<a class="pin" href="{href}" target="_top" style="left:{x}%; top:{y}%;">{label}</a>"""
        )
    pins = "\n".join(pins_html)

    # HTML + JS for gas cloud animation
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
        z-index: 20;
      }}
      .pin:hover {{ filter: brightness(0.95); }}
      canvas.cloud {{
        position:absolute; left:0; top:0; width:100%; height:100%; pointer-events:none; z-index:15;
      }}
      .shutter {{
        position:absolute; right:0; top:0; width:24px; height:100%; background:rgba(15,23,42,.55);
        transform:translateX(110%); transition: transform 1.2s ease; z-index:18; border-left:2px solid rgba(148,163,184,.5);
      }}
      .shutter.active {{ transform:translateX(0%); }}
    </style>

    <div id="roomwrap" class="wrap">
      <img id="roomimg" src="data:image/png;base64,{b64}" alt="{room}"/>
      <canvas id="cloud" class="cloud"></canvas>
      <div id="shutter" class="shutter"></div>
      {pins}
    </div>

    <script>
      (function() {{
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

          // smoke puffs
          for (let i=0;i<24;i++) {{
            const ang = i * 0.26;
            const r = 20 + t*60 + i*8;
            const x = canvas.width*0.55 + Math.cos(ang)*r;
            const y = canvas.height*0.55 + Math.sin(ang)*r*0.62;
            const alpha = Math.max(0, 0.6 - i*0.02 - t*0.07);
            ctx.beginPath();
            ctx.fillStyle = "{cloud_color}" + Math.floor(alpha*255).toString(16).padStart(2,'0');
            ctx.arc(x, y, 32 + i*0.8 + t*3, 0, Math.PI*2);
            ctx.fill();
          }}
          raf = requestAnimationFrame(draw);
        }}

        function start() {{
          if (raf) cancelAnimationFrame(raf);
          t0 = null;
          sh.classList.add('active');   // close shutter
          raf = requestAnimationFrame(draw);
          // fade out after 12s
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

    # Handle detector selection from query (?det=...)
    qp = st.query_params
    if "det" in qp:
        st.session_state["current_detector"] = unquote(qp["det"])

