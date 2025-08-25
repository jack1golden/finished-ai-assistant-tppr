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

# ---------- overview hotspots (final placements you approved) ----------
HOTSPOTS = {
    "Room 1":          dict(left=63, top=2,  width=14, height=16),
    "Room 2":          dict(left=67, top=43, width=14, height=16),
    "Room 3":          dict(left=60, top=19, width=14, height=16),
    "Room 12 17":      dict(left=38, top=-13, width=13, height=15),
    "Room Production": dict(left=24, top=28, width=23, height=21),
    "Room Production 2": dict(left=23, top=3, width=23, height=21),
}

# ---------- detectors (final placements you approved) ----------
DETECTORS = {
    "Room 1": [dict(label="NH₃", x=35, y=35, units="ppm")],
    "Room 2": [dict(label="CO",  x=85, y=62, units="ppm")],               # (x=85, y=62) final
    "Room 3": [dict(label="O₂",  x=5,  y=44, units="%")],
    "Room 12 17": [dict(label="Ethanol", x=63, y=15, units="ppm")],       # moved up as requested
    "Room Production": [
        dict(label="NH₃", x=20, y=28, units="ppm"),                       # NH3 left +2% done earlier
        dict(label="O₂",  x=88, y=40, units="%"),                         # O2 up +2% done earlier
    ],
    "Room Production 2": [
        dict(label="O₂",  x=83, y=45, units="%"),                         # O2 right +5% done earlier
        dict(label="H₂S", x=15, y=29, units="ppm"),                       # H2S left +2%, up +4% done earlier
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

# Honeywell recommended detectors (simple mapping for demo)
HONEYWELL_REC = {
    "NH₃": "Honeywell Sensepoint XCD (NH₃) or XNX + EC‑Tox (NH₃)",
    "CO": "Honeywell Sensepoint XCD (CO) or XNX + EC‑Tox (CO)",
    "O₂": "Honeywell Sensepoint XCD (O₂) or XNX + EC‑O₂",
    "H₂S": "Honeywell Sensepoint XCD (H₂S) or XNX + EC‑Tox (H₂S)",
    "Ethanol": "Honeywell Sensepoint XCD (VOC) or XNX + PID",
}

# ---------- init 7 days of synthetic history (for charts & AI context) ----------
history.init_if_needed(DETECTORS, days=7)

# ======================================================
# Overview (image + clickable hotspots with robust fallback)
# ======================================================
def _room_worst_status(room: str) -> str:
    dets = DETECTORS.get(room, [])
    worst = "OK"
    order = {"OK": 0, "WARN": 1, "ALARM": 2}
    for d in dets:
        label = d["label"]
        val = history.latest_value(room, label)
        if val is None:
            continue
        s, _ = _status_for(label, val)
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

    # Build hotspots (href + postMessage; no `return false`)
    tags = []
    for room, box in HOTSPOTS.items():
        tags.append(
            f"""
            <a class="hotspot" data-room="{room}"
               href="?room={quote(room)}" target="_top"
               onclick="try{{window.parent.postMessage({{type:'setQS', room:'{room}', det:null}}, '*');}}catch(_){{}}"
               style="position:absolute; left:{box['left']}%; top:{box['top']}%; width:{box['width']}%; height:{box['height']}%;
                      border:2px solid rgba(34,197,94,.95); border-radius:10px;
                      background:rgba(16,185,129,.22); color:#0b1220; font-weight:800; font-size:12px;
                      display:flex; align-items:flex-start; justify-content:flex-start; padding:4px 6px; z-index:20; text-decoration:none;">
              <span style="background:rgba(2,6,23,.06); border:1px solid rgba(10,35,66,.25); padding:2px 6px; border-radius:8px;">{room}</span>
            </a>
            """
        )
    hotspots_html = "\n".join(tags)

    html = f"""
    <div class="strip" style="display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 10px 0;">{chips}</div>
    <div id="ovwrap" style="
      position:relative; width:min(1280px,96%); margin:8px auto;
      border:2px solid #0a2342; border-radius:12px; overflow:hidden;
      box-shadow:0 18px 60px rgba(0,0,0,.20); background:#fff;">
      <style>
        .hotspot:hover {{ background:rgba(16,185,129,.32) !important; }}
        .chip {{ display:inline-block; color:#0b1220; font-weight:800; padding:6px 10px;
                 border-radius:999px; box-shadow:0 1px 6px rgba(0,0,0,.2); }}
      </style>
      <img src="{_img64(ov_path)}" alt="overview" style="display:block; width:100%; height:auto;" />
      {hotspots_html}
      <div style="position:absolute; right:10px; bottom:8px; color:#d81f26; font-weight:700; background:#fff9; padding:2px 6px; border-radius:6px; border:1px solid #0a2342;">
        OBW Technologies
      </div>
    </div>
    """
    components.html(html, height=820, scrolling=False)

# ======================================================
# Room view (image + clickable detector badges + cloud/shutter canvas + right panel)
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

    # Left: room image + detector pins + cloud & shutter
    pins_html = []
    for d in dets:
        lbl = d["label"]
        pins_html.append(
            f"""
            <a class="detector"
               href="?room={quote(room)}&det={quote(lbl)}" target="_top"
               onclick="try{{window.parent.postMessage({{type:'setQS', room:'{room}', det:'{lbl}'}}, '*');}}catch(_){{}}"
               style="position:absolute; left:{d['x']}%; top:{d['y']}%; transform:translate(-50%,-50%);
                      border:2px solid #22c55e; border-radius:10px; background:#ffffff;
                      padding:6px 10px; min-width:72px; text-align:center; z-index:30;
                      box-shadow:0 0 10px rgba(34,197,94,.35); font-weight:800; color:#0f172a; text-decoration:none;">
              <div class="lbl" style="font-size:14px; line-height:1.1;">{lbl}</div>
            </a>
            """
        )
    pins = "\n".join(pins_html)

    auto_cloud = "true" if simulate else "false"
    cloud_color = GAS_COLORS.get(selected_detector or (dets[0]["label"] if dets else "CO"), "#38bdf8")
    ops = ops or {}

    with colL:
        html = f"""
        <div id="roomwrap" style="
            position:relative; width:100%; max-width:1200px; margin:6px 0;
            border:2px solid #0a2342; border-radius:12px; overflow:hidden;
            box-shadow:0 18px 60px rgba(0,0,0,.12); background:#fff;">
          <style>.detector:hover {{ background:#eaffea !important; }}</style>
          <img id="roomimg" src="{_img64(room_path)}" alt="{room}" style="display:block; width:100%; height:auto;" />
          <canvas id="cloud" style="position:absolute; left:0; top:0; width:100%; height:100%; pointer-events:none; z-index:15;"></canvas>
          <div id="shutter" style="position:absolute; right:0; top:0; width:26px; height:100%;
              background:rgba(15,23,42,.55); transform:translateX(110%); transition: transform 1.2s ease; z-index:18;
              border-left:2px solid rgba(148,163,184,.5);"></div>
          {pins}
        </div>
        <script>
          (function(){{
            const canvas = document.getElementById("cloud");
            const wrap = document.getElementById("roomwrap");
            const sh = document.getElementById("shutter");
            const ctx = canvas.getContext("2d");
            function resize() {{
              const rect = wrap.getBoundingClientRect(); canvas.width = rect.width; canvas.height = rect.height;
            }}
            resize(); window.addEventListener('resize', resize);
            function hexToRGBA(hex, a) {{
              const c = hex.replace('#',''); const r = parseInt(c.substring(0,2),16);
              const g = parseInt(c.substring(2,4),16); const b = parseInt(c.substring(4,6),16);
              return 'rgba('+r+','+g+','+b+','+a+')';
            }}
            let t0 = null, raf = null;
            function drawCloud(ts) {{
              if (!t0) t0 = ts; const t = (ts - t0)/1000;
              ctx.clearRect(0,0,canvas.width,canvas.height);
              for (let i=0;i<28;i++) {{
                const ang = i * 0.25; const rad = 20 + t*60 + i*8;
                const x = canvas.width*0.55 + Math.cos(ang)*rad;
                const y = canvas.height*0.55 + Math.sin(ang)*rad*0.62;
                const a = Math.max(0, 0.55 - i*0.02 - t*0.07);
                ctx.beginPath(); ctx.fillStyle = hexToRGBA("{cloud_color}", a);
                ctx.arc(x, y, 32 + i*0.8 + t*3, 0, Math.PI*2); ctx.fill();
              }}
              raf = requestAnimationFrame(drawCloud);
            }}
            function startCloud() {{ if (raf) cancelAnimationFrame(raf); t0 = null; raf = requestAnimationFrame(drawCloud); }}
            function clearCloud() {{ if (raf) cancelAnimationFrame(raf); ctx.clearRect(0,0,canvas.width,canvas.height); }}
            function closeShutter() {{ sh.style.transform = 'translateX(0%)'; setTimeout(()=>{{ sh.style.transform = 'translateX(110%)'; }}, 6000); }}
            const autoCloud = {auto_cloud};
            if (autoCloud) startCloud();
            {"closeShutter();" if ops.get("close_shutter") else ""}
            {"clearCloud();" if ops.get("ventilate") else ""}
            {"clearCloud();" if ops.get("reset") else ""}
          }})();
        </script>
        """
        components.html(html, height=720, scrolling=False)

    # Right: chart + projection + thresholds + Honeywell + AI/logs
    with colR:
        if not selected_detector:
            st.info("Click a detector badge on the image (or use the selector above) to view its trend.")
            return

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
            # simple linear projection from recent points
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
                    strokeDash=alt.condition(
                        alt.datum.kind == "Projected",
                        alt.value([4,4]),
                        alt.value([0,0])
                    ),
                    tooltip=[alt.Tooltip("t:T"), alt.Tooltip("value:Q", format=".2f"), "kind:N"],
                    color=alt.Color("kind:N", scale=alt.Scale(range=[gas_color, gas_color]), legend=None),
                )
            )
            layers = [base_chart]
            if thr:
                warn_rule = alt.Chart(pd.DataFrame({"y":[thr["warn"]]})).mark_rule(stroke="#f59e0b")
                alarm_rule = alt.Chart(pd.DataFrame({"y":[thr["alarm"]]})).mark_rule(stroke="#ef4444")
                layers.extend([warn_rule, alarm_rule])

            st.altair_chart(alt.layer(*layers).resolve_scale(color="independent"), use_container_width=True)

            latest = float(df["value"].iloc[-1])
            status, msg = _status_for(selected_detector, latest)
            st.markdown(f"**Status:** {status}")
            st.caption(msg)

            # Honeywell recommendation
            rec = HONEYWELL_REC.get(selected_detector)
            if rec:
                st.markdown(f"**Recommended hardware:** {rec}")

            # AI auto‑log on status change
            key = f"{room}::{selected_detector}"
            last_status = st.session_state.setdefault("last_status", {}).get(key)
            if last_status != status:
                st.session_state["last_status"][key] = status
                mean, sd = history.stats(room, selected_detector, window_hours=24)
                crossing = None
                if thr:
                    if thr["mode"] == "high" and latest >= thr["warn"]:
                        crossing = 0 if latest >= thr["alarm"] else 1
                    elif thr["mode"] == "low" and latest <= thr["warn"]:
                        crossing = 0 if latest <= thr["alarm"] else 1

                prompt = f"Status changed to {status}. Provide actionable steps (max 4 bullets)."
                answer = ai.ask_ai(
                    prompt,
                    context={
                        "room": room,
                        "gas": selected_detector,
                        "value": latest,
                        "status": status,
                        "thresholds": thr,
                        "simulate": simulate,
                        "recent_series": df['value'].tail(60).tolist(),
                        "mean": mean,
                        "std": sd,
                        "projection_minutes": crossing
                    },
                    force_rule=ai_force_rule
                )
                log = st.session_state.setdefault("ai_log", {}).setdefault(room, [])
                log.append({"ts": int(time.time()), "text": answer})

        st.divider()
        st.subheader("🤖 AI Safety Assistant")
        if q := st.chat_input("Ask about thresholds, actions or risk…", key=f"chat_{room}"):
            st.chat_message("user").write(q)
            now = int(time.time())
            dfq = history.fetch_series(room, selected_detector, now-3600, now)
            latest = float(dfq["value"].iloc[-1]) if not dfq.empty else None
            thr = THRESHOLDS.get(selected_detector, {})
            status = "OK"
            if latest is not None and thr:
                status, _ = _status_for(selected_detector, latest)
            ans = ai.ask_ai(
                q,
                context={
                    "room": room,
                    "gas": selected_detector,
                    "value": latest,
                    "status": status,
                    "thresholds": thr,
                    "simulate": simulate,
                    "recent_series": dfq["value"].tail(60).tolist() if not dfq.empty else [],
                    "mean": history.stats(room, selected_detector, 24)[0],
                    "std": history.stats(room, selected_detector, 24)[1],
                },
                force_rule=ai_force_rule
            )
            st.chat_message("ai").write(ans)

