"""
ir_remote.py
Send IR codes from a Raspberry Pi using ir-ctl.

Usage from the command line:
    python3 ir_remote.py list
    python3 ir_remote.py led red
    python3 ir_remote.py roku up

Usage from other Python code (like a Flask app later):
    from ir_remote import send
    send("led", "red")
"""

import glob
import subprocess
import sys
import time

# Every code uses the Roku address (eac7). The LED strip ignores the
# address, so these work for both devices.
PROTOCOL = "necx"

LED_CODES = {
    "power":       "0xeac745",
    "white":       "0xeac71c",
    "brighter":    "0xeac70c",
    "dimmer":      "0xeac708",
    "red":         "0xeac742",
    "green":       "0xeac752",
    "blue":        "0xeac74a",
    "color_next":  "0xeac740",
    "cycle":       "0xeac75e",
    "cycle_light": "0xeac75a",
    "sound_mode":  "0xeac715",
    "oscillation": "0xeac719",
}

ROKU_CODES = {
    "power":     "0xeac717",
    "home":      "0xeac703",
    "back":      "0xeac766",
    "up":        "0xeac719",
    "down":      "0xeac733",
    "left":      "0xeac71e",
    "right":     "0xeac72d",
    "ok":        "0xeac72a",
    "play":      "0xeac74c",
    "rewind":    "0xeac734",
    "skip":      "0xeac755",
    "reverse":   "0xeac778",
    "settings":  "0xeac761",
    "sleep":     "0xeac762",
    "netflix":   "0xeac752",
    "hulu":      "0xeac74d",
    "sling":     "0xeac706",
    "now":       "0xeac76c",
}

DEVICES = {
    "led": LED_CODES,
    "roku": ROKU_CODES,
}

_tx_device = None  # cached after the first lookup


def find_transmitter():
    """Find the lirc device that can send. The number can change between boots."""
    global _tx_device
    if _tx_device:
        return _tx_device

    for dev in sorted(glob.glob("/dev/lirc*")):
        result = subprocess.run(
            ["ir-ctl", "-f", "-d", dev],
            capture_output=True, text=True,
        )
        if "Device can send" in result.stdout:
            _tx_device = dev
            return dev

    raise RuntimeError(
        "No IR transmitter found. Check the gpio-ir-tx overlay and your wiring, "
        "and make sure you have permission to use /dev/lirc*."
    )


def send_code(code, repeat=1):
    """Send a raw code like '0xeac742'."""
    dev = find_transmitter()
    for i in range(repeat):
        subprocess.run(
            ["ir-ctl", "-d", dev, "-S", f"{PROTOCOL}:{code}"],
            check=True,
        )
        if i < repeat - 1:
            time.sleep(0.1)


def send(device, button, repeat=1):
    """Send a named button, like send('led', 'red')."""
    codes = DEVICES.get(device)
    if codes is None:
        raise ValueError(f"Unknown device '{device}'. Options: {', '.join(DEVICES)}")
    code = codes.get(button)
    if code is None:
        raise ValueError(f"Unknown button '{button}' for {device}. Options: {', '.join(codes)}")
    send_code(code, repeat)
    return code


def print_buttons():
    for name, codes in DEVICES.items():
        print(f"{name}:")
        for button, code in codes.items():
            print(f"  {button:<12} {code}")


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("list", "-h", "--help"):
        print("Usage: python3 ir_remote.py <device> <button>\n")
        print_buttons()
        return

    if len(args) != 2:
        print("Usage: python3 ir_remote.py <device> <button>")
        sys.exit(1)

    device, button = args[0].lower(), args[1].lower()
    try:
        code = send(device, button)
        print(f"Sent {device} {button} ({code}) on {find_transmitter()}")
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}")
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("Error: ir-ctl failed. Try running with sudo, or see the permissions note.")
        sys.exit(1)


if __name__ == "__main__":
    main()
