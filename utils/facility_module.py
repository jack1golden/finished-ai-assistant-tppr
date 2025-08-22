# utils/facility_module.py
from __future__ import annotations

import base64
import random
from pathlib import Path
from urllib.parse import quote

import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────
# Image helpers
# ─────────────────────────────────────────────
def _b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _first(images_dir: Path, names: list[str]) -> Path | None:
    for n in names:
        p = images_dir / n
        if p.exists():
            return p
    return None

# ─────────────────────────────────────────────
# Assets / filenames
# ─────────────────────────────────────────────
OVERVIEW_CANDIDATES = ["Overview.png", "Overview (1).png", "overview.png"]

ROOM_FILE_CANDIDATES = {
    "Room 1": ["Room 1.png"],
    "Room 2": ["Room 2 (1).png", "Room 2.png"],
    "Room 3": ["Room 3 (1).png", "Room 3.png"],
    "Room 12 17": ["Room 12 17.png", "Room 12.png"],
    "Room Production": ["Room Production.png"],
    "Room Production 2": ["Room Production 2.png", "Room Production2.png"],
}

# ─────────────────────────────────────────────
# HARD-CODED HOTSPOTS (percent) — tune if needed
# ─────────────────────────────────────────────
HOTSPOTS = {
    "Room 1":        (12, 22, 14, 16),
    "Room 2":        (31, 23, 14, 16),
    "Room 3":        (50, 24, 14, 16),
    "Room 12 17":    (69, 25, 14, 16),
    "Room Production":   (24, 55, 24, 22),
    "Room Production 2": (54, 56, 24, 22),
}

# ─────────────────────────────────────────────
# Detector mapping (percent)
# ─────────────────────────────────────────────
GAS_RANGES = {
    "NH₃": "0–50 ppm",
    "CO": "0–200 ppm",
    "O₂": "19–23 %",
    "CH₄": "0–100 %LEL",
    "H₂S": "0–100 ppm",
    "Ethanol": "0–1000 ppm",
}

DETECTORS = {
    "Room 1": [{"label": "NH₃", "x": 35.0, "y": 35.0}],
    "Room 2": [{"label": "CO",  "x": 93.0, "y": 33.0}],  # right wall above doorway
    "Room 3": [{"label": "O₂",  "x": 28.0, "y": 72.0}],
    "Room 12 17": [{"label": "Ethanol", "x": 58.0, "y": 36.0}],
    "Room Production": [
        {"label": "O₂",  "x": 78.0, "y": 72.0},
        {"label": "CH₄", "x": 30.0, "y": 28.0},
    ],
    "Room Production 2": [
        {"label": "O₂",  "x": 70.0, "y": 45.0},
        {"label": "H₂S", "x": 70.0, "y": 65.0},
    ],
}

GAS_COLOUR = {
    "NH₃": "#38bdf8", "CO": "#f97316", "O₂": "#22c55e", "H₂": "#a855f7",
    "CH₄": "#f59e0b", "Ethanol": "#ef4444", "CO₂": "#06b6d4", "H₂S": "#eab308",
}

# ─────────────────────────────────────────────
# Live-value simulator (per detector)
# ─────────────────────────────────────────────
def _sim_key(room: str, label: str) -> str:
    return f"{room}::{label}"

def _next_value(room: str, label: str) -> float:
    key = _sim_key(room, label)
    state = st.session_state.setdefault("det_sim", {})
    v = state.get(key, random.uniform(0.0, 1.0) * 10.0)
    v += random.uniform(-0.5, 0.9)
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

# ─────────────────────────────────────────────
# Logo / Home
# ─────────────────────────────────────────────
def render_logo(images_dir: Path):
    custom = images_dir / "logo.png"
    if custom.exists():
        st.image(str(custom), use_container_width=True)
        return
    # minimal fallback
    W, H = 900, 240
    img = Image.new("RGB", (W, H), (17, 24, 39))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((30, 60, 200, 210), 20, outline=(80, 200, 255), width=5)
    try:
        fnt = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
    except Exception:
        fnt = None
    d.text((250, 95), "Pharma Safety HMI — AI First", fill=(210, 230, 255), font=fnt)
    st.image(img, use_container_width=True)

