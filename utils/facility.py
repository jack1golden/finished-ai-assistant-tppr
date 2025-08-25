# utils/facility.py
from __future__ import annotations

import base64
from pathlib import Path
from urllib.parse import quote

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

# ---------- helpers ----------
def _b64_of(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _img64(path: Path) -> str:
    return f"data:image/{path.suffix.lstrip('.').lower()};base64,{_b64_of(path)}"

def _exists(p: Path) -> bool:
    return p.exists() and p.is_file()

# ---------- file candidates ----------
OVERVIEW_CANDS = ["Overview.png", "Overview (1).png", "overview.png"]
ROOM_FILES = {
    "Room 1": ["Room 1.png"],
    "Room 2": ["Room 2 (1).png", "Room 2.png"],
    "Room 3": ["Room 3 (1).png", "Room 3.png"],
    "Room Production": ["Room Production.png"],
    "Room Production 2": ["Room Production 2.png"],
    "Room 12 17": ["Room 12 17.png"],
}

def _find_first(images_dir: Path, names: list[str]) -> Path | None:
    for n in names:
        p = images_dir / n
        if _exists(p):
            return p
    return None

# ---------- overview hotspots (unchanged except Room 12/17 up +8%) ----------
HOTSPOTS = {
    "Room 1": dict(left=63, top=2,  width=14, height=16),
    "Room 2": dict(left=67, top=43, width=14, height=16),
    "Room 3": dict(left=60, top=19, width=14, height=16),
    "Room 12 17": dict(left=38, top=-13, width=13, height=15),  # up +8% (was -5)
    "Room Production": dict(left=24, top=28, width=23, height=21),
    "Room Production 2": dict(left=23, top=3,  width=23, height=21),
}

# ---------- detectors (with your latest moves) ----------
# Notes on % moves: “left +X%” means subtract X from x (move left), “right +X%” means add X to x.
DETECTORS = {
    "Room 1": [
        dict(label="NH₃", x=35, y=35, units="ppm"),
    ],
    "Room 2": [
        # was x=93,y=33 -> left +5%, down +5% => x=88, y=38
        dict(label="CO", x=88, y=38, units="ppm"),
    ],
    "Room 3": [
        # baseline we had x=28-25=3, y=72-25=47
        # now: up +3% (y-3) and right +2% (x+2) => x=5, y=44
        dict(label="O₂", x=5, y=44, units="%"),
    ],
    "Room 12 17": [
        # previously moved up +5% already; no new detector shift here
        dict(label="Ethanol", x=63, y=31, units="ppm"),  # (58+5, 36-5) from earlier
    ],
    "Room Production": [
        # NH3: previously x=30-8=22, now left +2% => x=20
        dict(label="NH₃", x=20, y=28, units="ppm"),
        # O2: previously x=78+10=88, y=72-30=42, now up +2% => y=40
        dict(label="O₂", x=88, y=40, units="%"),
    ],
    "Room Production 2": [
        # O2: previously x=70+5=75, now right +3% => 78
        dict(label="O₂", x=78, y=45, units="%"),
        # H2S: previously x=70-50=20, y=65-30=35 → left +2% => 18; up +4% => 31
        dict(label="H₂S", x=18, y=31, units="ppm"),
    ],
}

# ---------- live series sim ----------
def _sim_key(room: str, label: str) -> str:
    return f"{room}::{label}"

def _next_value(room: str, label: str) -> float:
    key = _sim_key(room, label)
    state = st.session_state.setdefault("det_sim", {})
    v = state.get(key, 10.0)
    v += float(np.random.uniform(-0.5, 0.9))
    v = max(0.0, v)
    state[key] = v
    return v

def _series(room: str, label: str, n: int = 90):
    key = _sim_key(room, label)
    buf = st.session_state.setdefault("det_buf", {}).setdefault(key, [])
    buf.append(_next_value(room, label))
    if len(buf) > n:
        buf[:] = buf[-n:]
    return buf

# ======================================================
# Overview
# ======================================================
def render_overview(images_dir: Path):
    ov_path = _find_first(images_dir, OVERVIEW_CANDS)
    if not ov_path:
        st.error("Overview image not found in /images.")
        return

    hotspots_html = []
    for room, box in HOTSPOTS.items():
        # fallback href; onclick forces parent navigation (works in Streamlit Cloud iframe)
        href = f"?room={quote(room)}"
        hotspots_html.append(
            f"""
            <a class="hotspot" data-room="{room}" href="{href}" target="_top"
               onclick="
                 try {{
                   const base = window.top.location.pathname;
                   window.top.location.href = base + '?room=' + encodeURIComponent('{room}');
                 }} catch(e) {{
                   window.location.search = 'room=' + encodeURIComponent('{room}');
                 }}
                 return false;"
               style="left:{box['left']}%;top:{box['top']}%;width:{box['width']}%;height:{box['height']}%;">
              <span>{room}</span>
            </a>
            """
        )
    tags = "\n".join(hotspots_html)

    html = f"""
    <style>
      .wrap {{
        position:relative; width:min(1280px,96%); margin:8px auto;
        border:1px solid #1f2a44; border-radius:12px; overflow:hidden;
        box-shadow:0 18px 60px rgba(0,0,0,.35);
      }}
      .wrap img {{ display:block; width:100%; height:auto; }}
      .hotspot {{
        position:absolute; border:2px solid rgba(34,197,94,.9); border-radius:10px;
        background:rgba(16,185,129,.18); color:#e2e8f0; font-weight:800; font-size:12px;
        display:flex; align-items:flex-start; justify-content:flex-start; padding:4px 6px; z-index:20;
        text-decoration:none;
      }}
      .hotspot:hover {{ background:rgba(16,185,129,.28); }}
      .hotspot span {{
        background:rgba(2,6,23,.55); border:1px solid rgba(103,232,249,.5); padding:2px 6px; border-radius:8px;
      }}
    </style>
    <div class="wrap">
      <img src="{_img64(ov_path)}" alt="overview"/>
      {tags}
    </div>
    """
    components.html(html, height=780, scrolling=False)

# ======================================================
# Room
# ======================================================
def render_room(images_dir: Path, room: str, simulate: bool = False, selected_detector: str | None = None):
    room_path = _find_first(images_dir, ROOM_FILES.get(room, []))
    if not room_path:
        st.error(f"No image found for {room} in /images.")
        return

    dets = DETECTORS.get(room, [])

    colL, colR = st.columns([2, 1], gap="large")

    # LEFT: image + detector buttons + gas cloud + shutter
    pins_html = []
    for d in dets:
        lbl = d["label"]
        href = f"?room={quote(room)}&det={quote(lbl)}"
        pins_html.append(
            f"""
            <a class="detector" href="{href}" target="_top"
               onclick="
                 try {{
                   const base = window.top.location.pathname;
                   window.top.location.href = base + '?room=' + encodeURIComponent('{room}') + '&det=' + encodeURIComponent('{lbl}');
                 }} catch(e) {{
                   window.location.search = 'room={room}&det={lbl}';
                 }}
                 return false;"
               style="left:{d['x']}%;top:{d['y']}%;">
              <div class="lbl">{lbl}</div>
            </a>
            """
        )
    pins = "\n".join(pins_html)

    auto_start = "true" if simulate else "false"
    cloud_color = "#38bdf8"  # cyan-ish; could color by gas if we want per-detector later

    room_html = f"""
    <style>
      .roomwrap {{
        position:relative; width:100%; max-width:1200px; margin:6px 0;
        border:1px solid #1f2a44; border-radius:12px; overflow:hidden;
        box-shadow:0 18px 60px rgba(0,0,0,.30);
      }}
      .roomwrap img {{ display:block; width:100%; height:auto; }}

      .detector {{
        position:absolute; transform:translate(-50%,-50%);
        border:2px solid #22c55e; border-radius:10px; background:#fff;
        padding:6px 10px; min-width:72px; text-align:center; z-index:20;
        box-shadow:0 0 10px rgba(34,197,94,.35); font-weight:800; color:#0f172a; text-decoration:none;
      }}
      .detector:hover {{ background:#eaffea; }}
      .detector .lbl {{ font-size:14px; line-height:1.1; }}

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

    <div id="roomwrap" class="roomwrap">
      <img id="roomimg" src="{_img64(room_path)}" alt="{room}"/>
      <canvas id="cloud" class="cloud"></canvas>
      <div id="shutter" class="shutter"></div>
      {pins}
    </div>

    <script>
      (function(){{
        const simulate = {auto_start};
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
        function hexToRGBA(hex, a) {{
          const c = hex.replace('#','');
          const r = parseInt(c.substring(0,2),16);
          const g = parseInt(c.substring(2,4),16);
          const b = parseInt(c.substring(4,6),16);
          return `rgba(${r},${g},${b},${a})`;
        }}

        function draw(ts) {{
          if (!t0) t0 = ts;
          const t = (ts - t0)/1000;
          ctx.clearRect(0,0,canvas.width,canvas.height);

          for (let i=0;i<28;i++) {{
            const ang = i * 0.25;
            const r = 20 + t*60 + i*8;
            const x = canvas.width*0.55 + Math.cos(ang)*r;
            const y = canvas.height*0.55 + Math.sin(ang)*r*0.62;
            const a = Math.max(0, 0.55 - i*0.02 - t*0.07);
            ctx.beginPath();
            ctx.fillStyle = hexToRGBA("{cloud_color}", a);
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

        if (simulate) start();
      }})();
    </script>
    """
    with colL:
        components.html(room_html, height=720, scrolling=False)

    # RIGHT: chart + AI
    with colR:
        if selected_detector:
            st.subheader(f"📈 {selected_detector} — Live trend")
            series = _series(room, selected_detector, n=90)
            st.line_chart({"reading": series})
            # light auto-refresh so the line moves during your pitch
            st.experimental_set_query_params(room=room, det=selected_detector)
        else:
            st.info("Click a detector badge on the image to view its live trend.")
        st.divider()
        st.subheader("🤖 AI Safety Assistant")
        if p := st.chat_input("Ask about leaks, thresholds or actions…"):
            st.chat_message("user").write(p)
            st.chat_message("ai").write(
                "Recommendation: close shutters; increase extraction; verify detector calibrations; "
                "evacuate if O₂ < 19.5%."
            )

# ---------- simple pages ----------
def render_settings():
    st.write("Thresholds, units, and integrations will live here.")
    st.write("To adjust placements, edit HOTSPOTS and DETECTORS in utils/facility.py.")

def render_ai_chat():
    st.chat_message("ai").write("Hi, I’m your safety AI. Ask me about leaks, thresholds, or actions.")
    if p := st.chat_input("Ask the AI Safety Assistant…"):
        st.chat_message("user").write(p)
        st.chat_message("ai").write(
            "Recommendation: close shutters in all affected rooms; increase extraction in Production areas; "
            "verify detector calibrations and evacuate if O₂ < 19.5%."
        )








        



