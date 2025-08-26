# utils/facility.py
from __future__ import annotations
import base64, time
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
        if _exists(p):
            return p
    return None

# ---------- overview hotspots (visual only) ----------
HOTSPOTS = {
    "Room 1":            dict(left=63, top=2,   width=14, height=16),
    "Room 2":            dict(left=67, top=43,  width=14, height=16),
    "Room 3":            dict(left=60, top=19,  width=14, height=16),
    "Room 12 17":        dict(left=38, top=-13, width=13, height=15),
    "Room Production":   dict(left=24, top=28,  width=23, height=21),
    "Room Production 2": dict(left=23, top=3,   width=23, height=21),
}

# ---------- detector coordinates (your final set) ----------
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

# ---------- thresholds & colors & hardware ----------
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
HONEYWELL_REC = {
    "NH₃": "Honeywell Sensepoint XCD (NH₃) or XNX + EC-Tox (NH₃)",
    "CO":  "Honeywell Sensepoint XCD (CO) or XNX + EC-Tox (CO)",
    "O₂":  "Honeywell Sensepoint XCD (O₂) or XNX + EC-O₂",
    "H₂S": "Honeywell Sensepoint XCD (H₂S) or XNX + EC-Tox (H₂S)",
    "Ethanol": "Honeywell Sensepoint XCD (VOC) or XNX + PID",
}

# ---------- seed 60 days of synthetic history with weekly spikes ----------
history.init_if_needed(DETECTORS, days=60, spikes_per_week=1)

