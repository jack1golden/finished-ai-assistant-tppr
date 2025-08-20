import streamlit as st
import streamlit.components.v1 as components
import random
import time
import matplotlib.pyplot as plt
import numpy as np

# Paths
OVERVIEW_IMAGE = "images/Overview.png"
ROOM_IMAGES = {
    "Room 1": "images/Room 1.png",
    "Room 2": "images/Room 2 (1).png",
    "Room 3": "images/Room 3 (1).png",
    "Room 4": "images/Room Production.png",
    "Room 5": "images/Room Production 2.png",
    "Room 6": "images/Room 12 17.png",
}

# Hardcoded detector positions per room (percent-based)
DETECTORS = {
    "Room 1": [{"label": "NH₃", "x": 35, "y": 35}],
    "Room 2": [{"label": "O₂", "x": 75, "y": 20}],
    "Room 3": [{"label": "CH₄", "x": 40, "y": 60}],
    "Room 4": [{"label": "CO₂", "x": 50, "y": 30}],
    "Room 5": [{"label": "H₂S", "x": 60, "y": 70}],
    "Room 6": [{"label": "VOC", "x": 25, "y": 50}],
}

# ------------------------------
# Render Overview
# ------------------------------
def render_overview():
    st.title("🏭 Facility Overview")

    html = f"""
    <style>
    .map {{
        position: relative;
        display: inline-block;
    }}
    .map img {{
        max-width: 100%;
        height: auto;
        border: 2px solid #444;
        border-radius: 10px;
    }}
    .hotspot {{
        position: absolute;
        border: 2px solid green;
        border-radius: 8px;
        background-color: rgba(0, 200, 0, 0.3);
        color: white;
        font-weight: bold;
        text-align: center;
        padding: 2px;
        cursor: pointer;
    }}
    </style>

    <div class="map">
      <img src="{OVERVIEW_IMAGE}" />

      <!-- Hardcoded hotspots -->
      <a class="hotspot" href="?room=Room%201" style="left:15%;top:30%;width:12%;height:15%;">Room 1</a>
      <a class="hotspot" href="?room=Room%202" style="left:40%;top:30%;width:12%;height:15%;">Room 2</a>
      <a class="hotspot" href="?room=Room%203" style="left:65%;top:30%;width:12%;height:15%;">Room 3</a>
      <a class="hotspot" href="?room=Room%204" style="left:20%;top:65%;width:12%;height:15%;">Room 4</a>
      <a class="hotspot" href="?room=Room%205" style="left:50%;top:65%;width:12%;height:15%;">Room 5</a>
      <a class="hotspot" href="?room=Room%206" style="left:75%;top:65%;width:12%;height:15%;">Room 6</a>
    </div>
    """
    components.html(html, height=600)

# ------------------------------
# Render Room
# ------------------------------
def render_room(room, detector=None):
    st.title(f"🚪 {room}")

    img = ROOM_IMAGES[room]
    html = f"""
    <style>
    .room {{
        position: relative;
        display: inline-block;
    }}
    .room img {{
        max-width: 100%;
        height: auto;
        border: 2px solid #444;
        border-radius: 10px;
    }}
    .detector {{
        position: absolute;
        border: 2px solid green;
        border-radius: 50%;
        background-color: rgba(0,200,0,0.5);
        color: white;
        font-weight: bold;
        text-align: center;
        width: 40px;
        height: 40px;
        line-height: 40px;
        cursor: pointer;
    }}
    </style>

    <div class="room">
      <img src="{img}" />
    """

    for det in DETECTORS[room]:
        html += f"""
        <a class="detector" href="?room={room.replace(" ", "%20")}&det={det['label']}"
           style="left:{det['x']}%;top:{det['y']}%;">{det['label']}</a>
        """

    html += "</div>"
    components.html(html, height=600)

    # Show detector chart if selected
    if detector:
        st.subheader(f"📈 Live Data: {detector}")
        render_live_chart(detector)

    if st.button("⬅️ Back to Overview", key=f"back_{room}"):
        st.session_state["current_room"] = None
        st.session_state["current_detector"] = None


# ------------------------------
# Fake Live Chart
# ------------------------------
def render_live_chart(label):
    x = np.arange(0, 50)
    y = np.cumsum(np.random.randn(50)) + 50

    fig, ax = plt.subplots()
    ax.plot(x, y, label=label)
    ax.set_title(f"Live {label} Readings")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Concentration (ppm)")
    ax.legend()
    st.pyplot(fig)



        



