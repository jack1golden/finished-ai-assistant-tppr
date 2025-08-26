# utils/history.py
from __future__ import annotations
import math, random, time
from typing import Dict, Tuple
import numpy as np
import pandas as pd
import streamlit as st

# Internal store in session:
# st.session_state["hist"] = {(room, label): DataFrame[t, value]}

DEFAULT_BASE = {"NH₃": 20.0, "CO": 12.0, "O₂": 20.8, "H₂S": 1.5, "Ethanol": 260.0}
DEFAULT_UNIT = {"NH₃": "ppm", "CO": "ppm", "O₂": "%", "H₂S": "ppm", "Ethanol": "ppm"}

def _key(room: str, label: str) -> Tuple[str, str]:
    return (room, label)

def init_if_needed(DETECTORS: Dict[str, list], days: int = 60, spikes_per_week: int = 1):
    if "hist" in st.session_state and st.session_state.get("hist_days") == days:
        return
    st.session_state["hist"] = {}
    st.session_state["hist_days"] = days

    # Use 5-min resolution (288 pts/day) to keep memory reasonable
    now = pd.Timestamp.utcnow().floor("min")
    start = now - pd.Timedelta(days=days)
    time_index = pd.date_range(start, now, freq="5min")

    for room, dets in DETECTORS.items():
        for d in dets:
            label = d["label"]
            base = DEFAULT_BASE.get(label, 10.0)

            # smooth baseline with small noise
            n = len(time_index)
            wave = 0.5 * np.sin(np.linspace(0, 8*np.pi, n))
            noise = np.random.normal(0, 0.25, size=n)
            series = base + wave + noise

            # add weekly spikes (~1 hour Gaussian) * spikes_per_week
            weeks = max(1, days // 7)
            spike_count = max(1, weeks * max(1, spikes_per_week))
            spike_centers = np.random.choice(np.arange(60, n-60), size=spike_count, replace=False)
            for c in spike_centers:
                width = 6  # ~30 minutes each side at 5-min step
                height = {
                    "NH₃": 15, "CO": 25, "O₂": -3.0, "H₂S": 8, "Ethanol": 180
                }.get(label, 10)
                for k in range(-width, width+1):
                    idx = c + k
                    if 0 <= idx < n:
                        # Gaussian bump
                        series[idx] += height * math.exp(-(k*k)/(2*(width/2.2)**2))

            df = pd.DataFrame({"t": time_index, "value": series})
            st.session_state["hist"][_key(room, label)] = df

def fetch_series(room: str, label: str, start_ts: int, end_ts: int) -> pd.DataFrame:
    df = st.session_state.get("hist", {}).get(_key(room, label))
    if df is None or df.empty:
        return pd.DataFrame(columns=["t","value"])
    s = pd.to_datetime(start_ts, unit="s", utc=True)
    e = pd.to_datetime(end_ts, unit="s", utc=True)
    out = df[(df["t"] >= s) & (df["t"] <= e)].copy()
    return out.reset_index(drop=True)

def latest_value(room: str, label: str):
    df = st.session_state.get("hist", {}).get(_key(room, label))
    if df is None or df.empty:
        return None
    return float(df["value"].iloc[-1])

def stats(room: str, label: str, hours: int = 24) -> tuple[float, float]:
    df = st.session_state.get("hist", {}).get(_key(room, label))
    if df is None or df.empty:
        return (float("nan"), float("nan"))
    end = df["t"].iloc[-1]
    start = end - pd.Timedelta(hours=hours)
    sl = df[(df["t"] >= start) & (df["t"] <= end)]["value"]
    return (float(sl.mean()), float(sl.std(ddof=0)))

def anomalies(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["t","value"])
    s = df["value"].astype(float).copy()
    roll = s.rolling(12, min_periods=12)  # ~1 hour window (5-min step)
    mu = roll.mean()
    sd = roll.std().replace(0, np.nan)
    z = (s - mu) / sd
    mask = z.abs() >= 3.0
    out = df[mask].copy()
    return out[["t","value"]]

def project_linear(df: pd.DataFrame, minutes: int = 5) -> pd.DataFrame:
    if df is None or df.empty or len(df) < 3:
        return pd.DataFrame(columns=["t","value"])
    # take last 12 points (~1h) for trend
    tail = df.tail(12)
    x = (tail["t"].astype("int64")//10**9 - int(tail["t"].iloc[0].timestamp()))/60.0
    y = tail["value"].to_numpy()
    if len(np.unique(x)) < 2:
        return pd.DataFrame(columns=["t","value"])
    m, b = np.polyfit(x, y, 1)
    last_t = tail["t"].iloc[-1]
    last_x = (last_t.value//10**9 - int(tail["t"].iloc[0].timestamp()))/60.0
    ts = [last_t + pd.Timedelta(minutes=i) for i in range(1, minutes+1)]
    xs = [last_x + i for i in range(1, minutes+1)]
    vs = [m*x + b for x in xs]
    return pd.DataFrame({"t": ts, "value": vs})

def apply_runtime_ops(df: pd.DataFrame, room: str, label: str, simulate: bool, ops: dict) -> pd.DataFrame:
    """Apply real-time visual behaviours on top of historical baseline:
       - simulate leak grows last ~20 min
       - ventilation reduces last ~10 min
       - shutters mildly limit growth (visual analogue)
    """
    if df is None or df.empty:
        return df
    out = df.copy()
    # operate on last 20 samples (~100 min if 5-min step; still OK for demo)
    # if you want "live-looking", tweak to finer window
    tail = out.tail(20).copy()
    idx = tail.index

    if simulate:
        # additive growth curve
        grow = np.linspace(0, 1.0, len(tail))
        mag = {"NH₃": 10, "CO": 15, "O₂": -1.5, "H₂S": 6, "Ethanol": 120}.get(label, 8)
        tail["value"] = tail["value"] + mag * grow

    if ops.get("close_shutter"):
        # reduce growth (limit) in last samples
        damp = np.linspace(0.9, 0.7, len(tail))
        tail["value"] = tail["value"] * damp

    if ops.get("ventilate"):
        # linearly pull readings toward baseline of this detector
        base = DEFAULT_BASE.get(label, float(tail["value"].median()))
        pull = np.linspace(0.0, 1.0, len(tail))
        tail["value"] = tail["value"]*(1 - 0.6*pull) + base*(0.6*pull)

    if ops.get("reset"):
        base = DEFAULT_BASE.get(label, float(tail["value"].median()))
        tail["value"] = tail["value"]*0.2 + base*0.8

    out.loc[idx, "value"] = tail["value"]
    return out

