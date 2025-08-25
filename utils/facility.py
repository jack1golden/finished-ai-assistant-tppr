# utils/facility.py
from __future__ import annotations

import base64
import time
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import altair as alt

from . import ai
from . import history

# ---------- helpers ----------
def _b64_of(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _img64(path: Path) -> str:
    return f"data:image/{path.suffix.lstrip('.').lower()};base64,{_b64_of(path)}"

def _exists(p: Path) -> bool:
    return p.exists() and p.is_file()

def get_detectors_for(room: str):
    return DETECTORS.get(room, [])

def ts_str(ts: int) -> str:
    return pd.to_datetime(ts, unit="s").strftime("%Y-%m-%d %H:%M:%S")

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

# ---------- overview hotspots (positioned) ----------
HOTSPOTS = {
    "Room 1": dict(left=63, top=2,  width=14, height=16),
    "Room 2": dict(left=67, top=43, width=14, height=16),
    "Room 3": dict(left=60, top=19, width=14, height=16),
    "Room 12 17": dict(left=38, top=-13, width=13, height=15),
    "Room Production": dict(left=24, top=28, width=23, height=21),
    "Room Production 2": dict(left=23, top=3,  width=23, height=21),
}

# ---------- detectors (final placements you gave) ----------
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

# ---------- thresholds & gas colors ----------
THRESHOLDS = {
    "O₂":      {"mode": "low",  "warn": 19.5, "alarm": 18.0, "units": "%"},
    "CO":      {"mode": "high", "warn": 35.0, "alarm": 50.0, "units": "ppm"},
    "H₂S":     {"mode": "high", "warn": 10.0,  "alarm": 15.0, "units": "ppm"},
    "NH₃":     {"mode": "high", "warn": 25.0,  "alarm": 35.0, "units": "ppm"},
    "Ethanol": {"mode": "high", "warn": 300.0, "alarm": 500.0, "units": "ppm"},
}

GAS_COLORS = {
    "NH₃": "#8b5cf6",     # purple
    "CO": "#ef4444",      # red
    "O₂": "#60a5fa",      # blue
    "H₂S": "#eab308",     # yellow
    "Ethanol": "#fb923c", # orange
}

# ---------- live series sim (for manual chart ticks) ----------
def _sim_key(room: str, label: str) -> str:
    return f"{room}::{label}"

def _next_value(room: str, label: str) -> float:
    key = _sim_key(room, label)
    state = st.session_state.setdefault("det_sim", {})
    v = state.get(key, 10.0)
    v += float(np.random.uniform(-0.4, 0.9))
    v = max(0.0, v)
    state[key] = v
    return v

def _add_points(room: str, label: str, k: int = 5):
    key = _sim_key(room, label)
    buf = st.session_state.setdefault("det_buf", {}).setdefault(key, [])
    for _ in range(k):
        buf.append(_next_value(room, label))
    if len(buf) > 180:
        buf[:] = buf[-180:]
    return buf

def _status_for(label: str, value: float) -> tuple[str, str]:
    thr = THRESHOLDS.get(label)
    if not thr:
        return "OK", "Monitoring normal conditions."
    mode = thr["mode"]
    if mode == "low":
        if value <= thr["alarm"]:
            return "ALARM", f"{label} critically low ({value:.2f}{thr['units']}). Evacuate, ventilate, and isolate."
        if value <= thr["warn"]:
            return "WARN", f"{label} trending low ({value:.2f}{thr['units']}). Investigate consumption/airflow."
        return "OK", f"{label} normal ({value:.2f}{thr['units']})."
    else:
        if value >= thr["alarm"]:
            return "ALARM", f"{label} high ({value:.2f}{thr['units']}). Close shutters, isolate, evacuate."
        if value >= thr["warn"]:
            return "WARN", f"{label} elevated ({value:.2f}{thr['units']}). Increase extraction, check for leaks."
        return "OK", f"{label} normal ({value:.2f}{thr['units']})."

# ---------- initialize history once ----------
history.init_if_needed(DETECTORS, days=7)

# ======================================================
# Overview with traffic‑light strip
# ======================================================
def _room_worst_status(room: str) -> str:
    dets = DETECTORS.get(room, [])
    worst = "OK"
    for d in dets:
        label = d["label"]
        val = history.latest_value(room, label)
        if val is None:
            continue
        s, _ = _status_for(label, val)
        order = {"OK": 0, "WARN": 1, "ALARM": 2}
        if order[s] > order[worst]:
            worst = s
            if worst == "ALARM":
                break
    return worst

def _status_chip(room: str) -> str:
    s = _room_worst_status(room)
    color = {"OK":"#16a34a","WARN":"#f59e0b","ALARM":"#ef4444"}[s]
    return f'<span class="chip" style="background:{color}">{room}: {s}</span>'

def render_overview(images_dir: Path):
    ov_path = _find_first(images_dir, OVERVIEW_CANDS)
    if not ov_path:
        st.error("Overview image not found in /images.")
        return

    chips = "".join(_status_chip(r) for r in ["Room 1","Room 2","Room 3","Room Production","Room Production 2","Room 12 17"])

    hotspots_html = []
    for room, box in HOTSPOTS.items():
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
    <div class="strip" style="display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 10px 0;">{chips}</div>
    <div class="wrap" style="
      position:relative; width:min(1280px,96%); margin:8px auto;
      border:2px solid #0a2342; border-radius:12px; overflow:hidden;
      box-shadow:0 18px 60px rgba(0,0,0,.20); background:#fff;">
      <img src="{_img64(ov_path)}" alt="overview" style="display:block; width:100%; height:auto;" />
      {tags}
      <div style="position:absolute; right:10px; bottom:8px; color:#d81f26; font-weight:700; background:#fff9; padding:2px 6px; border-radius:6px; border:1px solid #0a2342;">
        OBW Technologies
      </div>
    </div>
    """
    components.html(html, height=820, scrolling=False)

# ======================================================
# Room view — image + badges + gas cloud/shutter + timeline + predictive chart + AI + auto‑log
# ======================================================
def render_room(
    images_dir: Path,
    room: str,
    simulate: bool = False,
    selected_detector: str | None = None,
    ai_force_rule: bool = False,
    ops: dict | None = None,
    brand: dict | None = None,
):
    room_path = _find_first(images_dir, ROOM_FILES.get(room, []))
    if not room_path:
        st.error(f"No image found for {room} in /images.")
        return

    dets = DETECTORS.get(room, [])
    colL, colR = st.columns([2, 1], gap="large")

    # Build detector pins
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
                   window.location.search = '?room=' + encodeURIComponent('{room}') + '&det=' + encodeURIComponent('{lbl}');
                 }}
                 return false;"
               style="left:{d['x']}%;top:{d['y']}%;">
              <div class="lbl">{lbl}</div>
            </a>
            """
        )
    pins = "\n".join(pins_html)

    # Operator one-shot triggers
    ops = ops or {}
    trigger_shutter = "true" if ops.get("close_shutter") else "false"
    trigger_vent = "true" if ops.get("ventilate") else "false"
    trigger_reset = "true" if ops.get("reset") else "false"
    trigger_ack = "true" if ops.get("ack") else "false"
    auto_cloud = "true" if simulate else "false"

    with colL:
        cloud_color = GAS_COLORS.get(selected_detector or (dets[0]["label"] if dets else "CO"), "#38bdf8")
        room_html = f"""
        <div id="roomwrap" style="
            position:relative; width:100%; max-width:1200px; margin:6px 0;
            border:2px solid #0a2342; border-radius:12px; overflow:hidden;
            box-shadow:0 18px 60px rgba(0,0,0,.12); background:#fff;">
          <img id="roomimg" src="{_img64(room_path)}" alt="{room}" style="display:block; width:100%; height:auto;" />
          <canvas id="cloud" class="cloud" style="position:absolute; left:0; top:0; width:100%; height:100%; pointer-events:none; z-index:15;"></canvas>
          <div id="shutter" style="
              position:absolute; right:0; top:0; width:26px; height:100%;
              background:rgba(15,23,42,.55);
              transform:translateX(110%); transition: transform 1.2s ease; z-index:18;
              border-left:2px solid rgba(148,163,184,.5);"></div>
          {pins}
        </div>
        <script>
          (function(){{
            const autoCloud = {auto_cloud};
            const triggerShutter = {trigger_shutter};
            const triggerVent = {trigger_vent};
            const triggerReset = {trigger_reset};
            const canvas = document.getElementById("cloud");
            const wrap = document.getElementById("roomwrap");
            const sh = document.getElementById("shutter");
            const ctx = canvas.getContext("2d");

            function resize() {{
              const rect = wrap.getBoundingClientRect();
              canvas.width = rect.width;
              canvas.height = rect.height;
            }}
            resize(); window.addEventListener('resize', resize);

            let t0 = null, raf = null;
            function hexToRGBA(hex, a) {{
              const c = hex.replace('#','');
              const r = parseInt(c.substring(0,2),16);
              const g = parseInt(c.substring(2,4),16);
              const b = parseInt(c.substring(4,6),16);
              return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
            }}

            function drawCloud(ts) {{
              if (!t0) t0 = ts;
              const t = (ts - t0)/1000;
              ctx.clearRect(0,0,canvas.width,canvas.height);
              for (let i=0;i<28;i++) {{
                const ang = i * 0.25;
                const rad = 20 + t*60 + i*8;
                const x = canvas.width*0.55 + Math.cos(ang)*rad;
                const y = canvas.height*0.55 + Math.sin(ang)*rad*0.62;
                const a = Math.max(0, 0.55 - i*0.02 - t*0.07);
                ctx.beginPath();
                ctx.fillStyle = hexToRGBA("{cloud_color}", a);
                ctx.arc(x, y, 32 + i*0.8 + t*3, 0, Math.PI*2);
                ctx.fill();
              }}
              raf = requestAnimationFrame(drawCloud);
            }}
            function startCloud() {{
              if (raf) cancelAnimationFrame(raf);
              t0 = null;
              raf = requestAnimationFrame(drawCloud);
            }}
            function clearCloud() {{
              if (raf) cancelAnimationFrame(raf);
              ctx.clearRect(0,0,canvas.width,canvas.height);
            }}
            function closeShutter() {{
              sh.classList.add('active');
              sh.style.transform = 'translateX(0%)';
              setTimeout(()=>{{ sh.style.transform = 'translateX(110%)'; }}, 6000);
            }}
            if (autoCloud) startCloud();
            if (triggerShutter) closeShutter();
            if (triggerVent) clearCloud();
            if (triggerReset) {{ clearCloud(); }}
          }})();
        </script>
        """
        components.html(room_html, height=720, scrolling=False)

    # RIGHT side: timeline, predictive chart, AI + auto‑log + action logging
    with colR:
        if selected_detector:
            st.subheader(f"📈 {selected_detector} — Trend")
            period = st.radio(
                "Range",
                ["Last 10 min", "Last 1 h", "Today", "7 days"],
                horizontal=True,
                key=f"rng_{room}_{selected_detector}"
            )
            now = int(time.time())
            if period == "Last 10 min":
                start = now - 10*60
            elif period == "Last 1 h":
                start = now - 60*60
            elif period == "Today":
                start = int(pd.Timestamp("today").replace(hour=0, minute=0, second=0).timestamp())
            else:
                start = now - 7*24*3600

            df = history.fetch_series(room, selected_detector, start, now)
            if df.empty:
                st.info("No data for the selected range.")
            else:
                recent = df.tail(15)
                slope = 0.0
                if len(recent) >= 2:
                    x = (recent["t"].astype("int64")//10**9 - int(recent["t"].iloc[0].timestamp())) / 60.0
                    y = recent["value"].to_numpy()
                    slope = float(np.polyfit(x, y, 1)[0])

                proj_minutes = np.arange(1, 6)
                last_v = float(df["value"].iloc[-1])
                last_t = df["t"].iloc[-1]
                proj_t = [last_t + pd.Timedelta(minutes=int(m)) for m in proj_minutes]
                proj_v = [last_v + slope*m for m in proj_minutes]
                df_proj = pd.DataFrame({"t": proj_t, "value": proj_v, "kind":"Projected"})
                df_obs = df.assign(kind="Observed")
                df_all = pd.concat([df_obs, df_proj], ignore_index=True)

                gas_color = GAS_COLORS.get(selected_detector, "#38bdf8")
                thr = THRESHOLDS.get(selected_detector, {})
                base_chart = (
                    alt.Chart(df_all)
                    .mark_line()
                    .encode(
                        x=alt.X("t:T", title="Time"),
                        y=alt.Y("value:Q", title=f"Reading ({thr.get('units','')})"),
                        strokeDash=alt.condition(alt.datum.kind == "Projected",
                                                 alt.value([4,4]), alt.value([0,0])),
                        tooltip=[alt.Tooltip("t:T"), alt.Tooltip("value:Q", format=".2f"), "kind:N"],
                        color=alt.Color("kind:N", scale=alt.Scale(range=[gas_color, gas_color]), legend=None),
                    )
                )
                rules = []
                if thr:
                    rules.append(alt)
















        



