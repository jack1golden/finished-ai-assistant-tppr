import streamlit as st
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from utils import facility

# -----------------------------
# App config
# -----------------------------
st.set_page_config(page_title="Pharma Safety HMI — AI First", layout="wide")
HERE = Path(__file__).parent
IMAGES = HERE / "images"
IMAGES.mkdir(exist_ok=True)

# -----------------------------
# Session init
# -----------------------------
st.session_state.setdefault("nav_tab", "Home")
st.session_state.setdefault("simulate_by_room", {})   # e.g. {"Room 1": True}
st.session_state.setdefault("current_detector", None)

# -----------------------------
# Generate a simple digital logo (once)
# -----------------------------
def ensure_logo(path: Path):
    if path.exists():
        return
    W, H = 900, 300
    img = Image.new("RGBA", (W, H), (10, 16, 26, 0))
    d = ImageDraw.Draw(img)

    # Panels/icons (minimal, clean)
    # Device
    d.rounded_rectangle((40, 60, 180, 240), 18, outline=(80,200,255), width=6)
    d.rectangle((70, 110, 150, 140), outline=(80,200,255), width=4)
    # Dots to head
    for i in range(6):
        d.ellipse((200 + i*22 - 4, 148 - 4, 200 + i*22 + 4, 148 + 4), fill=(80,200,255))

    # Head + brain
    d.ellipse((350, 90, 430, 170), outline=(80,200,255), width=6)
    d.ellipse((370, 110, 410, 150), outline=(80,200,255), width=3)
    # Shield
    d.polygon([(450,200),(490,180),(530,200),(530,240),(490,260),(450,240)], outline=(80,200,255), width=6)

    # Checklist
    d.rounded_rectangle((640, 70, 780, 210), 14, outline=(80,200,255), width=6)
    for i,y in enumerate([95,130,165]):
        d.line((655,y,720,y), fill=(80,200,255), width=4)

    # Clock
    d.ellipse((800, 185, 870, 255), outline=(80,200,255), width=6)
    d.line((835,220,860,220), fill=(80,200,255), width=4)
    d.line((835,220,835,200), fill=(80,200,255), width=4)

    # Skyline + leaf
    d.line((60,280,320,280), fill=(80,200,255), width=4)
    d.rectangle((90,235,110,280), outline=(80,200,255), width=4)
    d.rectangle((120,250,140,280), outline=(80,200,255), width=4)
    d.rectangle((150,220,170,280), outline=(80,200,255), width=4)
    d.polygon([(300,270),(320,250),(330,265)], outline=(80,200,255), width=4)

    # Title text
    try:
        fnt = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
    except:
        fnt = None
    d.text((40, 15), "Pharma Safety HMI — Innovation Project", fill=(200,230,255), font=fnt)

    img.convert("RGBA").save(path)

ensure_logo(IMAGES / "logo_auto.png")

# -----------------------------
# Sidebar Navigation
# -----------------------------
tabs = ["Home", "Overview",
        "Room 1", "Room 2", "Room 3", "Room 12 17", "Room Production", "Room Production 2",
        "Settings", "AI Safety Assistant"]
st.session_state["nav_tab"] = st.sidebar.radio("🔎 Navigation", tabs, index=tabs.index(st.session_state["nav_tab"]), key="nav_tabs_radio")

# -----------------------------
# Render Pages
# -----------------------------
tab = st.session_state["nav_tab"]

if tab == "Home":
    colL, colR = st.columns([2,1])
    with colL:
        st.image(str(IMAGES / "logo_auto.png"), use_container_width=True)
        st.markdown("### Facility Simulation & AI Safety Assistant")
        st.write("A pitch-ready 2.5D facility HMI demo with clickable rooms, detectors, "
                 "animated gas clouds, shutter actions, and an AI safety panel.")
        if st.button("Enter Simulation → Overview", key="enter_overview"):
            st.session_state["nav_tab"] = "Overview"
            st.rerun()
    with colR:
        st.info("Upload a polished logo later as `images/logo.png` to replace this auto-rendered one.")

elif tab == "Overview":
    st.title("🏭 Facility Overview")
    facility.render_overview(IMAGES)

elif tab in ["Room 1", "Room 2", "Room 3", "Room 12 17", "Room Production", "Room Production 2"]:
    room = tab
    st.title(f"🚪 {room}")
    simulate_flag = st.session_state["simulate_by_room"].get(room, False)

    # Controls row
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        if st.button("💨 Simulate Gas Leak", key=f"sim_{room}"):
            st.session_state["simulate_by_room"][room] = True
            st.rerun()
    with c2:
        if st.button("⏹ Reset Simulation", key=f"reset_{room}"):
            st.session_state["simulate_by_room"][room] = False
            st.rerun()
    with c3:
        if st.button("⬅️ Back to Overview", key=f"back_{room}"):
            st.session_state["nav_tab"] = "Overview"
            st.session_state["current_detector"] = None
            st.rerun()

    # Room view (image + detector pins + optional animation)
    facility.render_room(IMAGES, room, simulate=simulate_flag)

    # Detector selection (when clicked)
    det = st.session_state.get("current_detector")
    if det:
        st.subheader(f"📟 Detector Selected: {det}")
        st.caption("Live trend + AI advisory will appear here (placeholder).")
        st.line_chart({"reading": [0.2, 0.28, 0.35, 0.33, 0.4, 0.95, 0.6]})

elif tab == "Settings":
    st.title("⚙️ Settings")
    st.write("Thresholds, units, and other configuration go here.")

elif tab == "AI Safety Assistant":
    st.title("🤖 AI Safety Assistant")
    st.chat_message("ai").write("Hi, I’m your safety AI. Ask me about leaks, thresholds, or best actions.")
    if prompt := st.chat_input("Ask the AI Safety Assistant…"):
        st.chat_message("user").write(prompt)
        # Fake AI response
        st.chat_message("ai").write("Recommendation: close shutters in all rooms; increase extraction in Production areas; verify detector calibrations.")


