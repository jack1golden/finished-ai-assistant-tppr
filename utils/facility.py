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
    "NH₃": "Honeywell Sensepoint XCD (NH₃) or XNX + EC-Tox (NH₃)",
    "CO": "Honeywell Sensepoint XCD (CO) or XNX + EC-Tox (CO)",
    "O₂": "Honeywell Sensepoint XCD (O₂) or XNX + EC-O₂",
    "H₂S": "Honeywell Sensepoint XCD (H₂S) or XNX + EC-Tox (H₂S)",
    "Ethanol": "Honeywell Sensepoint XCD (VOC) or XNX + PID",
}

# ---------- live series sim ----------
def _sim_key(room: str, label: str) -> str:
    return f"{room}::{label}"

def _status_for(label: str, value: float) -> tuple[str, str]:
    thr = THRESHOLDS.get(label)
    if not thr:
        return "OK", "Monitoring normal conditions."
    mode = thr["mode"]
    if mode == "low":
        if value <= thr["alarm"]:
            return "ALARM", f"{label} critically low ({value:.2f}{thr['units']})."
        if value <= thr["warn"]:
            return "WARN", f"{label} trending low ({value:.2f}{thr['units']})."
        return "OK", f"{label} normal ({value:.2f}{thr['units']})."
    else:
        if value >= thr["alarm"]:
            return "ALARM", f"{label} high ({value:.2f}{thr['units']})."
        if value >= thr["warn"]:
            return "WARN", f"{label} elevated ({value:.2f}{thr['units']})."
        return "OK", f"{label} normal ({value:.2f}{thr['units']})."

# ---------- initialize history ----------
history.init_if_needed(DETECTORS, days=7)

# ======================================================
# Overview (with hotspots)
# ======================================================
def render_overview(images_dir: Path):
    ov_path = _find_first(images_dir, OVERVIEW_CANDS)
    if not ov_path:
        st.error("Overview image not found in /images.")
        return
    html = f"<img src='{_img64(ov_path)}' style='width:100%;'/>"
    components.html(html, height=820, scrolling=False)

# ======================================================
# Room rendering
# ======================================================
def render_room(images_dir: Path, room: str, simulate=False, selected_detector=None,
                ai_force_rule=False, ops=None, brand=None):
    st.write(f"### {room}")
    if not selected_detector:
        st.info("Select a detector to see details.")
        return
    now = int(time.time())
    start = now - 600
    df = history.fetch_series(room, selected_detector, start, now)
    if df.empty:
        st.warning("No data.")
        return
    gas_color = GAS_COLORS.get(selected_detector, "#38bdf8")
    thr = THRESHOLDS.get(selected_detector, {})
    chart = alt.Chart(df).mark_line(color=gas_color).encode(
        x="t:T", y="value:Q", tooltip=["t:T", "value:Q"]
    )
    st.altair_chart(chart, use_container_width=True)
    latest = float(df["value"].iloc[-1])
    status, msg = _status_for(selected_detector, latest)
    st.write(f"**Status:** {status} — {msg}")
    if rec := HONEYWELL_REC.get(selected_detector):
        st.caption(f"Recommended Honeywell hardware: {rec}")

# ======================================================
# Live Data rendering (new tab)
# ======================================================
def render_live_only(images_dir: Path, room: str, selected_detector: str,
                     simulate=False, ai_force_rule=False, ops=None, brand=None):
    colL, colR = st.columns([2, 1], gap="large")
    with colL:
        st.subheader(f"📈 {room} — {selected_detector} Trend")
        now = int(time.time())
        start = now - 3600
        df = history.fetch_series(room, selected_detector, start, now)
        if df.empty:
            st.warning("No data.")
        else:
            gas_color = GAS_COLORS.get(selected_detector, "#38bdf8")
            thr = THRESHOLDS.get(selected_detector, {})
            chart = alt.Chart(df).mark_line(color=gas_color).encode(
                x="t:T", y="value:Q", tooltip=["t:T", "value:Q"]
            )
            if thr:
                warn_rule = alt.Chart(pd.DataFrame({"y": [thr["warn"]]})).mark_rule(stroke="#f59e0b")
                alarm_rule = alt.Chart(pd.DataFrame({"y": [thr["alarm"]]})).mark_rule(stroke="#ef4444")
                chart = alt.layer(chart, warn_rule, alarm_rule)
            st.altair_chart(chart, use_container_width=True)
            latest = float(df["value"].iloc[-1])
            status, msg = _status_for(selected_detector, latest)
            st.write(f"**Status:** {status} — {msg}")
            if rec := HONEYWELL_REC.get(selected_detector):
                st.caption(f"Honeywell hardware: {rec}")
    with colR:
        st.subheader("🤖 AI Assistant (Live)")
        if q := st.chat_input("Ask about this detector…", key=f"chat_live_{room}"):
            st.chat_message("user").write(q)
            ans = ai.ask_ai(q, context={"room": room, "gas": selected_detector}, force_rule=ai_force_rule)
            st.chat_message("ai").write(ans)

# ======================================================
# Snapshot / Export
# ======================================================
def build_facility_snapshot() -> dict:
    snapshot = {}
    for room, dets in DETECTORS.items():
        node = {}
        for d in dets:
            label = d["label"]
            val = history.latest_value(room, label)
            if val is None: continue
            status, _ = _status_for(label, val)
            node[label] = {"value": float(val), "status": status,
                           "thresholds": THRESHOLDS.get(label, {})}
        snapshot[room] = node
    return snapshot

def export_incident_html(logs: dict, brand: dict | None = None) -> str:
    navy = brand.get("navy", "#0a2342") if brand else "#0a2342"
    red = brand.get("red", "#d81f26") if brand else "#d81f26"
    html = f"<h1 style='color:{navy}'>OBW — Incident Log</h1>"
    for room, entries in logs.items():
        html += f"<h2 style='color:{red}'>{room}</h2>"
        for e in entries:
            tstr = ts_str(e["ts"])
            html += f"<div>{tstr} — {e['text']}</div>"
    return f"<html><body>{html}</body></html>"





















        



