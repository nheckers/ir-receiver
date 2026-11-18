"""
app.py
Flask web remote for the LED strip (IR) and Roku TV (network ECP, or IR as a fallback).

Runs behind systemd socket activation (see the systemd/ folder), so it listens
privately on 127.0.0.1:5001 and the proxy handles port 5000.
"""

import urllib.request
import urllib.error

from flask import Flask, Response, jsonify, render_template

import ir_remote

# Set this to your Roku TV's IP (Settings > Network > About) to control it over Wi-Fi.
# Leave it as None to control the TV with IR instead.
ROKU_IP = "192.168.9.180"

# Web button name -> Roku ECP key name
ROKU_ECP_KEYS = {
    "power": "Power",
    "home": "Home",
    "back": "Back",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "ok": "Select",
    "play": "Play",
    "rewind": "Rev",
    "skip": "Fwd",
    "vol_up": "VolumeUp",
    "vol_down": "VolumeDown",
    "mute": "VolumeMute",
    "settings": "Info",  # the Roku API's Info key does the same thing as the IR Settings button
}

# Shortcuts page. IDs come from: curl http://<roku-ip>:8060/query/apps
# Inputs: (label, what's plugged in, Roku app ID)
ROKU_INPUTS = [
    ("HDMI 1", "Computer", "tvinput.hdmi1"),
    ("HDMI 2", "PS5", "tvinput.hdmi2"),
    ("HDMI 3", "Switch", "tvinput.hdmi3"),
]

# Apps: (label, Roku app ID). Add, remove, or reorder these.
ROKU_APPS = [
    ("Netflix", "12"),
    ("YouTube", "837"),
    ("Hulu", "2285"),
    ("Peacock", "593099"),
    ("discovery+", "593290"),
    ("HBO Max", "61322"),
    ("Disney Plus", "291097"),
]

# Only these IDs can be launched or have icons fetched through the app.
ALLOWED_IDS = {i[-1] for i in ROKU_INPUTS + ROKU_APPS}

app = Flask(__name__)


def roku_post(path):
    """Send a POST to the Roku's ECP API, like 'keypress/Home' or 'launch/12'."""
    url = f"http://{ROKU_IP}:8060/{path}"
    req = urllib.request.Request(url, data=b"", method="POST")
    urllib.request.urlopen(req, timeout=3)


@app.route("/")
def index():
    return render_template(
        "index.html",
        led_buttons=list(ir_remote.LED_CODES),
        tv_mode="Wi-Fi" if ROKU_IP else "IR",
        roku_inputs=ROKU_INPUTS,
        roku_apps=ROKU_APPS,
    )


@app.post("/api/led/<button>")
def led(button):
    try:
        code = ir_remote.send("led", button)
        return jsonify(ok=True, sent=f"led {button} ({code})")
    except ValueError as e:
        return jsonify(ok=False, error=str(e)), 400
    except Exception as e:
        return jsonify(ok=False, error=f"IR send failed: {e}"), 500


@app.post("/api/tv/<button>")
def tv(button):
    try:
        # Use Wi-Fi when it's set up and the Roku API has this button.
        # Buttons the API doesn't have (like settings and sleep) go out over IR.
        if ROKU_IP and button in ROKU_ECP_KEYS:
            key = ROKU_ECP_KEYS[button]
            roku_post(f"keypress/{key}")
            return jsonify(ok=True, sent=f"tv {button} (ECP {key})")
        else:
            code = ir_remote.send("roku", button)
            return jsonify(ok=True, sent=f"tv {button} (IR {code})")
    except ValueError as e:
        return jsonify(ok=False, error=str(e)), 400
    except urllib.error.URLError as e:
        return jsonify(ok=False, error=f"Can't reach the Roku: {e.reason}"), 502
    except Exception as e:
        return jsonify(ok=False, error=f"Send failed: {e}"), 500


@app.post("/api/tv/launch/<app_id>")
def tv_launch(app_id):
    if not ROKU_IP:
        return jsonify(ok=False, error="Launching apps needs Wi-Fi mode (set ROKU_IP)"), 400
    if app_id not in ALLOWED_IDS:
        return jsonify(ok=False, error=f"'{app_id}' isn't in your shortcuts"), 400
    try:
        roku_post(f"launch/{app_id}")
        return jsonify(ok=True, sent=f"launch {app_id}")
    except urllib.error.URLError as e:
        return jsonify(ok=False, error=f"Can't reach the Roku: {e.reason}"), 502


@app.get("/api/tv/icon/<app_id>")
def tv_icon(app_id):
    """Pass the app's icon through from the Roku, so the phone only talks to the Pi."""
    if not ROKU_IP or app_id not in ALLOWED_IDS:
        return "", 404
    try:
        with urllib.request.urlopen(f"http://{ROKU_IP}:8060/query/icon/{app_id}", timeout=3) as r:
            return Response(
                r.read(),
                mimetype=r.headers.get("Content-Type", "image/png"),
                headers={"Cache-Control": "public, max-age=604800"},  # cache for a week
            )
    except urllib.error.URLError:
        return "", 502


if __name__ == "__main__":
    # Only reachable from the Pi itself. The systemd proxy on port 5000 handles
    # outside traffic. Don't port-forward this; use WireGuard from outside.
    app.run(host="127.0.0.1", port=5001)
