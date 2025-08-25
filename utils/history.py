# utils/history.py
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

HERE = Path(__file__).parent.resolve()
DATA_DIR = HERE.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB = DATA_DIR / "history.db"

@dataclass
class Detector:
    room: str
    label: str  # gas symbol like 'NH₃', 'CO', 'O₂'

def det_key(room: str, label: str) -> str:
    return f"{room}::{label}"

def _connect():
    return sqlite3.connect(DB)

def init_if_needed(detectors: Dict[str, List[Dict]] , days:int = 7):
    with _connect() as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                det_key TEXT NOT NULL,
                ts INTEGER NOT NULL,
                val REAL NOT NULL,
                PRIMARY KEY(det_key, ts)
            )
        """)
        con.commit()

        # If DB is nearly empty, seed with synthetic history
        cur.execute("SELECT COUNT(*) FROM readings")
        n = cur.fetchone()[0]
        if n > 1000:
            return  # already seeded

        now = int(time.time())
        start = now - days*24*3600
        idx = pd.date_range(pd.to_datetime(start, unit="s"),
                            pd.to_datetime(now, unit="s"),
                            freq="1min")
        # Seed each detector with a realistic baseline pattern
        for room, dets in detectors.items():
            for d in dets:
                label = d["label"]
                base = _baseline_for(label)
                vals = _make_series(idx.size, base, label)
                rows = [(det_key(room, label), int(ts.value/1e9), float(v)) for ts, v in zip(idx, vals)]
                cur.executemany("INSERT OR IGNORE INTO readings(det_key, ts, val) VALUES (?, ?, ?)", rows)
        con.commit()

def _baseline_for(label: str) -> float:
    lbl = label.upper()
    if "O₂" in label or "O2" in label:
        return 20.8
    if "CO" in lbl and "CO₂" not in lbl:
        return 8.0
    if "H₂S" in lbl or "H2S" in lbl:
        return 1.5
    if "NH₃" in lbl or "NH3" in lbl:
        return 6.0
    if "ETHANOL" in lbl:
        return 280.0
    return 5.0

def _make_series(n: int, base: float, label: str) -> np.ndarray:
    t = np.arange(n)
    day = 1440.0
    circ = np.sin(2*np.pi*(t % day)/day)  # daily cycle
    noise = np.random.normal(0, 0.4 if base < 50 else 3.0, size=n)
    trend = 0.0002 * t  # tiny drift
    vals = base + (0.1*base if base<50 else 0.05*base) * 0.15*circ + trend + noise
    if "O₂" in label or "O2" in label:
        vals = np.clip(vals, 17.0, 21.0)
    else:
        vals = np.clip(vals, 0, None)
    return vals

def fetch_series(room: str, label: str, start_ts: int, end_ts: int) -> pd.DataFrame:
    k = det_key(room, label)
    with _connect() as con:
        df = pd.read_sql_query(
            "SELECT ts, val FROM readings WHERE det_key=? AND ts BETWEEN ? AND ? ORDER BY ts ASC",
            con, params=(k, start_ts, end_ts)
        )
    if df.empty:
        return pd.DataFrame(columns=["t","value"])
    df["t"] = pd.to_datetime(df["ts"], unit="s")
    df.rename(columns={"val":"value"}, inplace=True)
    return df[["t","value"]]

def latest_value(room: str, label: str) -> float | None:
    k = det_key(room, label)
    with _connect() as con:
        cur = con.cursor()
        cur.execute("SELECT val FROM readings WHERE det_key=? ORDER BY ts DESC LIMIT 1", (k,))
        row = cur.fetchone()
        return float(row[0]) if row else None

def inject_spike(room: str, label: str, when_ts: int, duration_min: int = 10, magnitude: float = 5.0):
    """Adds a positive spike segment into history (quick demo helper)."""
    k = det_key(room, label)
    with _connect() as con:
        cur = con.cursor()
        for i in range(duration_min):
            cur.execute("UPDATE readings SET val = val + ? WHERE det_key=? AND ts=?", (magnitude, k, when_ts + i*60))
        con.commit()

def stats(room: str, label: str, window_hours: int = 24) -> Tuple[float, float]:
    now = int(time.time())
    start = now - window_hours*3600
    df = fetch_series(room, label, start, now)
    if df.empty:
        return (0.0, 1.0)
    return float(df["value"].mean()), float(df["value"].std(ddof=1) if len(df)>=2 else 1.0)
