# utils/facility.py
from __future__ import annotations
import base64, time
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import altair as alt

from . import history

# ---------- helpers ----------
def _b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
def _img64(path: Path) -> str:
    ext = path.suffix.lstrip(".").lower()
    return f"data:image/{ext};base64,{_b64(path)}"
def _exists(p: Path) -> bool:
    return p.exists() and p.is_file()
def ts_str(ts: int) -> str:
    return pd.to_datetime(ts, unit="s").strftime("%Y-%m-%d %H:%M:%S")
def get_detectors_for(room: str):
    return DETECTORS.get(room, [])

# ---------- image files ----------
OVERVIEW_CANDS = ["Overview.png", "Overview (1).png", "overview.png"]
ROOM_FILES = {
    "Room 1": ["Room 1.png"],
    "Room 2": ["Room 2 (1).png", "Room 2.png"],
    "Room 3": ["Room 3 (1).png", "Room 3.png"],
    "Room 12 17": ["Room 12 17.png"],
    "Room Production": ["Room Production.png"],
    "Room Production 2": ["Room Production 2.png"],
}
def _find(images_dir: Path, cand: list[str]) -> Path | None:
    for n in cand:
        p = images_dir / n
        if _exists(p): return p
    return None

# ---------- hotspots (visual only) ----------
HOTSPOTS = {
    "Room 1":            dict(left=63, top=2,   width=14, height=16),
    "Room 2":            dict(left=67, top=43,  width=14, height=16),
    "Room 3":            dict(left=60, top=19,  width=14, height=16),
    "Room 12 17":        dict(left=38, top=-13, width=13, height=15),
    "Room Production":   dict(left=24, top=28,  width=23, height=21),
    "Room Production 2": dict(left=23, top=3,   width=23, height=21),
}

# ---------- detector coords (your final) ----------
DETECTORS = {
    "Room 1": [dict(label="NH₃", x=35, y=35, units="ppm")],
    "Room 2": [dict(label="CO",  x=85, y=62, units="ppm")],
    "Room 3": [dict(label="O₂",  x=5,  y=44, units="%")],
    "Room 12 17": [dict(label="Ethanol", x=63, y=15, units="ppm")],
    "Room Production": [
        dict(label="NH₃", x=20, y=28, units="ppm"),
        dict(label="O₂",  x=88, y=40, units="%"),
    ],
    "Room Production 2": [
        dict(label="O₂",  x=83, y=45, units="%"),
        dict(label="H₂S", x=15, y=29, units="ppm"),
    ],
}

# ---------- thresholds & colors ----------
THRESHOLDS = {
    "O₂":      {"mode":"low",  "warn":19.5, "alarm":18.0, "units":"%"},
    "CO":      {"mode":"high", "warn":35.0, "alarm":50.0, "units":"ppm"},
    "H₂S":     {"mode":"high", "warn":10.0, "alarm":15.0, "units":"ppm"},
    "NH₃":     {"mode":"high", "warn":25.0, "alarm":35.0, "units":"ppm"},
    "Ethanol": {"mode":"high", "warn":300.0, "alarm":500.0, "units":"ppm"},
}
GAS_COLORS = {
    "NH₃": "#8b5cf6", "CO": "#ef4444", "O₂": "#60a5fa", "H₂S": "#eab308", "Ethanol": "#fb923c",
}

# ===== Overview (visual only) =====
def render_overview_image_only(images_dir: Path):
    ov = _find(images_dir, OVERVIEW_CANDS)
    if not ov:
        st.error("Overview image not found in /images.")
        return
    boxes = []
    for room, box in HOTSPOTS.items():
        boxes.append(f"""
          <a class="room-btn" href="?room={quote(room)}" target="_top"
             style="left:{box['left']}%; top:{box['top']}%; width:{box['width']}%; height:{box['height']}%;">
            <span>{room}</span>
          </a>""")
    buttons_html = "\n".join(boxes)
    html = f"""
    <div id="wrap" style="position:relative; width:min(1280px, 96%); margin:6px auto;
                          border:2px solid #0a2342; border-radius:12px; overflow:hidden;
                          box-shadow:0 18px 60px rgba(0,0,0,.15);">
      <style>
        .room-btn {{
          position:absolute; display:flex; align-items:flex-start; justify-content:flex-start;
          border:2px solid #22c55e; border-radius:10px; background:rgba(16,185,129,.22);
          color:#0b1220; font-weight:800; padding:4px 6px; text-decoration:none; z-index:10;
        }}
        .room-btn:hover {{ background:rgba(16,185,129,.32); }}
        .room-btn > span {{
          background:rgba(255,255,255,.7); border:1px solid rgba(10,35,66,.25);
          padding:2px 6px; border-radius:8px; font-size:12px;
        }}
      </style>
      <img src="{_img64(ov)}" alt="Facility Overview" style="display:block; width:100%; height:auto;" />
      {buttons_html}
    </div>"""
    components.html(html, height=820, scrolling=False)

