# utils/history.py
from __future__ import annotations
import math
from typing import Dict, Tuple
import numpy as np
import pandas as pd
import streamlit as st

# st.session_state["hist"][(room,label)] = DataFrame[t, value]
DEFAULT_BASE = {"NH₃": 20.0, "CO": 12.0, "O₂": 20.8, "H₂S": 1.5, "Ethanol": 260.0}

def _key(room: str, label: str) -> Tuple[str, str]:
    return (room, label)

def init_if_needed(DETECTORS: Dict[str, list], days: int = 180, step_minutes: int = 15, spikes_per_week: int = 1):
    if "hist" in st.session_state and st.session_state.get("hist_days") == days and st.session_state.get("hist_step") == step_minutes:
        return
    st.session_state["hist"] = {}
    st.session_state["hist_days"] = days
    st.session_state["hist_step"] = step_minutes

    now = pd.Timestamp.utcnow().floor("min")
    start = now - pd.Timedelta(days=days)
    idx = pd.date_range(start, now, freq=f"{step_minutes}min")
    n = len(idx)
    weeks = max(1, days // 7)
    spike_count = max(1, weeks * max(1, spikes_per_week))

    for room, dets in DETECTORS.items():
        for d in dets:
            label = d["label"]; base = DEFAULT_BASE.get(label, 10.0)
            wave = 0.5 * np.sin(np.linspace(0, 12*np.pi, n))
            noise = np.random.normal(0, 0.2, size=n)
            series = base + wave + noise
            centers = np.random.choice(np.arange(48, n-48), size=spike_count, replace=False)
            for c in centers:
                width = int(60/step_minutes)  # ~1h half-width
                height = {"NH₃": 15, "CO": 25, "O₂": -3.0, "H₂S": 8, "Ethanol": 180}.get(label, 10)
                for k in range(-width, width+1):
                    idxk = c + k
                    if 0 <= idxk < n:
                        series[idxk] += height * math.exp(-(k*k)/(2*(width/2.2)**2))
            df = pd.DataFrame({"t": idx, "value": series})
            st.session_state["hist"][_key(room, label)] = df

def fetch_series(room: str, label: str, start_ts: int, end_ts: int) -> pd.DataFrame:
    df = st.session_state.get("hist", {}).get(_key(room, label))
    if df is None or df.empty: return pd.DataFrame(columns=["t","value"])
    s = pd.to_datetime(start_ts, unit="s", utc=True)
    e = pd.to_datetime(end_ts, unit="s", utc=True)
    out = df[(df["t"] >= s) & (df["t"] <= e)].copy()
    return out.reset_index(drop=True)

def latest_value(room: str, label: str):
    df = st.session_state.get("hist", {}).get(_key(room, label))
    if df is None or df.empty: return None
    return float(df["value"].iloc[-1])

def apply_runtime_ops(df: pd.DataFrame, room: str, label: str, simulate: bool, ops: dict) -> pd.DataFrame:
    if df is None or df.empty: return df
    out = df.copy()
    tail = out.tail(20).copy(); idx = tail.index
    if simulate:
        grow = np.linspace(0, 1.2, len(tail))
        mag = {"NH₃": 10, "CO": 15, "O₂": -1.5, "H₂S": 6, "Ethanol": 120}.get(label, 8)
        tail["value"] = tail["value"] + mag * grow
    if ops and ops.get("close_shutter"):
        damp = np.linspace(0.9, 0.7, len(tail))
        tail["value"] = tail["value"] * damp
    if ops and ops.get("ventilate"):
        base = DEFAULT_BASE.get(label, float(tail["value"].median()))
        pull = np.linspace(0.0, 1.0, len(tail))
        tail["value"] = tail["value"]*(1 - 0.6*pull) + base*(0.6*pull)
    if ops and ops.get("reset"):
        base = DEFAULT_BASE.get(label, float(tail["value"].median()))
        tail["value"] = tail["value"]*0.2 + base*0.8
    out.loc[idx, "value"] = tail["value"]
    return out


