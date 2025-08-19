import random

RESPONSES = [
    "AI suggests closing shutters in Room 2.",
    "AI recommends evacuation of Room 3.",
    "AI detects elevated CO₂ levels — activate ventilation.",
    "AI suggests monitoring boiler pressure in Production.",
    "AI recommends isolating Room 12/17 to prevent spread.",
]

def fake_ai_response(user_msg: str) -> str:
    return random.choice(RESPONSES)