# ===== Room (visual only) =====
def render_room_image_only(images_dir: Path, room: str,
                           simulate: bool = False,
                           selected_detector: str | None = None,
                           ops: dict | None = None):
    img = _find(images_dir, ROOM_FILES.get(room, []))
    if not img:
        st.error(f"No image found for {room} in /images.")
        return
    dets = DETECTORS.get(room, [])
    pins = []
    for d in dets:
        pins.append(f"""
          <div class="det-pin" style="left:{d['x']}%; top:{d['y']}%;">{d['label']}</div>
        """)
    pins_html = "\n".join(pins)
    chosen = selected_detector or (dets[0]["label"] if dets else "CO")
    cloud_color = GAS_COLORS.get(chosen, "#38bdf8")
    auto_cloud = "true" if simulate else "false"
    ops = ops or {}
    do_close = "true" if ops.get("close_shutter") else "false"
    do_vent = "true" if ops.get("ventilate") else "false"
    do_reset = "true" if ops.get("reset") else "false"

    html = f"""
    <div id="roomwrap" style="position:relative; width:100%; max-width:1200px; margin:6px 0;
                              border:2px solid #0a2342; border-radius:12px; overflow:hidden;
                              box-shadow:0 18px 60px rgba(0,0,0,.12);">
      <style>
        .det-pin {{
          position:absolute; transform:translate(-50%,-50%);
          border:2px solid #22c55e; border-radius:10px; background:#ffffff;
          padding:6px 10px; min-width:72px; text-align:center; z-index:30;
          box-shadow:0 0 10px rgba(34,197,94,.35); font-weight:800; color:#0f172a;
        }}
      </style>
      <img id="roomimg" src="{_img64(img)}" alt="{room}" style="display:block; width:100%; height:auto;" />
      <canvas id="cloud" style="position:absolute; left:0; top:0; width:100%; height:100%; pointer-events:none; z-index:15;"></canvas>
      <div id="shutter" style="position:absolute; right:0; top:0; width:26px; height:100%;
          background:rgba(15,23,42,.55); transform:translateX(110%); transition: transform 1.2s ease; z-index:18;
          border-left:2px solid rgba(148,163,184,.5);"></div>
      {pins_html}
    </div>
    <script>
      (function(){{
        const canvas = document.getElementById("cloud");
        const wrap = document.getElementById("roomwrap");
        const sh = document.getElementById("shutter");
        if (!canvas || !wrap || !sh) return;
        const ctx = canvas.getContext("2d");
        function resize() {{ const r = wrap.getBoundingClientRect(); canvas.width=r.width; canvas.height=r.height; }}
        resize(); window.addEventListener('resize', resize);
        function hexToRGBA(hex, a) {{
          const c=hex.replace('#',''); const r=parseInt(c.substring(0,2),16);
          const g=parseInt(c.substring(2,4),16); const b=parseInt(c.substring(4,6),16);
          return 'rgba('+r+','+g+','+b+','+a+')';
        }}
        let t0=null, raf=null;
        function drawCloud(ts){{
          if(!t0) t0=ts; const t=(ts-t0)/1000;
          ctx.clearRect(0,0,canvas.width,canvas.height);
          for(let i=0;i<28;i++) {{
            const ang=i*0.25; const rad=20+t*60+i*8;
            const x=canvas.width*0.55+Math.cos(ang)*rad;
            const y=canvas.height*0.55+Math.sin(ang)*rad*0.62;
            const a=Math.max(0,0.55-i*0.02-t*0.07);
            ctx.beginPath(); ctx.fillStyle=hexToRGBA("{cloud_color}", a);
            ctx.arc(x,y,32+i*0.8+t*3,0,Math.PI*2); ctx.fill();
          }}
          raf=requestAnimationFrame(drawCloud);
        }}
        function startCloud(){{ if(raf) cancelAnimationFrame(raf); t0=null; raf=requestAnimationFrame(drawCloud); }}
        function clearCloud(){{ if(raf) cancelAnimationFrame(raf); ctx.clearRect(0,0,canvas.width,canvas.height); }}
        function closeShutter(){{ sh.style.transform='translateX(0%)'; setTimeout(()=>{{ sh.style.transform='translateX(110%)'; }}, 6000); }}
        if ({auto_cloud}) startCloud();
        if ({do_close}) closeShutter();
        if ({do_vent} || {do_reset}) clearCloud();
      }})();
    </script>
    """
    components.html(html, height=720, scrolling=False)

