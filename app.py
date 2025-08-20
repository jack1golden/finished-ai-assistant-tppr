import streamlit as st
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from utils import facility

# --------------------------------
# App config
# --------------------------------
st.set_page_config(page_title="Pharma Safety HMI — AI First", layout="wide")
HERE = Path(__file__).parent
IMAGES = (HERE / "images")
IMAGES.mkdir(exist_ok=True)

# --------------------------------
# Session + query params sync
# --------------------------------
st.session_state.setdefault("nav_tab", "Home")
st.session_state.setdefault("simulate_by_room", {})
st.session_state.setdefault("current_detector", None)
st.session_state.setdefault("tuner_enabled", False)  # Position tuner (off by default)

# Read URL like ?room=Room%202&det=O%E2%82%82
qp = st.query_params
if "room" in qp:
    st.session_state["nav_tab"] = qp["room"]
if "det" in qp:
    st.session_state["current_detector"] = qp["det"]

# --------------------------------
# Logo: prefer user image images/logo.png, else auto-generate once
# --------------------------------
USER_LOGO = IMAGES / "logo.png"
AUTO_LOGO = IMAGES / "logo_auto.png"

def ensure_logo_auto(path: Path):
    if path.exists() or USER_LOGO.exists():
        return
    W, H = 900, 300
    img = Image.new("RGBA", (W, H), (10, 16, 26, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((40, 60, 180, 240), 18, outline=(80,200,255), width=6)
    d.rectangle((70, 110, 150, 140), outline=(80,200,255), width=4)
    for i in range(6):
        d.ellipse((200 + i*22 - 4, 148 - 4, 200 + i*22 + 4, 148 + 4), fill=(80,200,255))
    d.ellipse((350, 90, 430, 170), outline=(80,200,255), width=6)
    d.ellipse((370, 110, 410, 150), outline=(80,200,255), width=3)
    try:
        fnt = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
    except:
        fnt = None
    d.text((40, 15), "Pharma Safety HMI — Innovation Project", fill=(200,230,255), font=fnt)
    img.save(path)

def logo_path() -> Path:
    ensure_logo_auto(AUTO_LOGO)
    return USER_LOGO if USER_LOGO.exists() else AUTO_LOGO

# --------------------------------
# Sidebar Navigation
# --------------------------------
tabs = [
    "Home", "Overview",
    "Room 1", "Room 2", "Room 3", "Room 12 17", "Room Production", "Room Production 2",
    "Settings", "AI Safety Assistant"
]
st.session_state["nav_tab"] = st.sidebar.radio(
    "🔎 Navigation", tabs,
    index=tabs.index(st.session_state["nav_tab"]) if st.session_state["nav_tab"] in tabs else 0,
    key="nav_tabs_radio"
)

# --------------------------------
# Render pages
# --------------------------------
tab = st.session_state["nav_tab"]

if tab == "Home":
    colL, colR = st.columns([2, 1])
    with colL:
        st.image(str(logo_path()), use_container_width=True)
        st.markdown("### Facility Simulation & AI Safety Assistant")
        st.write(
            "A pitch-ready 2.5D facility HMI demo with clickable rooms, detector pins, "
            "animated gas clouds, shutters, and an AI safety panel."
        )
        if st.button("Enter Simulation → Overview", key="enter_overview"):
            st.session_state["nav_tab"] = "Overview"
            st.rerun()
    with colR:
        if not USER_LOGO.exists():
            st.info("Using a temporary logo. Place your artwork as **images/logo.png** to override.")

elif tab == "Overview":
    st.title("🏭 Facility Overview")
    facility.render_overview(IMAGES, tuner=st.session_state["tuner_enabled"])

elif tab in ["Room 1", "Room 2", "Room 3", "Room 12 17", "Room Production", "Room Production 2"]:
    room = tab
    st.title(f"🚪 {room}")
    simulate_flag = st.session_state["simulate_by_room"].get(room, False)

    c1, c2, c3 = st.columns([1, 1, 2])
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
            st.query_params.clear()  # clear URL params
            st.rerun()

    facility.render_room(IMAGES, room, simulate=simulate_flag, tuner=st.session_state["tuner_enabled"])

    det = st.session_state.get("current_detector")
    if det:
        st.subheader(f"📟 Detector Selected: {det}")
        st.caption("Live trend + AI advisory (placeholder).")
        st.line_chart({"reading": [0.2, 0.28, 0.35, 0.33, 0.4, 0.95, 0.6]})

elif tab == "Settings":
    st.title("⚙️ Settings")
    st.checkbox("🛠 Enable Position Tuner (drag hotspots & detector pins)", key="tuner_enabled")
    st.caption("When enabled, you can drag boxes/pins. Use the **Copy updated code** button to paste into the file.")

elif tab == "AI Safety Assistant":
    st.title("🤖 AI Safety Assistant")
    st.chat_message("ai").write("Hi, I’m your safety AI. Ask about leaks, thresholds, or actions.")
    if prompt := st.chat_input("Ask the AI Safety Assistant…"):
        st.chat_message("user").write(prompt)
        st.chat_message("ai").write(
            "Recommendation: close shutters in all affected rooms; increase extraction in Production areas; "
            "verify detector calibrations and evacuate if O₂ < 19.5%."
        )