# ─────────────────────────────────────────────
# Overview (hotspots over image)
# ─────────────────────────────────────────────
def render_overview(images_dir: Path):
    ov = _first(images_dir, OVERVIEW_CANDIDATES)
    if not ov:
        st.error("Overview image not found. Add **images/Overview.png**.")
        return

    # Only include rooms that have images
    available = {r for r in HOTSPOTS.keys() if _first(images_dir, ROOM_FILE_CANDIDATES.get(r, []))}

    # Build hotspots HTML
    hotspot_tags = []
    for rn in HOTSPOTS.keys():
        if rn not in available:
            continue
        L, T, W, H = HOTSPOTS[rn]
        href = f"?room={quote(rn)}"
        hotspot_tags.append(
            f"""
            <a class="hotspot" href="{href}" target="_top"
               style="left:{L}%; top:{T}%; width:{W}%; height:{H}%;">
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
        border:2px solid rgba(34,197,94,.9); border-radius:12px; padding:4px 6px;
        text-decoration:none; background: rgba(13, 25, 40, .18); z-index: 20;
      }}
      .hotspot span {{
        background: rgba(15,23,42,.65); padding: 2px 6px; border-radius: 8px;
        border:1px solid rgba(103,232,249,.5);
      }}
      .hotspot:hover {{ background: rgba(13, 25, 40, .26); }}
    </style>
    <div class="wrap">
      <img src="data:image/png;base64,{_b64(ov)}" alt="overview"/>
      {tags}
    </div>
    """
    components.html(html, height=780, scrolling=False)

# ─────────────────────────────────────────────
# Room view (image + detector buttons + gas cloud + shutters)
# ─────────────────────────────────────────────
def render_room(images_dir: Path, room: str, simulate: bool, selected_detector: str | None):
    img_path = _first(images_dir, ROOM_FILE_CANDIDATES.get(room, []))
    if not img_path:
        st.error(f"No image found for **{room}** in images/.")
        return

    dets = DETECTORS.get(room, [])

    colL, colR = st.columns([2, 1], gap="large")

    with colL:
        # Build detector pins
        pins_html = []
        for d in dets:
            lbl = d["label"]
            rng = GAS_RANGES.get(lbl, "")
            v = _next_value(room, lbl)
            val = f"{(19.5 + (v*0.05)):.1f} %" if "%" in rng else f"{v:.0f} ppm"
            href = f"?room={quote(room)}&det={quote(lbl)}"
            pins_html.append(
                f"""
                <a class="detector-btn" href="{href}" target="_top" style="left:{d['x']}%; top:{d['y']}%;">
                  <div class="lbl">{lbl}</div>
                  <div class="val">{val}</div>
                  <div class="rng">{rng}</div>
                </a>
                """
            )
        pins = "\n".join(pins_html)

        auto_start = "true" if simulate else "false"
        gas = dets[0]["label"] if dets else "Ethanol"
        colour = GAS_COLOUR.get(gas, "#38bdf8")

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
                ctx.fillStyle = "{colour}" + Math.floor(a*255).toString(16).padStart(2,'0');
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

    with colR:
        det = selected_detector
        if not det:
            st.subheader("🤖 AI Safety Assistant")
            if p := st.chat_input("Ask about leaks, thresholds or actions…"):
                st.chat_message("user").write(p)
                st.chat_message("ai").write(
                    "Recommendation: close shutters; increase extraction; verify detector calibrations; "
                    "evacuate if O₂ < 19.5%."
                )
        else:
            st.subheader(f"📈 {det} — Live trend")
            series = _series(room, det, n=90)
            st.line_chart({"reading": series})
            st.caption(f"Range: {GAS_RANGES.get(det, '—')}")

            st.divider()
            st.subheader("🤖 AI Safety Assistant")
            st.info(f"If {det} exceeds safe range, shutters will auto-close and evacuation is advised.")

# ─────────────────────────────────────────────
# Settings / AI pages
# ─────────────────────────────────────────────
def render_settings():
    st.write("Add thresholds, units, and endpoints here. (Placeholder)")
    st.write("All positions are hardcoded in this file (HOTSPOTS and DETECTORS).")

def render_ai_chat():
    st.chat_message("ai").write("Hi, I’m your safety AI. Ask me about leaks, thresholds, or actions.")
    if p := st.chat_input("Ask the AI Safety Assistant…"):
        st.chat_message("user").write(p)
        st.chat_message("ai").write(
            "Recommendation: close shutters in all affected rooms; increase extraction in Production areas; "
            "verify detector calibrations and evacuate if O₂ < 19.5%."
        )




        