# ===== Data panel & Live chart =====
def render_room_data_panel(images_dir: Path, room: str, selected_detector: str,
                           simulate: bool = False, ops: dict | None = None,
                           brand: dict | None = None):
    colL, colR = st.columns([2,1], gap="large")
    with colL:
        st.subheader(f"📈 {room} — {selected_detector}")
        period = st.radio("Range", ["Last 1 h","Today","7 days","60 days","6 months"],
                          horizontal=True, key=f"rng_{room}_{selected_detector}")
        now = int(time.time())
        if period == "Last 1 h":  start = now - 3600
        elif period == "Today":   start = int(pd.Timestamp("today").replace(hour=0, minute=0, second=0).timestamp())
        elif period == "7 days":  start = now - 7*24*3600
        elif period == "60 days": start = now - 60*24*3600
        else:                     start = now - 180*24*3600

        df = history.fetch_series(room, selected_detector, start, now)
        df = history.apply_runtime_ops(df, room, selected_detector, simulate=simulate, ops=ops or {})
        color = GAS_COLORS.get(selected_detector, "#38bdf8")
        thr = THRESHOLDS.get(selected_detector, {})

        base = alt.Chart(df).mark_line(color=color).encode(
            x=alt.X("t:T", title="Time"),
            y=alt.Y("value:Q", title=f"Reading ({thr.get('units','')})"),
            tooltip=[alt.Tooltip("t:T"), alt.Tooltip("value:Q", format=".2f")],
        )
        layers = [base]
        if thr:
            layers.append(alt.Chart(pd.DataFrame({"y":[thr["warn"]]})).mark_rule(stroke="#f59e0b"))
            layers.append(alt.Chart(pd.DataFrame({"y":[thr["alarm"]]})).mark_rule(stroke="#ef4444"))
        st.altair_chart(alt.layer(*layers), use_container_width=True)

    with colR:
        latest = history.latest_value(room, selected_detector)
        thr = THRESHOLDS.get(selected_detector, {})
        if latest is None:
            st.info("No data.")
            return
        if thr.get("mode") == "low":
            if latest <= thr["alarm"]: st.write(f"**ALARM** — {selected_detector} {latest:.2f}{thr['units']} (too low)")
            elif latest <= thr["warn"]: st.write(f"**WARN** — {selected_detector} {latest:.2f}{thr['units']} (low)")
            else: st.write(f"**OK** — {selected_detector} {latest:.2f}{thr['units']}")
        else:
            if latest >= thr["alarm"]: st.write(f"**ALARM** — {selected_detector} {latest:.2f}{thr['units']} (high)")
            elif latest >= thr["warn"]: st.write(f"**WARN** — {selected_detector} {latest:.2f}{thr['units']} (elevated)")
            else: st.write(f"**OK** — {selected_detector} {latest:.2f}{thr['units']}")

def render_live_only(images_dir: Path, room: str, selected_detector: str,
                     simulate=False, ops=None, brand=None):
    colL, colR = st.columns([2,1], gap="large")
    with colL:
        st.subheader(f"📈 {room} — {selected_detector} (Live)")
        now = int(time.time()); start = now - 3600
        df = history.fetch_series(room, selected_detector, start, now)
        df = history.apply_runtime_ops(df, room, selected_detector, simulate=simulate, ops=ops or {})
        color = GAS_COLORS.get(selected_detector, "#38bdf8")
        thr = THRESHOLDS.get(selected_detector, {})
        base = alt.Chart(df).mark_line(color=color).encode(x="t:T", y="value:Q", tooltip=["t:T","value:Q"])
        layers = [base]
        if thr:
            layers.append(alt.Chart(pd.DataFrame({"y":[thr["warn"]]})).mark_rule(stroke="#f59e0b"))
            layers.append(alt.Chart(pd.DataFrame({"y":[thr["alarm"]]})).mark_rule(stroke="#ef4444"))
        st.altair_chart(alt.layer(*layers), use_container_width=True)
    with colR:
        latest = history.latest_value(room, selected_detector)
        thr = THRESHOLDS.get(selected_detector, {})
        if latest is None: st.write("No data."); return
        if thr.get("mode") == "low":
            if latest <= thr["alarm"]: st.write(f"**ALARM** — {selected_detector} {latest:.2f}{thr['units']} (too low)")
            elif latest <= thr["warn"]: st.write(f"**WARN** — {selected_detector} {latest:.2f}{thr['units']} (low)")
            else: st.write(f"**OK** — {selected_detector} {latest:.2f}{thr['units']}")
        else:
            if latest >= thr["alarm"]: st.write(f"**ALARM** — {selected_detector} {latest:.2f}{thr['units']} (high)")
            elif latest >= thr["warn"]: st.write(f"**WARN** — {selected_detector} {latest:.2f}{thr['units']} (elevated)")
            else: st.write(f"**OK** — {selected_detector} {latest:.2f}{thr['units']}")


























        



