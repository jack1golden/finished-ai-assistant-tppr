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

# ---------- detectors (final placements) ----------
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

# Honeywell recommended detectors (simple mapping for demo)
HONEYWELL_REC = {
    "NH₃": "Honeywell Sensepoint XCD (NH₃) or XNX + EC‑Tox (NH₃)",
    "CO": "Honeywell Sensepoint XCD (CO) or XNX + EC‑Tox (CO)",
    "O₂": "Honeywell Sensepoint XCD (O₂) or XNX + EC‑O₂",
    "H₂S": "Honeywell Sensepoint XCD (H₂S) or XNX + EC‑Tox (H₂S)",
    "Ethanol": "Honeywell Sensepoint XCD (VOC) or XNX + PID",
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
# Overview with hotspots (iframe-safe & bridge click)
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
        hotspots_html.append(
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
    tags = "\n".join(hotspots_html)

    html = f"""
    <div class="strip" style="display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 10px 0;">{chips}</div>
    <div class="wrap" style="
      position:relative; width:min(1280px,96%); margin:8px auto;
      border:2px solid #0a2342; border-radius:12px; overflow:hidden;
      box-shadow:0 18px 60px rgba(0,0,0,.20); background:#fff;">
      <style>
        .hotspot:hover {{ background:rgba(16,185,129,.32) !important; }}
        .chip {{ display:inline-block; color:#0b1220; font-weight:800; padding:6px 10px;
                 border-radius:999px; box-shadow:0 1px 6px rgba(0,0,0,.2); }}
      </style>
      <img src="{_img64(ov_path)}" alt="overview" style="display:block; width:100%; height:auto;" />
      {tags}
      <div style="position:absolute; right:10px; bottom:8px; color:#d81f26; font-weight:700; background:#fff9; padding:2px 6px; border-radius:6px; border:1px solid #0a2342;">
        OBW Technologies
      </div>
    </div>
    """
    components.html(html, height=820, scrolling=False)

# ======================================================
# Room view — image + badges + gas cloud/shutter + charts + AI + logs
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

    # Detector pins: real href + bridge (no return false)
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

    # Operator one-shot triggers
    ops = ops or {}
    auto_cloud = "true" if simulate else "false"
    cloud_color = GAS_COLORS.get(selected_detector or (dets[0]["label"] if dets else "CO"), "#38bdf8")

    with colL:
        room_html = f"""
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
        components.html(room_html, height=720, scrolling=False)

    # RIGHT: timeline + predictive chart + AI + logs
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
                key = _sim_key(room, selected_detector)
                last_status = st.session_state.setdefault("last_status", {}).get(key)
                if last_status != status:
                    st.session_state["last_status"][key] = status
                    mean, sd = history.stats(room, selected_detector, window_hours=24)
                    crossing = None
                    if thr:
                        if thr["mode"] == "high" and latest >= thr["warn"]:
                            crossing = 0 if latest >= thr["alarm"] else int(
                                max(1, round((thr["alarm"] - latest) / max(slope, 1e-3)))
                            )
                        elif thr["mode"] == "low" and latest <= thr["warn"]:
                            crossing = 0 if latest <= thr["alarm"] else int(
                                max(1, round((latest - thr["alarm"]) / max(-slope, 1e-3)))
                            )

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
                            "recent_series": df["value"].tail(60).tolist(),
                            "mean": mean,
                            "std": sd,
                            "projection_minutes": crossing
                        },
                        force_rule=ai_force_rule
                    )
                    log = st.session_state.setdefault("ai_log", {}).setdefault(room, [])
                    log.append({"ts": int(time.time()), "text": answer})

            # Manual tick helpers for demo
            cc1, cc2, cc3 = st.columns(3)
            if selected_detector:
                if cc1.button("Add 5s", key=f"add5_{room}_{selected_detector}"):
                    _add_points(room, selected_detector, 5); st.rerun()
                if cc2.button("Add 15s", key=f"add15_{room}_{selected_detector}"):
                    _add_points(room, selected_detector, 15); st.rerun()
                if cc3.button("Spike (overlay)", key=f"spike_{room}_{selected_detector}"):
                    now_ts = int(time.time())
                    history.inject_spike(room, selected_detector, when_ts=now_ts, duration_min=5, magnitude=5.0)
                    _add_points(room, selected_detector, 5)
                    thr = THRESHOLDS.get(selected_detector, {})
                    mean, sd = history.stats(room, selected_detector, window_hours=24)
                    answer = ai.ask_ai(
                        "Detected spike injected for demo. Summarize recommended immediate actions (3 bullets).",
                        context={
                            "room": room,
                            "gas": selected_detector,
                            "value": None,
                            "status": "WARN",
                            "thresholds": thr,
                            "simulate": True,
                            "mean": mean,
                            "std": sd
                        },
                        force_rule=ai_force_rule
                    )
                    log = st.session_state.setdefault("ai_log", {}).setdefault(room, [])
                    log.append({"ts": int(time.time()), "text": answer})
                    st.rerun()
        else:
            st.info("Click a detector badge on the image (or use the selector above) to view its trend.")

        st.divider()
        st.subheader("🤖 AI Safety Assistant")
        if selected_detector:
            if p := st.chat_input("Ask about leaks, thresholds or actions…", key=f"chat_{room}"):
                st.chat_message("user").write(p)
                now = int(time.time())
                df = history.fetch_series(room, selected_detector, now-3600, now)
                latest = float(df["value"].iloc[-1]) if not df.empty else None
                thr = THRESHOLDS.get(selected_detector, {})
                status = "OK"
                if latest is not None and thr:
                    status, _ = _status_for(selected_detector, latest)

                answer = ai.ask_ai(
                    p,
                    context={
                        "room": room,
                        "gas": selected_detector,
                        "value": latest,
                        "status": status,
                        "thresholds": thr,
                        "simulate": simulate,
                        "recent_series": df["value"].tail(60).tolist() if not df.empty else [],
                        "mean": history.stats(room, selected_detector, 24)[0],
                        "std": history.stats(room, selected_detector, 24)[1],
                    },
                    force_rule=ai_force_rule
                )
                st.chat_message("ai").write(answer)

        # Log operator actions
        if ops:
            action_txts = []
            if ops.get("ack"):
                action_txts.append("Operator acknowledged alarm.")
            if ops.get("close_shutter"):
                action_txts.append("Operator commanded shutters to close.")
            if ops.get("ventilate"):
                action_txts.append("Operator increased ventilation.")
            if ops.get("reset"):
                action_txts.append("Operator reset detector.")
            if action_txts:
                log = st.session_state.setdefault("ai_log", {}).setdefault(room, [])
                log.append({"ts": int(time.time()), "text": " ".join(action_txts)})

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

    html_parts = [f"""
    <html>
      <head>
        <meta charset="utf-8">
        <title>OBW Incident Log</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 20px; background:#fff; }}
          h1 {{ color:{navy}; }}
          .entry {{ margin:8px 0; padding:6px 10px; border-left:4px solid {red}; background:#f9f9f9; }}
          .room {{ font-weight: bold; color:{navy}; }}
          .ts {{ font-size:0.85em; color:#666; }}
        </style>
      </head>
      <body>
        <h1>OBW — Incident Log</h1>
    """]
    for room, entries in logs.items():
        if not entries:
            continue
        html_parts.append(f"<h2 style='color:{red}'>{room}</h2>")
        for e in entries:
            tstr = ts_str(e["ts"])
            html_parts.append(
                f"<div class='entry'><span class='ts'>{tstr}</span><br/>{e['text']}</div>"
            )
    html_parts.append("</body></html>")
    return "\n".join(html_parts)




















        