# ======================================================
# 1) Overview IMAGE ONLY (visual hotspots preserved)
# ======================================================
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
    </div>
    """
    components.html(html, height=820, scrolling=False)

# ======================================================
# 2) Room IMAGE ONLY (visual hotspots preserved + gas cloud & shutter)
# ======================================================
def render_room_image_only(images_dir: Path, room: str,
                           simulate: bool = False,
                           selected_detector: str | None = None,
                           ops: dict | None = None):
    room_img = _find(images_dir, ROOM_FILES.get(room, []))
    if not room_img:
        st.error(f"No image found for {room} in /images.")
        return

    dets = DETECTORS.get(room, [])
    pins = []
    for d in dets:
        lbl = d["label"]
        pins.append(f"""
          <a class="det-btn" href="?room={quote(room)}&det={quote(lbl)}" target="_top"
             style="left:{d['x']}%; top:{d['y']}%;">{lbl}</a>
        """)
    pins_html = "\n".join(pins)

    auto_cloud = "true" if simulate else "false"
    chosen = selected_detector or (dets[0]["label"] if dets else "CO")
    cloud_color = GAS_COLORS.get(chosen, "#38bdf8")
    ops = ops or {}
    do_close = "true" if ops.get("close_shutter") else "false"
    do_vent = "true" if ops.get("ventilate") else "false"
    do_reset = "true" if ops.get("reset") else "false"

    html = f"""
    <div id="roomwrap" style="position:relative; width:100%; max-width:1200px; margin:6px 0;
                              border:2px solid #0a2342; border-radius:12px; overflow:hidden;
                              box-shadow:0 18px 60px rgba(0,0,0,.12);">
      <style>
        .det-btn {{
          position:absolute; transform:translate(-50%,-50%);
          border:2px solid #22c55e; border-radius:10px; background:#ffffff;
          padding:6px 10px; min-width:72px; text-align:center; z-index:30;
          box-shadow:0 0 10px rgba(34,197,94,.35); font-weight:800; color:#0f172a; text-decoration:none;
        }}
        .det-btn:hover {{ background:#eaffea; }}
      </style>
      <img id="roomimg" src="{_img64(room_img)}" alt="{room}" style="display:block; width:100%; height:auto;" />
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
        const autoCloud={auto_cloud};
        if(autoCloud) startCloud();
        if ({do_close}) closeShutter();
        if ({do_vent} || {do_reset}) clearCloud();
      }})();
    </script>
    """
    components.html(html, height=720, scrolling=False)

# ======================================================
# 3) Data Panel (live chart + thresholds + Honeywell + AI + anomalies)
# ======================================================
def render_room_data_panel(images_dir: Path, room: str, selected_detector: str,
                           simulate: bool = False, ai_force_rule: bool = False,
                           ops: dict | None = None, brand: dict | None = None):
    colL, colR = st.columns([2, 1], gap="large")

    with colL:
        st.subheader(f"📈 {room} — {selected_detector} Trend")
        period = st.radio("Range", ["Last 10 min","Last 1 h","Today","7 days","60 days"],
                          horizontal=True, key=f"rng_{room}_{selected_detector}")
        now = int(time.time())
        if period == "Last 10 min": start = now - 10*60
        elif period == "Last 1 h":  start = now - 60*60
        elif period == "Today":     start = int(pd.Timestamp("today").replace(hour=0, minute=0, second=0).timestamp())
        elif period == "7 days":    start = now - 7*24*3600
        else:                       start = now - 60*24*3600

        # Fetch historical baseline (2 months seeded, weekly spikes baked in)
        df = history.fetch_series(room, selected_detector, start, now)

        # If simulate flag set: overlay “live” spike shape for last few minutes
        df = history.apply_runtime_ops(df, room, selected_detector, simulate=simulate, ops=ops or {})

        # Compute anomaly pins (z-score on rolling window)
        ann = history.anomalies(df)

        # Short projection (5 min)
        df_proj = history.project_linear(df, minutes=5)

        # Chart
        gas_color = GAS_COLORS.get(selected_detector, "#38bdf8")
        thr = THRESHOLDS.get(selected_detector, {})
        base = alt.Chart(df.assign(kind="Observed")).mark_line(color=gas_color).encode(
            x=alt.X("t:T", title="Time"),
            y=alt.Y("value:Q", title=f"Reading ({thr.get('units','')})"),
            tooltip=[alt.Tooltip("t:T"), alt.Tooltip("value:Q", format=".2f"), "kind:N"],
        )
        layers = [base]
        if df_proj is not None and not df_proj.empty:
            layers.append(
                alt.Chart(df_proj.assign(kind="Projected")).mark_line(strokeDash=[4,4], color=gas_color).encode(
                    x="t:T", y="value:Q"
                )
            )
        if ann is not None and not ann.empty:
            layers.append(
                alt.Chart(ann).mark_point(shape="triangle-up", size=60, color="#ef4444").encode(
                    x="t:T", y="value:Q", tooltip=["t:T","value:Q"]
                )
            )
        if thr:
            layers.append(alt.Chart(pd.DataFrame({"y":[thr["warn"]]})).mark_rule(stroke="#f59e0b"))
            layers.append(alt.Chart(pd.DataFrame({"y":[thr["alarm"]]})).mark_rule(stroke="#ef4444"))
        st.altair_chart(alt.layer(*layers), use_container_width=True)

        latest = float(df["value"].iloc[-1]) if not df.empty else None
        status = "OK"; msg = "Monitoring normal conditions."
        if latest is not None:
            status, msg = _status_for(selected_detector, latest)
        st.markdown(f"**Status:** {status}")
        st.caption(msg)
        if rec := HONEYWELL_REC.get(selected_detector):
            st.caption(f"Recommended hardware: {rec}")

        # AI auto-react stronger on simulate
        if latest is not None:
            prompt = "Provide precise actionable steps; prioritize people-first safety, isolation, ventilation, and escalation. Max 5 bullets."
            answer = ai.ask_ai(
                prompt,
                context={
                    "room": room, "gas": selected_detector, "value": latest,
                    "status": status, "thresholds": thr, "simulate": simulate,
                    "recent_series": df['value'].tail(60).tolist(),
                    "projection_minutes": 5
                },
                force_rule=ai_force_rule
            )
            st.session_state.setdefault("ai_log", {}).setdefault(room, []).append(
                {"ts": int(time.time()), "text": answer}
            )

    with colR:
        st.subheader("🤖 AI Safety Assistant")
        if q := st.chat_input("Ask about thresholds, actions or risk…", key=f"chat_{room}_{selected_detector}"):
            st.chat_message("user").write(q)
            now = int(time.time())
            dfq = history.fetch_series(room, selected_detector, now-3600, now)
            latest = float(dfq["value"].iloc[-1]) if dfq is not None and not dfq.empty else None
            thr = THRESHOLDS.get(selected_detector, {})
            status = "OK"
            if latest is not None and thr:
                status, _ = _status_for(selected_detector, latest)
            ans = ai.ask_ai(
                q,
                context={"room": room, "gas": selected_detector, "value": latest,
                         "status": status, "thresholds": thr,
                         "recent_series": dfq['value'].tail(60).tolist() if (dfq is not None and not dfq.empty) else []},
                force_rule=ai_force_rule
            )
            st.chat_message("ai").write(ans)

# ======================================================
# 4) Live Data helper (used by the Live tab)
# ======================================================
def render_live_only(images_dir: Path, room: str, selected_detector: str,
                     simulate=False, ai_force_rule=False, ops=None, brand=None):
    colL, colR = st.columns([2,1], gap="large")
    with colL:
        st.subheader(f"📈 {room} — {selected_detector} Trend")
        now = int(time.time()); start = now - 3600
        df = history.fetch_series(room, selected_detector, start, now)
        df = history.apply_runtime_ops(df, room, selected_detector, simulate=simulate, ops=ops or {})
        gas_color = GAS_COLORS.get(selected_detector, "#38bdf8")
        thr = THRESHOLDS.get(selected_detector, {})

        ann = history.anomalies(df)
        df_proj = history.project_linear(df, minutes=5)

        base = alt.Chart(df.assign(kind="Observed")).mark_line(color=gas_color).encode(
            x="t:T", y="value:Q", tooltip=["t:T","value:Q"]
        )
        layers = [base]
        if df_proj is not None and not df_proj.empty:
            layers.append(
                alt.Chart(df_proj.assign(kind="Projected")).mark_line(strokeDash=[4,4], color=gas_color).encode(
                    x="t:T", y="value:Q"
                )
            )
        if ann is not None and not ann.empty:
            layers.append(
                alt.Chart(ann).mark_point(shape="triangle-up", size=60, color="#ef4444").encode(
                    x="t:T", y="value:Q"
                )
            )
        if thr:
            layers.append(alt.Chart(pd.DataFrame({"y":[thr["warn"]]})).mark_rule(stroke="#f59e0b"))
            layers.append(alt.Chart(pd.DataFrame({"y":[thr["alarm"]]})).mark_rule(stroke="#ef4444"))
        st.altair_chart(alt.layer(*layers), use_container_width=True)

        latest = float(df["value"].iloc[-1]) if not df.empty else None
        status, msg = ("OK", "Monitoring normal conditions.")
        if latest is not None:
            status, msg = _status_for(selected_detector, latest)
        st.write(f"**Status:** {status} — {msg}")
        if rec := HONEYWELL_REC.get(selected_detector):
            st.caption(f"Honeywell hardware: {rec}")

    with colR:
        st.subheader("🤖 AI Assistant (Live)")
        if q := st.chat_input("Ask about this detector…", key=f"chat_live_{room}_{selected_detector}"):
            st.chat_message("user").write(q)
            ans = ai.ask_ai(q, context={"room": room, "gas": selected_detector}, force_rule=ai_force_rule)
            st.chat_message("ai").write(ans)

# ---------- status ----------
def _status_for(label: str, value: float) -> tuple[str, str]:
    thr = THRESHOLDS.get(label)
    if not thr:
        return "OK", "Monitoring normal conditions."
    if thr["mode"] == "low":
        if value <= thr["alarm"]: return "ALARM", f"{label} critically low ({value:.2f}{thr['units']})."
        if value <= thr["warn"] : return "WARN",  f"{label} trending low ({value:.2f}{thr['units']})."
        return "OK", f"{label} normal ({value:.2f}{thr['units']})."
    else:
        if value >= thr["alarm"]: return "ALARM", f"{label} high ({value:.2f}{thr['units']})."
        if value >= thr["warn"] : return "WARN",  f"{label} elevated ({value:.2f}{thr['units']})."
        return "OK", f"{label} normal ({value:.2f}{thr['units']})."

# ---------- snapshot ----------
def build_facility_snapshot() -> dict:
    snap = {}
    for room, dets in DETECTORS.items():
        node = {}
        for d in dets:
            label = d["label"]
            val = history.latest_value(room, label)
            if val is None: continue
            status, _ = _status_for(label, val)
            node[label] = {"value": float(val), "status": status}
        snap[room] = node
    return snap
























        



