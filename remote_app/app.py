"""
app.py
Flask web remote for the LED strip (IR) and Roku TV (network ECP, or IR as a fallback).

Run:
    python3 app.py
Then open http://<pi-ip-address>:5000 on your phone.
"""

import urllib.request
import urllib.error

from flask import Flask, jsonify, render_template

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
}

app = Flask(__name__)


def roku_ecp(key):
    """Send a keypress to the Roku over the network."""
    url = f"http://{ROKU_IP}:8060/keypress/{key}"
    req = urllib.request.Request(url, data=b"", method="POST")
    urllib.request.urlopen(req, timeout=3)


@app.route("/")
def index():
    return render_template(
        "index.html",
        led_buttons=list(ir_remote.LED_CODES),
        tv_mode="Wi-Fi" if ROKU_IP else "IR",
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
        if ROKU_IP:
            key = ROKU_ECP_KEYS.get(button)
            if key is None:
                return jsonify(ok=False, error=f"Unknown TV button '{button}'"), 400
            roku_ecp(key)
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


if __name__ == "__main__":
    # 0.0.0.0 makes it reachable from other devices on your network.
    # Don't port-forward this. Reach it from outside your home over WireGuard.
    app.run(host="0.0.0.0", port=5000)