# ---------- status logic ----------
def _status_for(label: str, value: float) -> tuple[str, str]:
    thr = THRESHOLDS.get(label)
    if not thr:
        return "OK", "Monitoring normal conditions."
    if thr["mode"] == "low":
        if value <= thr["alarm"]:
            return "ALARM", f"{label} critically low ({value:.2f}{thr['units']}). Evacuate, ventilate, isolate."
        if value <= thr["warn"]:
            return "WARN", f"{label} trending low ({value:.2f}{thr['units']}). Investigate consumption/airflow."
        return "OK", f"{label} normal ({value:.2f}{thr['units']})."
    else:
        if value >= thr["alarm"]:
            return "ALARM", f"{label} high ({value:.2f}{thr['units']}). Close shutters, isolate source, evacuate."
        if value >= thr["warn"]:
            return "WARN", f"{label} elevated ({value:.2f}{thr['units']}). Increase extraction, check for leaks."
        return "OK", f"{label} normal ({value:.2f}{thr['units']})."

# ======================================================
# Live Data helper (used by the Live Data tab)
# ======================================================
def render_live_only(
    images_dir: Path,
    room: str,
    selected_detector: str,
    simulate: bool = False,
    ai_force_rule: bool = False,
    ops: dict | None = None,
    brand: dict | None = None,
):
    """Standalone live panel for the Live Data tab."""
    ops = ops or {}
    colL, colR = st.columns([2, 1], gap="large")

    with colL:
        st.subheader(f"📈 {room} — {selected_detector} Trend")
        period = st.radio(
            "Range", ["Last 10 min", "Last 1 h", "Today", "7 days"],
            horizontal=True, key=f"rng_live_{room}_{selected_detector}"
        )
        now = int(time.time())
        if period == "Last 10 min": start = now - 600
        elif period == "Last 1 h": start = now - 3600
        elif period == "Today": start = int(pd.Timestamp("today").replace(hour=0, minute=0).timestamp())
        else: start = now - 7*86400

        df = history.fetch_series(room, selected_detector, start, now)
        if df.empty:
            st.info("No data available.")
        else:
            # projection
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
                    x=alt.X("t:T"),
                    y=alt.Y("value:Q"),
                    strokeDash=alt.condition(alt.datum.kind=="Projected", alt.value([4,4]), alt.value([0,0])),
                    tooltip=[alt.Tooltip("t:T"), alt.Tooltip("value:Q", format=".2f"), "kind:N"],
                    color=alt.Color("kind:N", scale=alt.Scale(range=[gas_color, gas_color]), legend=None),
                )
            )
            layers = [base_chart]
            if thr:
                warn_rule = alt.Chart(pd.DataFrame({"y":[thr["warn"]]})).mark_rule(stroke="#f59e0b")
                alarm_rule = alt.Chart(pd.DataFrame({"y":[thr["alarm"]]})).mark_rule(stroke="#ef4444")
                layers += [warn_rule, alarm_rule]
            st.altair_chart(alt.layer(*layers), use_container_width=True)

            latest = float(df["value"].iloc[-1])
            status, msg = _status_for(selected_detector, latest)
            st.markdown(f"**Current status:** {status}")
            st.caption(msg)
            if rec := HONEYWELL_REC.get(selected_detector):
                st.markdown(f"**Recommended hardware:** {rec}")

    with colR:
        st.subheader("🤖 AI Safety Assistant (Live)")
        if q := st.chat_input("Ask about thresholds or actions…", key=f"chat_live_{room}"):
            st.chat_message("user").write(q)
            now = int(time.time())
            dfq = history.fetch_series(room, selected_detector, now-3600, now)
            latest = float(dfq["value"].iloc[-1]) if not dfq.empty else None
            thr = THRESHOLDS.get(selected_detector, {})
            status = "OK"
            if latest is not None and thr:
                status, _ = _status_for(selected_detector, latest)
            ans = ai.ask_ai(
                q,
                context={
                    "room": room,
                    "gas": selected_detector,
                    "value": latest,
                    "status": status,
                    "thresholds": thr,
                    "simulate": simulate,
                    "recent_series": dfq["value"].tail(60).tolist() if not dfq.empty else [],
                    "mean": history.stats(room, selected_detector, 24)[0],
                    "std": history.stats(room, selected_detector, 24)[1],
                },
                force_rule=ai_force_rule
            )
            st.chat_message("ai").write(ans)

# ======================================================
# Facility snapshot + export
# ======================================================
def build_facility_snapshot() -> dict:
    snapshot = {}
    for room, dets in DETECTORS.items():
        node = {}
        for d in dets:
            label = d["label"]
            val = history.latest_value(room, label)
            if val is None:
                continue
            status, _ = _status_for(label, val)
            node[label] = {
                "value": float(val),
                "status": status,
                "thresholds": THRESHOLDS.get(label, {})
            }
        snapshot[room] = node
    return snapshot

def export_incident_html(logs: dict, brand: dict | None = None) -> str:
    navy = brand.get("navy", "#0a2342") if brand else "#0a2342"
    red = brand.get("red", "#d81f26") if brand else "#d81f26"
    parts = [f"""
    <html>
      <head>
        <meta charset="utf-8"><title>OBW Incident Log</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 20px; background:#fff; }}
          h1 {{ color:{navy}; }} h2 {{ color:{red}; }}
          .entry {{ margin:8px 0; padding:6px 10px; border-left:4px solid {red}; background:#f9f9f9; }}
          .ts {{ font-size:0.85em; color:#666; }}
        </style>
      </head>
      <body>
        <h1>OBW — Incident Log</h1>
    """]
    for rm, entries in logs.items():
        if not entries:
            continue
        parts.append(f"<h2>{rm}</h2>")
        for e in entries:
            parts.append(f"<div class='entry'><span class='ts'>{ts_str(e['ts'])}</span><br/>{e['text']}</div>")
    parts.append("</body></html>")
    return "\n".join(parts)






















        



